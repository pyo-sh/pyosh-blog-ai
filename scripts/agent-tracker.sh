#!/usr/bin/env bash
# scripts/agent-tracker.sh
# Real-time tmux agent dashboard — tracks Claude Code and Codex panes
#
# Usage: bash scripts/agent-tracker.sh [-s SESSION] [-i INTERVAL]
#   -s SESSION   tmux session name (default: lab)
#   -i INTERVAL  refresh interval in seconds (default: 2)

SESSION="lab"
INTERVAL=1
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null \
  || cd "$SCRIPT_DIR/.." && pwd)"
PIPELINE_DIR="${PIPELINE_DIR:-"$REPO_ROOT/.workspace/pipeline"}"

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
    working) printf "${GREEN}● work${R}" ;;
    plan)    printf "${GOLD}◑ plan${R}" ;;
    error)   printf "${ROSE}✖ err ${R}" ;;
    *)       printf "${GRAY}○ idle${R}" ;;
  esac
}

# ─────────────────────────────────────────────────────────────────────────────
# Data extraction: Claude Code
# ─────────────────────────────────────────────────────────────────────────────

# find_claude_transcript <pane_id>
# Map a Claude pane to its own transcript JSONL via TTY → PID → /proc/fd scan.
# Falls back to most-recent file when PID mapping is unavailable.
find_claude_transcript() {
  local pane_id="$1"
  local pane_tty claude_pid session_uuid

  # 1. pane TTY → Claude PID
  pane_tty=$(tmux display-message -t "$pane_id" -p "#{pane_tty}" 2>/dev/null)
  if [[ -n "$pane_tty" ]]; then
    local pts="${pane_tty#/dev/}"
    claude_pid=$(ps -a -o pid,tty,comm 2>/dev/null \
      | awk -v pts="$pts" '$2==pts && $3=="claude" {print $1; exit}')
  fi

  # 2. /proc/PID/fd scan → session UUID
  if [[ -n "$claude_pid" && -d "/proc/$claude_pid/fd" ]]; then
    local pane_cwd project_dir fd_target
    pane_cwd=$(readlink "/proc/$claude_pid/cwd" 2>/dev/null)
    [[ -z "$pane_cwd" ]] && pane_cwd=$(tmux display-message -t "$pane_id" \
      -p '#{pane_current_path}' 2>/dev/null)
    project_dir="${pane_cwd//\//-}"

    for fd_path in /proc/"$claude_pid"/fd/*; do
      fd_target=$(readlink "$fd_path" 2>/dev/null) || continue
      # tasks/{UUID} held open via flock(), or projects/{dir}/{UUID} session subdir
      if [[ "$fd_target" =~ /tasks/([0-9a-f-]{36}) ]] || \
         [[ "$fd_target" =~ /projects/${project_dir}/([0-9a-f-]{36}) ]]; then
        session_uuid="${BASH_REMATCH[1]}"
        break
      fi
    done

    if [[ -n "$session_uuid" ]]; then
      local t="${HOME}/.claude/projects/${project_dir}/${session_uuid}.jsonl"
      [[ -f "$t" ]] && { printf '%s' "$t"; return; }
    fi
  fi

  # 3. Fallback: most recent JSONL for this project dir
  local pane_cwd project_dir
  pane_cwd=$(tmux display-message -t "$pane_id" -p '#{pane_current_path}' 2>/dev/null)
  [[ -z "$pane_cwd" ]] && return
  project_dir="${pane_cwd//\//-}"
  ls -t "${HOME}/.claude/projects/$project_dir"/*.jsonl 2>/dev/null | head -1
}

parse_claude_pane() {
  local pane_id="$1"
  local captured
  captured=$(tmux capture-pane -p -t "$pane_id" -S -150 2>/dev/null)

  # ── Status: spinner → working, ⏸ → plan, ❯ alone → idle ──────────────────
  local status="idle"
  local bottom8
  bottom8=$(printf '%s' "$captured" | tail -8)
  if printf '%s' "$bottom8" | grep -qE '✢|✶|✻|✽|⠋|⠙|⠹|⠸|⠼|⠴|⠦|⠧|⠇|⠏'; then
    status="working"
  elif printf '%s' "$bottom8" | grep -qE '⏸|plan mode'; then
    status="plan"
  fi

  # ── Model + Token + Task: transcript 직접 읽기 ──────────────────────────
  local model="Claude" pct=0 tok_k=0 task="—"
  local transcript
  transcript=$(find_claude_transcript "$pane_id")

  if [[ -n "$transcript" && -f "$transcript" ]]; then
    # Single jq pass: model, ctx_len, last user message
    # Fields separated by RS (0x1e); task is base64-encoded to survive embedded newlines
    local raw_data raw_model ctx_len task_raw
    raw_data=$(jq -rs '
      . as $all |
      [$all[] | select(.type == "assistant" and .isSidechain != true
                and .isApiErrorMessage != true)] as $a |
      ($a | last | .message.model // "") as $m |
      ($a | map(select(.message.usage)) | last |
        if . then
          (.message.usage.input_tokens // 0) +
          (.message.usage.cache_read_input_tokens // 0) +
          (.message.usage.cache_creation_input_tokens // 0)
        else 0 end) as $ctx |
      ([$all[] | select(.type == "user") |
        .message.content |
        if type == "string" then .
        elif type == "array" then
          [.[] | select(.type == "text") | .text] | join(" ")
        else "" end
      ] | last // "") as $task |
      "\($m)\u001e\($ctx)\u001e\($task | @base64)"
    ' < "$transcript" 2>/dev/null)

    IFS=$'\x1e' read -r raw_model ctx_len task_raw <<< "$raw_data"
    # Decode base64 task so embedded newlines are preserved for normalization below
    task_raw=$(base64 -d <<< "$task_raw" 2>/dev/null)

    # "claude-opus-4-6" → "Opus 4.6" (handles date-suffixed IDs like claude-haiku-4-5-20251001)
    if [[ -n "$raw_model" && "$raw_model" =~ ^claude-([a-z]+)-([0-9]+)-([0-9]+) ]]; then
      model="${BASH_REMATCH[1]^} ${BASH_REMATCH[2]}.${BASH_REMATCH[3]}"
    fi

    if [[ -n "$ctx_len" && "$ctx_len" -gt 0 ]] 2>/dev/null; then
      pct=$(( ctx_len * 100 / 200000 ))
      (( pct > 100 )) && pct=100
      tok_k=$(( ctx_len / 1000 ))
    fi

    if [[ -n "$task_raw" ]]; then
      task="${task_raw//$'\n'/ }"   # newlines → spaces (faster than jq gsub)
      task="${task//  / }"          # collapse double spaces
    fi
  else
    # Fallback: pane 스크래핑
    local tok
    tok=$(printf '%s' "$captured" \
      | grep -oE '[0-9]+% of [0-9]+k tokens' | sed 's/%.*//' | tail -1)
    if [[ -n "$tok" ]]; then
      pct=$tok
      tok_k=$(( pct * 200 / 100 ))
    fi

    local ptask
    ptask=$(printf '%s' "$captured" | grep -o '💬 .*' | sed 's/.*💬 //' | tail -1)
    [[ -n "$ptask" ]] && task="$ptask"

    # Model: startup screen may still be visible
    local pane_model
    pane_model=$(printf '%s' "$captured" \
      | grep -oE '(Opus|Sonnet|Haiku)[[:space:]]+[0-9]+\.[0-9]+' | tail -1)
    [[ -n "$pane_model" ]] && model="$pane_model"
  fi

  printf '%s|%s|%d|%d|%s' "$model" "$status" "$pct" "$tok_k" "$task"
}

