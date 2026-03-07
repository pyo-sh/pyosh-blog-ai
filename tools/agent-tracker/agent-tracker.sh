#!/usr/bin/env bash
# tools/agent-tracker/agent-tracker.sh
# Real-time tmux agent dashboard — reads from sidecar files (push model)
#
# Claude Code panes: data pushed by hooks → .workspace/agent-tracker/{pane_id}.json
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
ORCH_DIR="${ORCH_DIR:-"$REPO_ROOT/.workspace/orchestrate"}"
SIDECAR_DIR="$REPO_ROOT/.workspace/agent-tracker"

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
  local char="$1" n="$2" s="" i
  for ((i = 0; i < n; i++)); do s+="$char"; done
  printf '%s' "$s"
}

# display_width <string> — terminal display columns (CJK=2, ASCII=1)
# ASCII fast path avoids subshell for pure-ASCII strings (#30)
display_width() {
  local s="$1"
  if [[ "$s" != *[^[:ascii:]]* ]]; then
    printf '%d' "${#s}"
  else
    printf '%s' "$s" | wc -L
  fi
}

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
  local pct="$1" color="$2" bar="" i
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
    done)         printf "${BLUE}✓ done${R}" ;;
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
      .activity // "",
      (.updated_at // 0 | tostring)
    ] | join("\u001e")' "$sidecar_path" 2>/dev/null)

    if [[ -n "$raw" ]]; then
      local updated_at
      IFS=$'\x1e' read -r model status pct tok_k task activity updated_at <<< "$raw"

      # Stale sidecar detection: if not updated for 30s and status is non-idle,
      # the agent likely crashed without sending SessionEnd. Reset to idle. (#47)
      if [[ "$status" != "idle" && -n "$updated_at" && "$updated_at" != "0" ]]; then
        local now_epoch age
        now_epoch=$(date +%s)
        age=$(( now_epoch - ${updated_at%.*} ))
        if (( age > 30 )); then
          status="idle"
          activity=""
        fi
      fi
    fi

    # Only scrape pane when sidecar status is idle — prevents spinner false
    # positives (spinner chars in code/output overriding non-idle sidecar
    # status) and skips unnecessary capture-pane when already working (#30, #31)
    if [[ "$status" == "idle" ]]; then
      local captured bottom8
      captured=$(tmux capture-pane -p -t "$pane_id" -S -8 2>/dev/null)
      bottom8=$(printf '%s' "$captured" | tail -8)
      if printf '%s' "$bottom8" | grep -qE '✢|✶|✻|✽|⠋|⠙|⠹|⠸|⠼|⠴|⠦|⠧|⠇|⠏'; then
        status="working"
      elif printf '%s' "$bottom8" | grep -qE '⏸|plan mode'; then
        status="plan"
      fi
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
    # Merge all jq queries into a single pass over the session file (#30)
    local raw_jq
    raw_jq=$(jq -rs '
      def last_ne(f): [.[] | f | select(. != null and . != "")] | if length == 0 then null else last end;
      {
        model:     last_ne(select(.type == "turn_context") | .payload.model),
        total_tok: last_ne(select(.payload.info | type == "object") | .payload.info.total_token_usage.total_tokens | tostring),
        ctx_win:   last_ne(select(.payload.info | type == "object") | .payload.info.model_context_window | tostring),
        msg:       (last_ne(select(.payload.type == "user_message") | .payload.message)
                   // last_ne(select(.type == "response_item" and .payload.role == "user") | .payload.content // .payload.message))
      } | [(.model // ""), (.total_tok // ""), (.ctx_win // ""), (.msg // "")] | join("\u001e")
    ' "$session_file" 2>/dev/null)

    if [[ -n "$raw_jq" ]]; then
      local raw_model raw_total_tok raw_ctx_win raw_msg
      IFS=$'\x1e' read -r raw_model raw_total_tok raw_ctx_win raw_msg <<< "$raw_jq"
      [[ -n "$raw_model" ]] && model="$raw_model"
      local ctx_window="${raw_ctx_win:-200000}"
      [[ -z "$ctx_window" || "$ctx_window" -le 0 ]] 2>/dev/null && ctx_window=200000
      if [[ -n "$raw_total_tok" && "$raw_total_tok" -gt 0 ]] 2>/dev/null; then
        pct=$(( raw_total_tok * 100 / ctx_window ))
        (( pct > 100 )) && pct=100
        tok_k=$(( raw_total_tok / 1000 ))
      fi
      [[ -n "$raw_msg" ]] && task="$raw_msg"
    fi
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
# Orchestrator batch rendering (#59)
# ─────────────────────────────────────────────────────────────────────────────

# _orch_elapsed <seconds> — compact elapsed time
_orch_elapsed() {
  local s=$1
  (( s < 0 )) && s=0
  if (( s >= 3600 )); then
    printf '%dh%02dm' $(( s / 3600 )) $(( (s % 3600) / 60 ))
  elif (( s >= 60 )); then
    printf '%dm%02ds' $(( s / 60 )) $(( s % 60 ))
  else
    printf '%ds' "$s"
  fi
}

# _orch_badge <type> — 6 visible chars, colored
_orch_badge() {
  case "$1" in
    run)   printf "${GREEN}● run ${R}" ;;
    done)  printf "${BLUE}✓ done${R}" ;;
    stop)  printf "${ROSE}✖ stop${R}" ;;
    *)     printf "${GRAY}○ --- ${R}" ;;
  esac
}

