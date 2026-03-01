#!/usr/bin/env bash
# tools/agent-tracker/agent-tracker.sh
# Real-time tmux agent dashboard — reads from sidecar files (push model)
#
# Claude Code panes: data pushed by hooks → /tmp/agent-tracker/{pane_id}.json
# Codex panes: pane scraping fallback (no hooks support)
#
# Usage: bash tools/agent-tracker/agent-tracker.sh [-s SESSION] [-i INTERVAL]
#   -s SESSION   tmux session name (default: lab)
#   -i INTERVAL  refresh interval in seconds (default: 1)

SESSION="lab"
INTERVAL=1
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PIPELINE_DIR="${PIPELINE_DIR:-"$REPO_ROOT/.workspace/pipeline"}"
SIDECAR_DIR="/tmp/agent-tracker"

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
ROSE='\033[38;5;132m'    # error / needs-input

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
      printf '  -i INTERVAL  refresh interval in seconds (default: 1)\n'
      exit 0 ;;
    \?) printf 'Unknown option: -%s\n' "$OPTARG"; exit 1 ;;
  esac
done

# Validate INTERVAL: must be a positive number
if ! [[ "$INTERVAL" =~ ^[0-9]*\.?[0-9]+$ ]] || \
   ! awk "BEGIN { exit ($INTERVAL > 0) ? 0 : 1 }"; then
  printf 'Error: -i INTERVAL must be a positive number (got: %s)\n' "$INTERVAL" >&2
  exit 1
fi

# ─────────────────────────────────────────────────────────────────────────────
# Rendering helpers
# ─────────────────────────────────────────────────────────────────────────────

# make_line <char> <n> — repeat unicode char n times
make_line() {
  local char="$1" n="$2" s=""
  for ((i = 0; i < n; i++)); do s+="$char"; done
  printf '%s' "$s"
}

# display_width <string> — terminal display columns (CJK=2, ASCII=1)
display_width() { printf '%s' "$1" | wc -L; }

# trunc <string> <width> — truncate by display width; pad with spaces if shorter
trunc() {
  local s="$1" w="$2"
  local dw
  dw=$(display_width "$s")
  if (( dw <= w )); then
    printf '%s%*s' "$s" "$(( w - dw ))" ""
  else
    # binary search: longest prefix whose display width fits in w-1 (room for …)
    local lo=0 hi=${#s} mid best=0
    while (( lo <= hi )); do
      mid=$(( (lo + hi) / 2 ))
      if (( $(display_width "${s:0:$mid}") <= w - 1 )); then
        best=$mid; lo=$(( mid + 1 ))
      else
        hi=$(( mid - 1 ))
      fi
    done
    local prefix="${s:0:$best}"
    local pad=$(( w - $(display_width "$prefix") - 1 ))
    printf '%s…' "$prefix"
    (( pad > 0 )) && printf '%*s' "$pad" ""
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
    working)      printf "${GREEN}● work${R}" ;;
    plan)         printf "${GOLD}◑ plan${R}" ;;
    needs-input)  printf "${ROSE}◉ wait${R}" ;;
    error)        printf "${ROSE}✖ err ${R}" ;;
    *)            printf "${GRAY}○ idle${R}" ;;
  esac
}

# ─────────────────────────────────────────────────────────────────────────────
# Data extraction: Claude Code (sidecar-based)
# ─────────────────────────────────────────────────────────────────────────────

