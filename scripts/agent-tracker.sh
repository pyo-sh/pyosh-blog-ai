#!/usr/bin/env bash
# scripts/agent-tracker.sh
# Real-time tmux agent dashboard — tracks Claude Code and Codex panes
#
# Usage: bash scripts/agent-tracker.sh [-s SESSION] [-i INTERVAL]
#   -s SESSION   tmux session name (default: lab)
#   -i INTERVAL  refresh interval in seconds (default: 2)

SESSION="lab"
INTERVAL=2
PIPELINE_DIR="/workspace/.workspace/pipeline"

# ─────────────────────────────────────────────────────────────────────────────
# Colors (blue accent theme, matching context-bar.sh)
# ─────────────────────────────────────────────────────────────────────────────
R='\033[0m'
BOLD='\033[1m'
GRAY='\033[38;5;245m'
DARK='\033[38;5;238m'
BLUE='\033[38;5;74m'     # Claude / accent
CYAN='\033[38;5;37m'     # Codex
GREEN='\033[38;5;71m'    # working
GOLD='\033[38;5;136m'    # plan / pipeline
ROSE='\033[38;5;132m'    # error

# ─────────────────────────────────────────────────────────────────────────────
# Terminal lifecycle
# ─────────────────────────────────────────────────────────────────────────────
cleanup() {
  tput cnorm 2>/dev/null
  tput rmcup 2>/dev/null
  exit 0
}
trap cleanup EXIT INT TERM

# ─────────────────────────────────────────────────────────────────────────────
# Argument parsing
# ─────────────────────────────────────────────────────────────────────────────
while getopts ":s:i:h" opt; do
  case $opt in
    s) SESSION="$OPTARG" ;;
    i) INTERVAL="$OPTARG" ;;
    h)
      printf 'Usage: %s [-s SESSION] [-i INTERVAL]\n' "$(basename "$0")"
      printf '  -s SESSION   tmux session name (default: lab)\n'
      printf '  -i INTERVAL  refresh interval in seconds (default: 2)\n'
      exit 0 ;;
    \?) printf 'Unknown option: -%s\n' "$OPTARG"; exit 1 ;;
  esac
done

# ─────────────────────────────────────────────────────────────────────────────
# Rendering helpers
# ─────────────────────────────────────────────────────────────────────────────

# make_line <char> <n> — repeat unicode char n times
make_line() {
  local char="$1" n="$2" s=""
  for ((i = 0; i < n; i++)); do s+="$char"; done
  printf '%s' "$s"
}

# trunc <string> <width> — truncate to width; pad with spaces if shorter
trunc() {
  local s="$1" w="$2"
  if (( ${#s} > w )); then
    printf '%s…' "${s:0:$((w - 1))}"
  else
    printf '%-*s' "$w" "$s"
  fi
}

# pad_right <string> <width>
pad_right() { printf '%-*s' "$2" "$1"; }

# token_bar <pct> <color> — render ▰▰▰▱▱ (5 blocks)
token_bar() {
  local pct="$1" color="$2" bar=""
  for ((i = 0; i < 5; i++)); do
    (( i * 20 < pct )) && bar+="${color}▰${R}" || bar+="${DARK}▱${R}"
  done
  printf '%s' "$bar"
}

# status_badge <status> — 6 visible chars
status_badge() {
  case "$1" in
    working) printf "${GREEN}● work${R}" ;;
    plan)    printf "${GOLD}◑ plan${R}" ;;
    error)   printf "${ROSE}✖ err ${R}" ;;
    *)       printf "${GRAY}○ idle${R}" ;;
  esac
}