# render_orchestrator <INNER> — render all orchestrator batch sections
# Called from render_dashboard after the agent footer, before bottom border.
# Auto-detects batches via .workspace/orchestrate/*/batch.state.json.
render_orchestrator() {
  local INNER=$1

  local -a batch_files=()
  for f in "$ORCH_DIR"/*/batch.state.json; do
    [[ -f "$f" ]] || continue
    batch_files+=("$f")
  done
  (( ${#batch_files[@]} == 0 )) && return

  # Cache ps output once for subprocess detection
  local ps_cache
  ps_cache=$(ps aux 2>/dev/null | grep "claude -p" | grep -v grep || true)

  # Column widths: ISSUE(7) STEP(13) STATUS(6) TIME(7) INFO(rest)
  # overhead: 2(left pad) + 4(column separators) + 2(right pad) = 8
  local W_ISS=7 W_STEP=13 W_STAT=6 W_TIME=7
  local W_INFO=$(( INNER - W_ISS - W_STEP - W_STAT - W_TIME - 8 ))
  (( W_INFO < 10 )) && W_INFO=10

  local now_epoch
  now_epoch=$(date +%s)

  for batch_file in "${batch_files[@]}"; do
    local state
    state=$(cat "$batch_file" 2>/dev/null) || continue

    # Extract metadata + dispatched list in a single jq pass
    local combined
    combined=$(printf '%s' "$state" | jq -r '
      def cnt(v): [.status | to_entries[] | select(.value == v)] | length | tostring;
      [
        .area, .batchId,
        cnt("completed"), cnt("dispatched"), cnt("pending"), cnt("blocked"), cnt("failed"),
        (.issues | length | tostring),
        (.orchestratorPid // 0 | tostring),
        (.orchestratorStartedAt // ""),
        (. as $root | [.dispatched | to_entries[]
          | select($root.status[.key] == "dispatched")
          | [.key, (.value.pid // 0 | tostring), (.value.dispatchedAt // "")]
          | join("\u001e")] | sort | join("\n"))
      ] | join("\u001f")' 2>/dev/null)

    local meta dispatched_data
    IFS=$'\x1f' read -r meta dispatched_data <<< "$combined"

    local area batch_id n_done n_active n_pending n_blocked n_failed n_total orch_pid orch_started_at
    IFS=$'\x1e' read -r area batch_id n_done n_active n_pending n_blocked n_failed n_total orch_pid orch_started_at <<< "$meta"

    # ── Batch liveness detection ──
    # Check orchestrator process: PID alive + start time match (guards PID reuse)
    local batch_status="stopped"
    local n_terminal=$(( n_done + n_failed ))
    if (( n_terminal >= n_total )); then
      batch_status="done"
    elif [[ -n "$orch_pid" && "$orch_pid" != "0" && "$orch_pid" != "null" ]]; then
      if kill -0 "$orch_pid" 2>/dev/null; then
        local current_starttime
        current_starttime=$(awk '{print $22}' /proc/"$orch_pid"/stat 2>/dev/null)
        if [[ "$current_starttime" == "$orch_started_at" ]]; then
          batch_status="active"
        fi
      fi
    fi

    # ── Section separator ──
    printf "${GRAY}╠%s╣${R}" "$_CACHE_eqline"; tput el; echo

    # ── Header ──
    local h_left="⚙ Orchestrator: ${area}"
    local h_right="${n_done}/${n_total} done  ${batch_id}"
    local hgap=$(( INNER - 4 - ${#h_left} - ${#h_right} ))
    (( hgap < 1 )) && hgap=1

    local h_color="$GOLD"
    [[ "$batch_status" == "done" ]] && h_color="$BLUE"
    [[ "$batch_status" == "stopped" ]] && h_color="$ROSE"

    printf "${GRAY}║${R}  ${BOLD}${h_color}%s${R}%*s${GRAY}%s${R}  ${GRAY}║${R}" \
      "$h_left" "$hgap" "" "$h_right"
    tput el; echo

    printf "${GRAY}║${R}%*s${GRAY}║${R}" "$INNER" ""; tput el; echo

    # ── Dispatched issues (already extracted in combined jq above) ──
    if [[ -n "$dispatched_data" ]]; then
      # Column headers
      printf "${GRAY}║${R}  ${DARK}%s %s %s %s %s${R}  ${GRAY}║${R}" \
        "$(pad_right "ISSUE" $W_ISS)" "$(pad_right "STEP" $W_STEP)" \
        "$(pad_right "STATUS" $W_STAT)" "$(pad_right "TIME" $W_TIME)" \
        "$(pad_right "INFO" $W_INFO)"
      tput el; echo

      printf "${GRAY}║${R}  ${DARK}%s %s %s %s %s${R}  ${GRAY}║${R}" \
        "$(make_line '─' $W_ISS)" "$(make_line '─' $W_STEP)" \
        "$(make_line '─' $W_STAT)" "$(make_line '─' $W_TIME)" \
        "$(make_line '─' $W_INFO)"
      tput el; echo

      while IFS=$'\x1e' read -r issue pid dispatched_at; do
        [[ -z "$issue" ]] && continue

        # Pipeline state for step + PR
        local step="—" pr_num="" pr_display="—"
        local pf="$PIPELINE_DIR/${area}/issue-${issue}.state.json"
        if [[ -f "$pf" ]]; then
          local praw
          praw=$(jq -r '[.step // "—", (.pr // 0 | tostring)] | join("\u001e")' "$pf" 2>/dev/null)
          IFS=$'\x1e' read -r step pr_num <<< "$praw"
          [[ -n "$pr_num" && "$pr_num" != "0" ]] && pr_display="PR #${pr_num}"
        fi

        # Process alive check
        local alive=0
        [[ -n "$pid" && "$pid" != "0" && "$pid" != "null" ]] && kill -0 "$pid" 2>/dev/null && alive=1

        # Elapsed time
        local etime="—"
        if [[ -n "$dispatched_at" ]]; then
          local ts
          ts=$(date -d "$dispatched_at" +%s 2>/dev/null)
          [[ -n "$ts" ]] && etime=$(_orch_elapsed $(( now_epoch - ts )))
        fi

        # Issue row
        printf "${GRAY}║${R}  "
        printf "%s " "$(pad_right "#${issue}" $W_ISS)"
        printf "%s " "$(trunc "$step" $W_STEP)"
        printf "%b " "$( (( alive )) && _orch_badge run || _orch_badge stop)"
        printf "%s " "$(pad_right "$etime" $W_TIME)"
        printf "%s  " "$(trunc "$pr_display" $W_INFO)"
        printf "${GRAY}║${R}"
        tput el; echo

        # Subprocess detection (review/resolve)
        if [[ -n "$pr_num" && "$pr_num" != "0" && -n "$ps_cache" ]]; then
          local sub_line
          sub_line=$(printf '%s' "$ps_cache" \
            | grep -E "dev-(review|resolve)" | grep "PR #${pr_num} " \
            | grep -v timeout | head -1)

          if [[ -n "$sub_line" ]]; then
            local sub_pid sub_type
            sub_pid=$(printf '%s' "$sub_line" | awk '{print $2}')
            if printf '%s' "$sub_line" | grep -q "dev-review"; then
              sub_type="review"
            else
              sub_type="resolve"
            fi

            local sub_alive=0
            kill -0 "$sub_pid" 2>/dev/null && sub_alive=1

            local sub_etime="—"
            local sub_secs
            sub_secs=$(ps -o etimes= -p "$sub_pid" 2>/dev/null | tr -d ' ')
            [[ -n "$sub_secs" ]] && sub_etime=$(_orch_elapsed "$sub_secs")

            printf "${GRAY}║${R}  "
            printf "${DARK}%s${R} " "$(pad_right "  └─" $W_ISS)"
            printf "%s " "$(trunc "/dev-${sub_type}" $W_STEP)"
            printf "%b " "$( (( sub_alive )) && _orch_badge run || _orch_badge stop)"
            printf "%s " "$(pad_right "$sub_etime" $W_TIME)"
            printf "%s  " "$(trunc "PID ${sub_pid}" $W_INFO)"
            printf "${GRAY}║${R}"
            tput el; echo
          fi
        fi
      done <<< "$dispatched_data"
    else
      local no_msg="  No dispatched issues"
      printf "${GRAY}║${R}%-*s${GRAY}║${R}" "$INNER" "$no_msg"
      tput el; echo
    fi

    printf "${GRAY}║${R}%*s${GRAY}║${R}" "$INNER" ""; tput el; echo

    # ── Orchestrator footer ──
    local of="${BLUE}✓${R} ${GRAY}${n_done} done${R}"
    of+="  ${GREEN}●${R} ${GRAY}${n_active} active${R}"
    of+="  ${GOLD}○${R} ${GRAY}${n_pending} pending${R}"
    of+="  ${DARK}◆${R} ${GRAY}${n_blocked} blocked${R}"
    (( n_failed > 0 )) && of+="  ${ROSE}✖${R} ${GRAY}${n_failed} failed${R}"

    local of_plain="✓ ${n_done} done  ● ${n_active} active  ○ ${n_pending} pending  ◆ ${n_blocked} blocked"
    (( n_failed > 0 )) && of_plain+="  ✖ ${n_failed} failed"

    # Append batch status indicator
    local batch_label=""
    local batch_label_plain=""
    if [[ "$batch_status" == "done" ]]; then
      batch_label="${BLUE}[DONE]${R}"
      batch_label_plain="[DONE]"
    elif [[ "$batch_status" == "stopped" ]]; then
      batch_label="${ROSE}[STOPPED]${R}"
      batch_label_plain="[STOPPED]"
    fi

    local bl_extra=0
    (( ${#batch_label_plain} > 0 )) && bl_extra=$(( ${#batch_label_plain} + 2 ))
    local fp=$(( INNER - 4 - ${#of_plain} - bl_extra ))
    (( fp < 0 )) && fp=0
    if [[ -n "$batch_label" ]]; then
      printf "${GRAY}║${R}  %b%*s%b  ${GRAY}║${R}" "$of" "$fp" "" "$batch_label"
    else
      printf "${GRAY}║${R}  %b%*s  ${GRAY}║${R}" "$of" "$fp" ""
    fi
    tput el; echo
  done
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
# No cache — re-detects each cycle so dynamic pane changes (agent start/stop)
# are reflected immediately. Cost is negligible (~50 /proc reads/sec). (#47)
detect_agent_type() {
  local root_pid="$1"
  local pids=() queue=("$root_pid") pid child cmdline exename result

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
    result=$(_match_agent "$cmdline" "$exename") && {
      printf '%s' "$result"
      return 0
    }
  done
  return 1
}

# ─────────────────────────────────────────────────────────────────────────────
# Dashboard renderer
# ─────────────────────────────────────────────────────────────────────────────

# Cached border/header strings — only recalculated when terminal width changes (#30)
_PREV_COLS=-1
_CACHE_eqline=""
_CACHE_h_pane="" _CACHE_h_engine="" _CACHE_h_status="" _CACHE_h_tokens=""
_CACHE_d_pane="" _CACHE_d_engine="" _CACHE_d_status="" _CACHE_d_tokens=""

render_dashboard() {
  local COLS
  COLS=$(tput cols 2>/dev/null || echo 100)
  (( COLS < 86 )) && COLS=86
  local INNER=$(( COLS - 2 ))

  local W_PANE=11 W_ENGINE=12 W_STATUS=6 W_TOKENS_MIN=10
  local W_ACTIVITY_MIN=10

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

    # Detect "(Done) " prefix in task and promote idle → done
    if [[ "$status" == "idle" && "$task" == "(Done) "* ]]; then
      status="done"
    fi

    case "$status" in
      working)      (( n_working++ )) ;;
      plan)         (( n_plan++ ))    ;;
      needs-input)  (( n_working++ )) ;;
      done)         (( n_idle++ ))    ;;
      *)            (( n_idle++ ))    ;;
    esac

    rows+=("$(printf '%s\x1e%s\x1e%s\x1e%s\x1e%s\x1e%s\x1e%s\x1e%s\x1e%s' \
      "$pane_addr" "$pane_id" "$etype" "$model" "$status" "$pct" "$tok_k" "$task" "$activity")")
  done < <(tmux list-panes -s -t "$SESSION" \
    -F '#{window_index}:#{pane_index} #{pane_id} #{pane_current_command}' 2>/dev/null)

  local n_total=${#rows[@]}

  # ── TOKENS column width ────────────────────────────────────────────────────
  local W_TOKENS=$W_TOKENS_MIN
  local _tok_str _tok_w _row_tok_k _row_pct
  for _row in "${rows[@]}"; do
    IFS=$'\x1e' read -r _ _ _ _ _ _row_pct _row_tok_k _ _ <<< "$_row"
    if (( _row_tok_k > 999 )); then _tok_str="999+"; else printf -v _tok_str "%3dk" "$_row_tok_k"; fi
    _tok_w=$(( 5 + 1 + ${#_tok_str} ))
    (( _tok_w > W_TOKENS )) && W_TOKENS=$_tok_w
  done

  # ── ACTIVITY column width — dynamic based on actual content (#32) ──────────
  local W_ACTIVITY=$W_ACTIVITY_MIN
  for _row in "${rows[@]}"; do
    local _r_status _r_activity _act_disp _act_dw
    IFS=$'\x1e' read -r _ _ _ _ _r_status _ _ _ _r_activity <<< "$_row"
    if [[ -z "$_r_activity" || "$_r_activity" == "null" ]]; then
      [[ "$_r_status" == "idle" ]] && _act_disp="— (idle)" || _act_disp="—"
    else
      _act_disp="$_r_activity"
    fi
    _act_dw=$(display_width "$_act_disp")
    (( _act_dw > W_ACTIVITY )) && W_ACTIVITY=$_act_dw
  done
  # Cap W_ACTIVITY so W_TASK always has room for at least 15 chars (#33)
  local W_ACTIVITY_MAX=$(( INNER - W_PANE - W_ENGINE - W_STATUS - W_TOKENS - 9 - 15 ))
  (( W_ACTIVITY_MAX < W_ACTIVITY_MIN )) && W_ACTIVITY_MAX=$W_ACTIVITY_MIN
  (( W_ACTIVITY > W_ACTIVITY_MAX )) && W_ACTIVITY=$W_ACTIVITY_MAX

  # W_TASK: INNER minus all fixed columns and separators.
  # Overhead = left_pad(2) + 5 inter-col separators + trailing_2sp(2) = 9 (#31)
  local W_TASK=$(( INNER - W_PANE - W_ACTIVITY - W_ENGINE - W_STATUS - W_TOKENS - 9 ))
  (( W_TASK < 15 )) && W_TASK=15

  # ── Recalculate fixed-width border strings only when terminal width changes (#30)
  if (( COLS != _PREV_COLS )); then
    _PREV_COLS=$COLS
    _CACHE_eqline=$(make_line '═' "$INNER")

    _CACHE_h_pane=$(pad_right "PANE"    $W_PANE)
    _CACHE_h_engine=$(pad_right "ENGINE" $W_ENGINE)
    _CACHE_h_status=$(pad_right "STATUS" $W_STATUS)
    _CACHE_d_pane=$(make_line '─' $W_PANE)
    _CACHE_d_engine=$(make_line '─' $W_ENGINE)
    _CACHE_d_status=$(make_line '─' $W_STATUS)
  fi

  # Activity/task/tokens headers always reflect current dynamic widths
  local h_activity h_task h_tokens d_activity d_task d_tokens
  h_activity=$(pad_right "ACTIVITY" $W_ACTIVITY)
  h_task=$(pad_right "TASK"         $W_TASK)
  h_tokens=$(pad_right "TOKENS"     $W_TOKENS)
  d_activity=$(make_line '─' $W_ACTIVITY)
  d_task=$(make_line '─'     $W_TASK)
  d_tokens=$(make_line '─'   $W_TOKENS)

  # ── Draw ───────────────────────────────────────────────────────────────────
  tput cup 0 0

  printf "${GRAY}╔%s╗${R}" "$_CACHE_eqline"; tput el; echo

  local title_len=13
  local gap=$(( INNER - 2 - title_len - ${#now} - 1 ))
  (( gap < 1 )) && gap=1
  printf "${GRAY}║${R}  ${BOLD}${BLUE}Agent Tracker${R}${GRAY}%*s%s ${GRAY}║${R}" \
    "$gap" "" "$now"
  tput el; echo

  printf "${GRAY}╠%s╣${R}" "$_CACHE_eqline"; tput el; echo

  printf "${GRAY}║${R}%*s${GRAY}║${R}" "$INNER" ""; tput el; echo

  printf "${GRAY}║${R}  ${DARK}%s %s %s %s %s %s${R}  ${GRAY}║${R}" \
    "$_CACHE_h_pane" "$h_task" "$h_activity" "$_CACHE_h_engine" "$_CACHE_h_status" "$h_tokens"
  tput el; echo

  printf "${GRAY}║${R}  ${DARK}%s %s %s %s %s %s${R}  ${GRAY}║${R}" \
    "$_CACHE_d_pane" "$d_task" "$d_activity" "$_CACHE_d_engine" "$_CACHE_d_status" "$d_tokens"
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

  printf "${GRAY}╠%s╣${R}" "$_CACHE_eqline"; tput el; echo

  local n_stat="(${n_working} working"
  (( n_plan > 0 )) && n_stat+=", ${n_plan} plan"
  n_stat+=", ${n_idle} idle)"

  local left_colored="${GREEN}●${R} ${GRAY}Active: ${n_total} agents ${n_stat}${R}"
  local left_plain="● Active: ${n_total} agents ${n_stat}"

  local footer_len=$(( 2 + ${#left_plain} ))
  local fpad=$(( INNER - footer_len - 1 ))
  (( fpad < 0 )) && fpad=0

  printf "${GRAY}║${R}  %b%*s ${GRAY}║${R}" \
    "$left_colored" "$fpad" ""
  tput el; echo

  # Orchestrator batch sections (#59)
  render_orchestrator "$INNER"

  printf "${GRAY}╚%s╝${R}" "$_CACHE_eqline"; tput el; echo

  tput ed
}

# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

# Suppress tput errors when TERM is unset (#31)
tput smcup 2>/dev/null
tput civis 2>/dev/null

# Clean up orphan sidecar files for panes not in the current session (#32)
# Smarter than rm -rf: preserves files for active panes
mkdir -p "$SIDECAR_DIR"
declare -A _active_panes=()
while IFS= read -r _pid; do
  _active_panes["$_pid"]=1
done < <(tmux list-panes -s -t "$SESSION" -F '#{pane_id}' 2>/dev/null | sed 's/^%//')
for _f in "$SIDECAR_DIR"/*.json; do
  [[ -f "$_f" ]] || continue
  _fname="${_f##*/}"
  _pane="${_fname%.json}"
  [[ -z "${_active_panes[$_pane]+x}" ]] && rm -f "$_f"
done
unset _active_panes _fname _pane _f _pid

while true; do
  render_dashboard
  sleep "$INTERVAL"
done