# parse_claude_pane <pane_id>
# Reads sidecar file written by hooks. Falls back to pane scraping if no sidecar.
parse_claude_pane() {
  local pane_id="$1"
  local pane_file="${pane_id#%}"
  local sidecar_path="${SIDECAR_DIR}/${pane_file}.json"

  local model="Claude" status="idle" pct=0 tok_k=0 task="—" activity=""

  if [[ -f "$sidecar_path" ]]; then
    # Sidecar exists — read all fields in a single jq pass
    local raw
    raw=$(jq -r '[
      .model // "Claude",
      .status // "idle",
      (.tokens.pct // 0 | tostring),
      ((.tokens.used // 0) / 1000 | floor | tostring),
      .task // "—",
      .activity // ""
    ] | join("\u001e")' "$sidecar_path" 2>/dev/null)

    if [[ -n "$raw" ]]; then
      IFS=$'\x1e' read -r model status pct tok_k task activity <<< "$raw"
    fi

    # Override status from pane if sidecar status seems stale
    # (e.g., hooks didn't fire but spinner is visible)
    local captured bottom8
    captured=$(tmux capture-pane -p -t "$pane_id" -S -8 2>/dev/null)
    bottom8=$(printf '%s' "$captured" | tail -8)
    if [[ "$status" != "working" ]] && \
       printf '%s' "$bottom8" | grep -qE '✢|✶|✻|✽|⠋|⠙|⠹|⠸|⠼|⠴|⠦|⠧|⠇|⠏'; then
      status="working"
    elif printf '%s' "$bottom8" | grep -qE '⏸|plan mode'; then
      status="plan"
    fi
  else
    # No sidecar — full pane scraping fallback
    local captured
    captured=$(tmux capture-pane -p -t "$pane_id" -S -50 2>/dev/null)

    # Status
    local bottom8
    bottom8=$(printf '%s' "$captured" | tail -8)
    if printf '%s' "$bottom8" | grep -qE '✢|✶|✻|✽|⠋|⠙|⠹|⠸|⠼|⠴|⠦|⠧|⠇|⠏'; then
      status="working"
    elif printf '%s' "$bottom8" | grep -qE '⏸|plan mode'; then
      status="plan"
    fi

    # Token %
    local tok
    tok=$(printf '%s' "$captured" \
      | grep -oE '[0-9]+% of [0-9]+k tokens' | sed 's/%.*//' | tail -1)
    if [[ -n "$tok" ]]; then
      pct=$tok
      tok_k=$(( pct * 200 / 100 ))
    fi

    # Task
    local ptask
    ptask=$(printf '%s' "$captured" | grep -o '💬 .*' | sed 's/.*💬 //' | tail -1)
    [[ -n "$ptask" ]] && task="$ptask"

    # Model
    local pane_model
    pane_model=$(printf '%s' "$captured" \
      | grep -oE '(Opus|Sonnet|Haiku)[[:space:]]+[0-9]+\.[0-9]+' | tail -1)
    [[ -n "$pane_model" ]] && model="$pane_model"
  fi

  printf '%s\x1e%s\x1e%d\x1e%d\x1e%s\x1e%s' "$model" "$status" "$pct" "$tok_k" "$task" "$activity"
}

# ─────────────────────────────────────────────────────────────────────────────
# Data extraction: Codex (pane scraping — no hooks support)
# ─────────────────────────────────────────────────────────────────────────────

# find_codex_session_file <pane_id>
find_codex_session_file() {
  local pane_id="$1"
  local pane_pid session_file

  pane_pid=$(tmux display-message -t "$pane_id" -p '#{pane_pid}' 2>/dev/null)

  if [[ -n "$pane_pid" ]]; then
    local all_pids=("$pane_pid") child grandchild
    while IFS= read -r child; do
      all_pids+=("$child")
      while IFS= read -r grandchild; do
        all_pids+=("$grandchild")
      done < <(pgrep -P "$child" 2>/dev/null)
    done < <(pgrep -P "$pane_pid" 2>/dev/null)

    if [[ -d /proc ]]; then
      local pid
      for pid in "${all_pids[@]}"; do
        session_file=$(readlink -f /proc/"$pid"/fd/* 2>/dev/null \
          | grep -E '\.codex/sessions.*\.jsonl$' | head -1)
        [[ -n "$session_file" ]] && { printf '%s' "$session_file"; return; }
      done
    fi
  fi

  # No global fallback — avoids cross-contamination in multi-pane setups
}

parse_codex_pane() {
  local pane_id="$1"
  local captured
  captured=$(tmux capture-pane -p -t "$pane_id" -S -50 2>/dev/null)

  local model="Codex" status="idle" pct=0 tok_k=0 task="—" activity=""

  local session_file
  session_file=$(find_codex_session_file "$pane_id")

  if [[ -n "$session_file" && -f "$session_file" ]]; then
    local raw_model
    raw_model=$(jq -r 'select(.type == "turn_context") | .payload.model // empty' \
      "$session_file" 2>/dev/null | tail -1)
    [[ -n "$raw_model" ]] && model="$raw_model"

    local total_tok ctx_window
    total_tok=$(jq -r \
      'select(.payload.info | type == "object") | .payload.info.total_token_usage.total_tokens // empty' \
      "$session_file" 2>/dev/null | tail -1)
    ctx_window=$(jq -r \
      'select(.payload.info | type == "object") | .payload.info.model_context_window // empty' \
      "$session_file" 2>/dev/null | tail -1)
    [[ -z "$ctx_window" || "$ctx_window" -le 0 ]] 2>/dev/null && ctx_window=200000
    if [[ -n "$total_tok" && "$total_tok" -gt 0 ]] 2>/dev/null; then
      pct=$(( total_tok * 100 / ctx_window ))
      (( pct > 100 )) && pct=100
      tok_k=$(( total_tok / 1000 ))
    fi

    # Bug A fix: try user_message first, then response_item with role=="user"
    local last_msg
    last_msg=$(jq -r \
      'select(.payload.type == "user_message") | .payload.message // empty' \
      "$session_file" 2>/dev/null | tail -1 | tr '\n' ' ')
    if [[ -z "$last_msg" ]]; then
      last_msg=$(jq -r \
        'select(.type == "response_item" and .payload.role == "user") |
         .payload.content // .payload.message // empty' \
        "$session_file" 2>/dev/null | tail -1 | tr '\n' ' ')
    fi
    [[ -n "$last_msg" ]] && task="$last_msg"
  fi

  local bottom5
  bottom5=$(printf '%s' "$captured" | tail -5)
  if printf '%s' "$bottom5" \
      | grep -qE '[⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏]|Working\.\.\.|Generating'; then
    status="working"
  fi

  printf '%s\x1e%s\x1e%d\x1e%d\x1e%s\x1e%s' "$model" "$status" "$pct" "$tok_k" "$task" "$activity"
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

# _get_cmdline <pid>
_get_cmdline() {
  local pid=$1
  if [[ -f /proc/"$pid"/cmdline ]]; then
    tr '\0' ' ' < /proc/"$pid"/cmdline 2>/dev/null
    return
  fi
  ps -o command= -p "$pid" 2>/dev/null
}

# _get_exe_name <pid>
_get_exe_name() {
  local pid=$1
  if [[ -L /proc/"$pid"/exe ]]; then
    local p
    p=$(readlink /proc/"$pid"/exe 2>/dev/null) && printf '%s' "${p##*/}"
    return
  fi
  ps -o comm= -p "$pid" 2>/dev/null | xargs basename 2>/dev/null
}

# _match_agent <cmdline> <exe_name>
_match_agent() {
  local cmdline="$1" exe="$2"
  if [[ "$exe" == "claude" ]] || \
     [[ "$cmdline" =~ @anthropic-ai/claude-code|claude-code/cli ]]; then
    printf 'claude'; return 0
  fi
  if [[ "$exe" == "codex" ]] || \
     [[ "$cmdline" =~ @openai/codex|codex\.js ]]; then
    printf 'codex'; return 0
  fi
  return 1
}

# detect_agent_type <pane_pid>
detect_agent_type() {
  local pids=() queue=("$1") pid child cmdline exename result
  while (( ${#queue[@]} > 0 )); do
    pid="${queue[0]}"; queue=("${queue[@]:1}")
    pids+=("$pid")
    while IFS= read -r child; do
      [[ -n "$child" ]] && queue+=("$child")
    done < <(pgrep -P "$pid" 2>/dev/null)
  done
  for pid in "${pids[@]}"; do
    cmdline=$(_get_cmdline "$pid") || continue
    exename=$(_get_exe_name "$pid") || true
    result=$(_match_agent "$cmdline" "$exename") && { printf '%s' "$result"; return 0; }
  done
  return 1
}

# ─────────────────────────────────────────────────────────────────────────────
# Dashboard renderer
# ─────────────────────────────────────────────────────────────────────────────
render_dashboard() {
  local COLS
  COLS=$(tput cols 2>/dev/null || echo 100)
  (( COLS < 86 )) && COLS=86
  local INNER=$(( COLS - 2 ))

  local W_PANE=11 W_ACTIVITY=18 W_ENGINE=12 W_STATUS=6 W_TOKENS_MIN=10

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
      *)
        local _pane_pid _detected
        _pane_pid=$(tmux display-message -t "$pane_id" -p '#{pane_pid}' 2>/dev/null)
        _detected=$(detect_agent_type "$_pane_pid" 2>/dev/null) || continue
        etype="$_detected" ;;
    esac

    local data
    if [[ "$etype" == "claude" ]]; then
      data=$(parse_claude_pane "$pane_id")
    else
      data=$(parse_codex_pane "$pane_id")
    fi

    local model status pct tok_k task activity
    IFS=$'\x1e' read -r model status pct tok_k task activity <<< "$data"

    case "$status" in
      working)      (( n_working++ )) ;;
      plan)         (( n_plan++ ))    ;;
      needs-input)  (( n_working++ )) ;;
      *)            (( n_idle++ ))    ;;
    esac

    rows+=("$(printf '%s\x1e%s\x1e%s\x1e%s\x1e%s\x1e%s\x1e%s\x1e%s\x1e%s' \
      "$pane_addr" "$pane_id" "$etype" "$model" "$status" "$pct" "$tok_k" "$task" "$activity")")
  done < <(tmux list-panes -s -t "$SESSION" \
    -F '#{window_index}:#{pane_index} #{pane_id} #{pane_current_command}' 2>/dev/null)

  local n_total=${#rows[@]}

  # ── TOKENS column width ────────────────────────────────────────────────────
  local W_TOKENS=$W_TOKENS_MIN
  local _tok_k _tok_str _tok_w _row_tok_k _row_pct
  for _row in "${rows[@]}"; do
    IFS=$'\x1e' read -r _ _ _ _ _ _row_pct _row_tok_k _ <<< "$_row"
    if (( _row_tok_k > 999 )); then _tok_str="999+"; else printf -v _tok_str "%3dk" "$_row_tok_k"; fi
    _tok_w=$(( 5 + 1 + ${#_tok_str} ))
    (( _tok_w > W_TOKENS )) && W_TOKENS=$_tok_w
  done
  local W_TASK=$(( INNER - W_PANE - W_ACTIVITY - W_ENGINE - W_STATUS - W_TOKENS - 10 ))
  (( W_TASK < 15 )) && W_TASK=15

  # ── Pipeline ───────────────────────────────────────────────────────────────
  local pipeline_str
  pipeline_str=$(get_pipeline_summary)

  # ── Border strings ─────────────────────────────────────────────────────────
  local eqline hline
  eqline=$(make_line '═' "$INNER")

  # ── Column header/divider strings ──────────────────────────────────────────
  local h_pane h_task h_activity h_engine h_status h_tokens
  h_pane=$(pad_right "PANE"     $W_PANE)
  h_task=$(pad_right "TASK"     $W_TASK)
  h_activity=$(pad_right "ACTIVITY" $W_ACTIVITY)
  h_engine=$(pad_right "ENGINE"  $W_ENGINE)
  h_status=$(pad_right "STATUS"  $W_STATUS)
  h_tokens=$(pad_right "TOKENS"  $W_TOKENS)

  local d_pane d_task d_activity d_engine d_status d_tokens
  d_pane=$(make_line '─' $W_PANE)
  d_task=$(make_line '─' $W_TASK)
  d_activity=$(make_line '─' $W_ACTIVITY)
  d_engine=$(make_line '─' $W_ENGINE)
  d_status=$(make_line '─' $W_STATUS)
  d_tokens=$(make_line '─' $W_TOKENS)

  # ── Draw ───────────────────────────────────────────────────────────────────
  tput cup 0 0

  printf "${GRAY}╔%s╗${R}" "$eqline"; tput el; echo

  local title_len=13
  local gap=$(( INNER - 2 - title_len - ${#now} - 1 ))
  (( gap < 1 )) && gap=1
  printf "${GRAY}║${R}  ${BOLD}${BLUE}Agent Tracker${R}${GRAY}%*s%s ${GRAY}║${R}" \
    "$gap" "" "$now"
  tput el; echo

  printf "${GRAY}╠%s╣${R}" "$eqline"; tput el; echo

  printf "${GRAY}║${R}%*s${GRAY}║${R}" "$INNER" ""; tput el; echo

  printf "${GRAY}║${R}  ${DARK}%s %s %s %s %s %s${R}  ${GRAY}║${R}" \
    "$h_pane" "$h_task" "$h_activity" "$h_engine" "$h_status" "$h_tokens"
  tput el; echo

  printf "${GRAY}║${R}  ${DARK}%s %s %s %s %s %s${R}  ${GRAY}║${R}" \
    "$d_pane" "$d_task" "$d_activity" "$d_engine" "$d_status" "$d_tokens"
  tput el; echo

  # ── Agent rows ─────────────────────────────────────────────────────────────
  if (( n_total == 0 )); then
    local no_msg
    no_msg=$(printf "  No active agents in session '%s'" "$SESSION")
    printf "${GRAY}║${R}%-*s${GRAY}║${R}" "$INNER" "$no_msg"; tput el; echo
  else
    for row in "${rows[@]}"; do
      IFS=$'\x1e' read -r pane_addr pane_id etype model status pct tok_k task activity <<< "$row"

      local ecol
      [[ "$etype" == "claude" ]] && ecol="$BLUE" || ecol="$CYAN"

      # Activity display: show tool action or idle indicator
      local act_display
      if [[ -z "$activity" || "$activity" == "null" ]]; then
        if [[ "$status" == "idle" ]]; then
          act_display="— (idle)"
        else
          act_display="—"
        fi
      else
        act_display="$activity"
      fi

      local col_pane col_task col_activity col_engine tok_bar_str badge
      col_pane=$(trunc "${pane_addr} ${pane_id}" $W_PANE)
      col_task=$(trunc "$task" $W_TASK)
      col_activity=$(trunc "$act_display" $W_ACTIVITY)
      col_engine=$(printf "${ecol}%s${R}" "$(trunc "$model" $W_ENGINE)")
      tok_bar_str=$(token_bar "$pct" "$ecol")
      badge=$(status_badge "$status")

      printf "${GRAY}║${R}  "
      printf "${GRAY}%s${R} " "$col_pane"
      printf "%s "            "$col_task"
      printf "%s "            "$col_activity"
      printf "%b "            "$col_engine"
      printf "%b "            "$badge"
      local tok_str
      if (( tok_k > 999 )); then tok_str="999+"; else printf -v tok_str "%3dk" "$tok_k"; fi
      printf "%b %s  "       "$tok_bar_str" "$tok_str"
      printf "${GRAY}║${R}"
      tput el; echo
    done
  fi

  printf "${GRAY}║${R}%*s${GRAY}║${R}" "$INNER" ""; tput el; echo

  printf "${GRAY}╠%s╣${R}" "$eqline"; tput el; echo

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

  printf "${GRAY}╚%s╝${R}" "$eqline"; tput el; echo

  tput ed
}

# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
tput smcup
tput civis

while true; do
  render_dashboard
  sleep "$INTERVAL"
done