# ─────────────────────────────────────────────────────────────────────────────
# Data extraction: Claude Code
# ─────────────────────────────────────────────────────────────────────────────
parse_claude_pane() {
  local pane_id="$1"
  local captured
  captured=$(tmux capture-pane -p -t "$pane_id" -S -150 2>/dev/null)

  # ── Status: spinner → working, ⏸ → plan, ❯ alone → idle ──────────────────
  local status="idle"
  local bottom8
  bottom8=$(printf '%s' "$captured" | tail -8)
  if printf '%s' "$bottom8" | grep -qP '✻|⠋|⠙|⠹|⠸|⠼|⠴|⠦|⠧|⠇|⠏'; then
    status="working"
  elif printf '%s' "$bottom8" | grep -qP '⏸|plan mode'; then
    status="plan"
  fi

  # ── Engine: "Opus 4.6", "Sonnet 4.6", "Haiku 4.5" ────────────────────────
  local model
  model=$(printf '%s' "$captured" \
    | grep -oP '(Opus|Sonnet|Haiku)\s+[0-9]+\.[0-9]+' | tail -1)
  [[ -z "$model" ]] && model="Claude"

  # ── Token %: "31% of 200k tokens" ────────────────────────────────────────
  local pct=0
  local tok
  tok=$(printf '%s' "$captured" \
    | grep -oP '[0-9]+(?=% of [0-9]+k tokens)' | tail -1)
  [[ -n "$tok" ]] && pct=$tok

  # ── Task: 💬 line from context-bar hook ──────────────────────────────────
  local task
  task=$(printf '%s' "$captured" | grep -oP '(?<=💬 ).+' | tail -1)
  [[ -z "$task" ]] && task="—"

  printf '%s|%s|%d|%s' "$model" "$status" "$pct" "$task"
}

# ─────────────────────────────────────────────────────────────────────────────
# Data extraction: Codex
# ─────────────────────────────────────────────────────────────────────────────
parse_codex_pane() {
  local pane_id="$1"
  local captured
  captured=$(tmux capture-pane -p -t "$pane_id" -S -50 2>/dev/null)

  local model="Codex" status="idle" pct=0 task="—"

  # Most recent session JSONL
  local session_file
  session_file=$(ls -t ~/.codex/sessions/*/*/*-*.jsonl 2>/dev/null | head -1)

  if [[ -n "$session_file" && -f "$session_file" ]]; then
    # ── Engine ───────────────────────────────────────────────────────────────
    local raw_model
    raw_model=$(jq -r 'select(.type == "turn_context") | .payload.model // empty' \
      "$session_file" 2>/dev/null | tail -1)
    [[ -n "$raw_model" ]] && model="$raw_model"

    # ── Token % (assuming 128k context) ──────────────────────────────────────
    local total_tok
    total_tok=$(jq -r \
      'select(.type == "token_count") | .payload.info.total_token_usage // empty' \
      "$session_file" 2>/dev/null | tail -1)
    if [[ -n "$total_tok" && "$total_tok" -gt 0 ]]; then
      pct=$(( total_tok * 100 / 128000 ))
      (( pct > 100 )) && pct=100
    fi

    # ── Task ─────────────────────────────────────────────────────────────────
    local last_msg
    last_msg=$(jq -r \
      'select(.type == "user_message") | .payload.message // empty' \
      "$session_file" 2>/dev/null | tail -1 | tr '\n' ' ')
    [[ -n "$last_msg" ]] && task="$last_msg"
  fi

  # ── Status: spinner in pane content ──────────────────────────────────────
  local bottom5
  bottom5=$(printf '%s' "$captured" | tail -5)
  if printf '%s' "$bottom5" \
      | grep -qP '[⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏]|Working\.\.\.|Generating'; then
    status="working"
  fi

  printf '%s|%s|%d|%s' "$model" "$status" "$pct" "$task"
}