# ─────────────────────────────────────────────────────────────────────────────
# Data extraction: Codex
# ─────────────────────────────────────────────────────────────────────────────

# find_codex_session_file <pane_id>
# Map a Codex pane to its own session JSONL by inspecting open file descriptors
# in the pane's process tree. Falls back to the globally most recent file.
find_codex_session_file() {
  local pane_id="$1"
  local pane_pid session_file

  pane_pid=$(tmux display-message -t "$pane_id" -p '#{pane_pid}' 2>/dev/null)

  if [[ -n "$pane_pid" ]]; then
    # Collect PIDs in pane's process tree (shell + 2 levels of children)
    local all_pids=("$pane_pid") child grandchild
    while IFS= read -r child; do
      all_pids+=("$child")
      while IFS= read -r grandchild; do
        all_pids+=("$grandchild")
      done < <(pgrep -P "$child" 2>/dev/null)
    done < <(pgrep -P "$pane_pid" 2>/dev/null)

    # Linux: read /proc/{pid}/fd symlinks for open session files (fast, no lsof)
    if [[ -d /proc ]]; then
      local pid
      for pid in "${all_pids[@]}"; do
        session_file=$(readlink -f /proc/"$pid"/fd/* 2>/dev/null \
          | grep -E '\.codex/sessions.*\.jsonl$' | head -1)
        [[ -n "$session_file" ]] && { printf '%s' "$session_file"; return; }
      done
    fi

    # Cross-platform fallback via lsof (if available)
    if command -v lsof >/dev/null 2>&1; then
      local pids_str
      pids_str=$(printf '%s,' "${all_pids[@]}"); pids_str="${pids_str%,}"
      session_file=$(lsof -p "$pids_str" 2>/dev/null \
        | awk '$NF ~ /\.codex\/sessions.*\.jsonl$/ { print $NF; exit }')
      [[ -n "$session_file" ]] && { printf '%s' "$session_file"; return; }
    fi
  fi

  # Final fallback: globally most recent session file
  ls -t ~/.codex/sessions/*/*/*-*.jsonl 2>/dev/null | head -1
}

parse_codex_pane() {
  local pane_id="$1"
  local captured
  captured=$(tmux capture-pane -p -t "$pane_id" -S -50 2>/dev/null)

  local model="Codex" status="idle" pct=0 tok_k=0 task="—"

  # Pane-specific session JSONL (falls back to globally most recent)
  local session_file
  session_file=$(find_codex_session_file "$pane_id")

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
      tok_k=$(( total_tok / 1000 ))
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
      | grep -qE '[⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏]|Working\.\.\.|Generating'; then
    status="working"
  fi

  printf '%s|%s|%d|%d|%s' "$model" "$status" "$pct" "$tok_k" "$task"
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

  # ── Fixed column widths (PANE, ENGINE, STATUS) ────────────────────────────
  # TOKENS: named content = bar(5)+sp(1)+str(N), trailing 2sp in printf absorbed into -8
  # TASK: fills remaining space
  # Fixed formula: W_TASK = INNER - W_PANE - W_ENGINE - W_STATUS - W_TOKENS - 8
  #   where -8 = left_margin(2) + 4_seps(4) + right_margin_2sp(2)
  local W_PANE=11 W_ENGINE=12 W_STATUS=6 W_TOKENS_MIN=10

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

    local model status pct tok_k task
    IFS='|' read -r model status pct tok_k task <<< "$data"

    case "$status" in
      working) (( n_working++ )) ;;
      plan)    (( n_plan++ ))    ;;
      *)       (( n_idle++ ))    ;;
    esac

    rows+=("${pane_addr}|${pane_id}|${etype}|${model}|${status}|${pct}|${tok_k}|${task}")
  done < <(tmux list-panes -s -t "$SESSION" \
    -F '#{window_index}:#{pane_index} #{pane_id} #{pane_current_command}' 2>/dev/null)

  local n_total=${#rows[@]}

  # ── TOKENS column: min width, grows with content ───────────────────────────
  local W_TOKENS=$W_TOKENS_MIN
  local _tok_k _tok_str _tok_w _row_tok_k _row_pct
  for _row in "${rows[@]}"; do
    IFS='|' read -r _ _ _ _ _ _row_pct _row_tok_k _ <<< "$_row"
    if (( _row_tok_k > 999 )); then _tok_str="999+"; else printf -v _tok_str "%3dk" "$_row_tok_k"; fi
    _tok_w=$(( 5 + 1 + ${#_tok_str} ))   # bar(5) + sp(1) + str(N); trailing 2sp in printf is in -8
    (( _tok_w > W_TOKENS )) && W_TOKENS=$_tok_w
  done
  local W_TASK=$(( INNER - W_PANE - W_ENGINE - W_STATUS - W_TOKENS - 8 ))
  (( W_TASK < 15 )) && W_TASK=15

  # ── Pipeline ───────────────────────────────────────────────────────────────
  local pipeline_str
  pipeline_str=$(get_pipeline_summary)

  # ── Border strings ─────────────────────────────────────────────────────────
  local eqline hline
  eqline=$(make_line '═' "$INNER")
  hline=$(make_line '─' "$INNER")

  # ── Column header/divider strings (computed after W_TOKENS is known) ───────
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
      IFS='|' read -r pane_addr pane_id etype model status pct tok_k task <<< "$row"

      local ecol
      [[ "$etype" == "claude" ]] && ecol="$BLUE" || ecol="$CYAN"

      local col_pane col_task col_engine tok_bar_str badge
      col_pane=$(trunc "${pane_addr} ${pane_id}" $W_PANE)
      col_task=$(trunc "$task" $W_TASK)
      col_engine=$(printf "${ecol}%s${R}" "$(trunc "$model" $W_ENGINE)")
      tok_bar_str=$(token_bar "$pct" "$ecol")
      badge=$(status_badge "$status")

      printf "${GRAY}║${R}  "
      printf "${GRAY}%s${R} " "$col_pane"          # PANE
      printf "%s "            "$col_task"           # TASK
      printf "%b "            "$col_engine"         # ENGINE
      printf "%b "            "$badge"              # STATUS (6 chars + 1 pad)
      local tok_str
      if (( tok_k > 999 )); then tok_str="999+"; else printf -v tok_str "%3dk" "$tok_k"; fi
      printf "%b %s  "       "$tok_bar_str" "$tok_str" # TOKENS (5 bar + 1 sp + 4 str + 2 sp)
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