# ─────────────────────────────────────────────────────────────────────────────
# Pipeline summary for footer
# ─────────────────────────────────────────────────────────────────────────────
get_pipeline_summary() {
  local parts=()
  for f in "$PIPELINE_DIR"/issue-*.state.json; do
    [[ -f "$f" ]] || continue
    local issue step
    issue=$(jq -r '.issue // empty' "$f" 2>/dev/null)
    step=$(jq -r '.step  // empty' "$f" 2>/dev/null)
    [[ -z "$issue" ]] && continue
    parts+=("#${issue}(${step})")
  done
  if (( ${#parts[@]} > 0 )); then
    local IFS=', '
    printf '%s' "${parts[*]}"
  fi
}

# ─────────────────────────────────────────────────────────────────────────────
# Dashboard renderer
# ─────────────────────────────────────────────────────────────────────────────
render_dashboard() {
  # ── Terminal width ─────────────────────────────────────────────────────────
  local COLS
  COLS=$(tput cols 2>/dev/null || echo 100)
  (( COLS < 82 )) && COLS=82
  local INNER=$(( COLS - 2 ))   # inside ║...║

  # ── Column widths: PANE | TASK | ENGINE | STATUS | TOKENS ─────────────────
  # STATUS = 6 visible ("● work"), TOKENS = 9 ("▰▰▰▱▱ 31%")
  # margins: 2 left + 2 right = 4, gaps: 4 × 1 = 4  → fixed cost = 4+4+11+12+6+9 = 46
  local W_PANE=11 W_ENGINE=12 W_STATUS=6 W_TOKENS=9
  local W_TASK=$(( INNER - W_PANE - W_ENGINE - W_STATUS - W_TOKENS - 8 ))
  (( W_TASK < 15 )) && W_TASK=15

  local now
  now=$(date '+%Y-%m-%d %H:%M:%S')

  # ── Collect agent pane data ────────────────────────────────────────────────
  local -a rows=()
  local n_working=0 n_plan=0 n_idle=0

  while IFS=' ' read -r pane_addr pane_id pane_cmd; do
    local etype
    case "$pane_cmd" in
      claude) etype="claude" ;;
      codex)  etype="codex"  ;;
      *)      continue ;;
    esac

    local data
    if [[ "$etype" == "claude" ]]; then
      data=$(parse_claude_pane "$pane_id")
    else
      data=$(parse_codex_pane "$pane_id")
    fi

    local model status pct task
    IFS='|' read -r model status pct task <<< "$data"

    case "$status" in
      working) (( n_working++ )) ;;
      plan)    (( n_plan++ ))    ;;
      *)       (( n_idle++ ))    ;;
    esac

    rows+=("${pane_addr}|${pane_id}|${etype}|${model}|${status}|${pct}|${task}")
  done < <(tmux list-panes -s -t "$SESSION" \
    -F '#{window_index}:#{pane_index} #{pane_id} #{pane_current_command}' 2>/dev/null)

  local n_total=${#rows[@]}

  # ── Pipeline ───────────────────────────────────────────────────────────────
  local pipeline_str
  pipeline_str=$(get_pipeline_summary)

  # ── Border strings ─────────────────────────────────────────────────────────
  local eqline hline
  eqline=$(make_line '═' "$INNER")
  hline=$(make_line '─' "$INNER")

  # ── Column header/divider strings ─────────────────────────────────────────
  local h_pane h_task h_engine h_status h_tokens
  h_pane=$(pad_right "PANE"   $W_PANE)
  h_task=$(pad_right "TASK"   $W_TASK)
  h_engine=$(pad_right "ENGINE" $W_ENGINE)
  h_status=$(pad_right "STATUS" $W_STATUS)
  h_tokens=$(pad_right "TOKENS" $W_TOKENS)

  local d_pane d_task d_engine d_status d_tokens
  d_pane=$(make_line '─' $W_PANE)
  d_task=$(make_line '─' $W_TASK)
  d_engine=$(make_line '─' $W_ENGINE)
  d_status=$(make_line '─' $W_STATUS)
  d_tokens=$(make_line '─' $W_TOKENS)

  # ── Draw ───────────────────────────────────────────────────────────────────
  tput cup 0 0

  # ╔═══...═══╗
  printf "${GRAY}╔%s╗${R}" "$eqline"; tput el; echo

  # ║  Agent Tracker          2026-02-28 10:35:42 ║
  local title_len=13  # "Agent Tracker"
  local gap=$(( INNER - 2 - title_len - ${#now} - 1 ))
  (( gap < 1 )) && gap=1
  printf "${GRAY}║${R}  ${BOLD}${BLUE}Agent Tracker${R}${GRAY}%*s%s ${GRAY}║${R}" \
    "$gap" "" "$now"
  tput el; echo

  # ╠═══...═══╣
  printf "${GRAY}╠%s╣${R}" "$eqline"; tput el; echo

  # ║ (blank) ║
  printf "${GRAY}║${R}%*s${GRAY}║${R}" "$INNER" ""; tput el; echo

  # ║  PANE        TASK   ENGINE  STATUS  TOKENS  ║
  printf "${GRAY}║${R}  ${DARK}%s %s %s %s %s${R}  ${GRAY}║${R}" \
    "$h_pane" "$h_task" "$h_engine" "$h_status" "$h_tokens"
  tput el; echo

  # ║  ───  ─────  ──────  ──────  ──────  ║
  printf "${GRAY}║${R}  ${DARK}%s %s %s %s %s${R}  ${GRAY}║${R}" \
    "$d_pane" "$d_task" "$d_engine" "$d_status" "$d_tokens"
  tput el; echo

  # ── Agent rows ────────────────────────────────────────────────────────────
  if (( n_total == 0 )); then
    local no_msg
    no_msg=$(printf "  No active agents in session '%s'" "$SESSION")
    printf "${GRAY}║${R}%-*s${GRAY}║${R}" "$INNER" "$no_msg"; tput el; echo
  else
    for row in "${rows[@]}"; do
      IFS='|' read -r pane_addr pane_id etype model status pct task <<< "$row"

      local ecol
      [[ "$etype" == "claude" ]] && ecol="$BLUE" || ecol="$CYAN"

      local col_pane col_task col_engine tok_bar_str badge
      col_pane=$(pad_right "${pane_addr} ${pane_id}" $W_PANE)
      col_task=$(trunc "$task" $W_TASK)
      col_engine=$(printf "${ecol}%-*s${R}" $W_ENGINE "$model")
      tok_bar_str=$(token_bar "$pct" "$ecol")
      badge=$(status_badge "$status")

      printf "${GRAY}║${R}  "
      printf "${GRAY}%s${R} " "$col_pane"          # PANE
      printf "%s "            "$col_task"           # TASK
      printf "%b "            "$col_engine"         # ENGINE
      printf "%b   "          "$badge"              # STATUS (6 chars + 3 pad)
      printf "%b %2d%%  "     "$tok_bar_str" "$pct" # TOKENS
      printf "${GRAY}║${R}"
      tput el; echo
    done
  fi

  # ║ (blank) ║
  printf "${GRAY}║${R}%*s${GRAY}║${R}" "$INNER" ""; tput el; echo

  # ╠═══...═══╣
  printf "${GRAY}╠%s╣${R}" "$eqline"; tput el; echo

  # ║  ● Active: N agents (W working, I idle)  │  ⚙ Pipeline: #10(resolve)  ║
  local n_stat="(${n_working} working"
  (( n_plan > 0 )) && n_stat+=", ${n_plan} plan"
  n_stat+=", ${n_idle} idle)"

  local left_colored="${GREEN}●${R} ${GRAY}Active: ${n_total} agents ${n_stat}${R}"
  local left_plain="● Active: ${n_total} agents ${n_stat}"

  local right_colored="" right_plain=""
  if [[ -n "$pipeline_str" ]]; then
    right_colored="  ${GRAY}│${R}  ${GOLD}⚙ Pipeline: ${pipeline_str}${R}"
    right_plain="  │  ⚙ Pipeline: ${pipeline_str}"
  fi

  local footer_len=$(( 2 + ${#left_plain} + ${#right_plain} ))
  local fpad=$(( INNER - footer_len - 1 ))
  (( fpad < 0 )) && fpad=0

  printf "${GRAY}║${R}  %b%b%*s ${GRAY}║${R}" \
    "$left_colored" "$right_colored" "$fpad" ""
  tput el; echo

  # ╚═══...═══╝
  printf "${GRAY}╚%s╝${R}" "$eqline"; tput el; echo

  # Clear any lines below the dashboard
  tput ed
}

# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
tput smcup  # enter alternate screen
tput civis  # hide cursor

while true; do
  render_dashboard
  sleep "$INTERVAL"
done
