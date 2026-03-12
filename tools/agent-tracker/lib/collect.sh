#!/usr/bin/env bash
# tools/agent-tracker/lib/collect.sh
# Data collection layer — produces a JSON snapshot.
#
# All data boundaries are JSON. No \x1e/\x1f/newline-based delimiter protocols.
# Text fields are normalized to single-line at collection time.
#
# Output schema:
# {
#   "agents": [{ pane_addr, pane_id, engine, model, status,
#                tokens: { used, total, pct, source, fresh },
#                task, activity }],
#   "orchestrator": [{ area, batch_id, batch_alive, batch_status, n_done, n_failed, n_total,
#                      created_at, elapsed, dispatched: [...] }]
# }
#
# Status enum: idle, working, plan, needs-input, done, error, unknown
# Token source enum: sidecar, scraping, session, unknown
# Token fresh: true = current, false = stale (>30s since last token update)
#
# Source precedence (Claude panes): sidecar > pane scrape > session JSONL
#   sidecar:      written by hooks (push model); most accurate, includes all fields (#109)
#   pane scrape:  tmux capture-pane; used for status inference when sidecar is absent or idle
#   session JSONL: not used for Claude (only Codex panes use session files)
#
# Sidecar v2 namespace: <sidecar_dir>/<socket-hash>/<session>/<pane>.json (#109)

# Codex session file mtime cache for incremental reparse detection (#72)
declare -A _CODEX_CACHE_MTIME=()
declare -A _CODEX_CACHE_DATA=()

# ─────────────────────────────────────────────────────────────────────────────
# Main entry
# ─────────────────────────────────────────────────────────────────────────────

collect_snapshot() {
  local session=$1 sidecar_dir=$2 orch_dir=$3 pipeline_dir=$4

  local agents_json orch_json
  agents_json=$(_collect_agents "$session" "$sidecar_dir")
  orch_json=$(_collect_orchestrator "$orch_dir" "$pipeline_dir")

  jq -nc \
    --argjson agents "${agents_json:-[]}" \
    --argjson orch "${orch_json:-[]}" \
    '{agents: $agents, orchestrator: $orch}'
}

# ─────────────────────────────────────────────────────────────────────────────
# Agent collection
# ─────────────────────────────────────────────────────────────────────────────

_collect_agents() {
  local session=$1 sidecar_dir=$2
  local -a records=()

  # Compute socket hash for v2 namespace ($TMUX: socket_path,server_pid,session_id)
  local _socket_hash="default"
  if [[ -n "${TMUX:-}" ]]; then
    _socket_hash=$(printf '%s' "${TMUX%%,*}" | md5sum | cut -c1-6)
  fi

  local pane_list
  pane_list=$(tmux list-panes -s -t "$session" \
    -F '#{window_index}:#{pane_index} #{pane_id} #{pane_current_command}' 2>/dev/null) || {
    printf '[]'
    return
  }

  while IFS=' ' read -r pane_addr pane_id pane_cmd; do
    [[ -z "$pane_addr" ]] && continue

    local etype="" _pane_tty=""
    case "$pane_cmd" in
      claude) etype="claude" ;;
      codex)  etype="codex"  ;;
      *)
        _pane_tty=$(tmux display-message -t "$pane_id" -p '#{pane_tty}' 2>/dev/null) || continue
        local _tty_procs
        _tty_procs=$(ps -t "${_pane_tty#/dev/}" -o comm= 2>/dev/null) || continue
        if printf '%s\n' "$_tty_procs" | grep -qx 'claude'; then
          etype="claude"
        elif printf '%s\n' "$_tty_procs" | grep -qx 'codex'; then
          etype="codex"
        else
          continue
        fi ;;
    esac

    local record
    if [[ "$etype" == "claude" ]]; then
      record=$(_collect_claude_pane "$pane_id" "$sidecar_dir" "$pane_addr" "$session" "$_socket_hash")
    else
      record=$(_collect_codex_pane "$pane_id" "$_pane_tty" "$pane_addr")
    fi
    [[ -n "$record" ]] && records+=("$record")
  done <<< "$pane_list"

  if (( ${#records[@]} == 0 )); then
    printf '[]'
  else
    printf '%s\n' "${records[@]}" | jq -sc '.'
  fi
}

# ─────────────────────────────────────────────────────────────────────────────
# Claude pane collector
# ─────────────────────────────────────────────────────────────────────────────

_collect_claude_pane() {
  local pane_id=$1 sidecar_dir=$2 pane_addr=$3 session=${4:-} socket_hash=${5:-default}

  # Path traversal guard: pane_id must be %N (digits only) (#108)
  [[ ! "$pane_id" =~ ^%[0-9]+$ ]] && return

  local pane_file="${pane_id#%}"
  # v2 namespace: <sidecar_dir>/<socket-hash>/<session>/<pane>.json (#109)
  local sidecar_path="${sidecar_dir}/${socket_hash}/${session}/${pane_file}.json"

  local model="unknown" status="idle" task="-" activity=""
  local tok_used=0 tok_total=0 tok_pct=0 tok_source="unknown" tok_fresh=true

  if [[ -f "$sidecar_path" ]]; then
    # Read sidecar: single jq call, normalize text to single-line.
    # Use RS=\x1e (non-whitespace) so empty fields are never collapsed by read (#108).
    # task/activity are base64-encoded to survive any control chars in values (#108).
    # Includes tokens_updated_at for independent token freshness tracking (#74).
    local raw
    raw=$(jq -r '[
      (.model // "unknown"),
      (.status // "idle"),
      (.tokens.pct // 0 | tostring),
      (.tokens.used // 0 | tostring),
      (.tokens.max // 0 | tostring),
      ((.task // "-") | gsub("[\\n\\r]"; " ") | gsub("  +"; " ") | @base64),
      ((.activity // "") | gsub("[\\n\\r]"; " ") | gsub("  +"; " ") | @base64),
      (.updated_at // 0 | tostring),
      (.tokens_updated_at // 0 | tostring)
    ] | join("\u001e")' "$sidecar_path" 2>/dev/null)

    if [[ -n "$raw" ]]; then
      local updated_at tokens_updated_at _task_b64 _act_b64
      IFS=$'\x1e' read -r model status tok_pct tok_used tok_total \
        _task_b64 _act_b64 updated_at tokens_updated_at <<< "$raw"
      task=$(printf '%s' "$_task_b64" | base64 -d 2>/dev/null)
      activity=$(printf '%s' "$_act_b64" | base64 -d 2>/dev/null)

      tok_source="sidecar"

      local now_epoch
      now_epoch=$(date +%s)

      # Token freshness: use tokens_updated_at if available, else fall back to updated_at (#74)
      local tok_ts="${tokens_updated_at:-0}"
      [[ "$tok_ts" == "0" || "$tok_ts" == "null" || -z "$tok_ts" ]] && tok_ts="${updated_at:-0}"
      if [[ -n "$tok_ts" && "$tok_ts" != "0" && "$tok_ts" != "null" ]]; then
        local tok_age=$(( now_epoch - ${tok_ts%.*} ))
        (( tok_age > STALE_THRESHOLD_SECS )) && tok_fresh=false
      fi

      # Zero tokens → no token data present yet; source unknown (#108)
      if [[ "$tok_used" == "0" && "$tok_total" == "0" ]]; then
        tok_source="unknown"
      fi

      # Status staleness: non-idle/non-done without recent update → stale (#47, #108)
      if [[ "$status" != "idle" && "$status" != "done" && \
            -n "$updated_at" && "$updated_at" != "0" ]]; then
        local age=$(( now_epoch - ${updated_at%.*} ))
        if (( age > STALE_THRESHOLD_SECS )); then
          status="stale"
          activity=""
        fi
      fi
    else
      # jq failed to parse sidecar → fault (partial write / corrupt) (#108)
      status="fault"
    fi

    # Augment idle status from pane scraping (spinner detection)
    if [[ "$status" == "idle" ]]; then
      local pane_status
      pane_status=$(_infer_status_from_pane "$pane_id" 8)
      [[ -n "$pane_status" ]] && status="$pane_status"
    fi
  else
    # No sidecar: full pane scraping fallback
    local pane_status
    pane_status=$(_infer_status_from_pane "$pane_id" 8)
    [[ -n "$pane_status" ]] && status="$pane_status"

    # Token % from scraping — extract actual window size (#72)
    local captured
    captured=$(tmux capture-pane -p -t "$pane_id" -S -50 2>/dev/null)
    if [[ -n "$captured" ]]; then
      local tok tok_total_k
      tok=$(printf '%s' "$captured" \
        | grep -oE '[0-9]+% of [0-9]+k tokens' | tail -1)
      if [[ -n "$tok" ]]; then
        tok_pct=$(printf '%s' "$tok" | grep -oE '^[0-9]+')
        tok_total_k=$(printf '%s' "$tok" | grep -oE 'of [0-9]+k' | grep -oE '[0-9]+')
        if [[ -n "$tok_total_k" && -n "$tok_pct" ]]; then
          tok_total=$(( tok_total_k * 1000 ))
          tok_used=$(( tok_pct * tok_total / 100 ))
          tok_source="scraping"
        fi
      fi
      # If no match: tok_source stays "unknown", values stay 0

      # Task from scraping
      local ptask
      ptask=$(printf '%s' "$captured" | grep -o '.*' | sed 's/.*💬 //' | tail -1)
      [[ -n "$ptask" ]] && task="$ptask"

      # Model from scraping
      local pane_model
      pane_model=$(printf '%s' "$captured" \
        | grep -oE '(Opus|Sonnet|Haiku)[[:space:]]+[0-9]+\.[0-9]+' | tail -1)
      [[ -n "$pane_model" ]] && model="$pane_model"
    fi
  fi

  # Status promotion: "(Done) " prefix → done; unconditional so pane-scrape
  # spinner cannot mask a completed task (#108)
  if [[ "$task" == "(Done) "* ]]; then
    status="done"
  fi

  # Final text normalization (belt-and-suspenders for any path)
  task=$(printf '%s' "$task" | tr '\n\t\r' '   ' | sed 's/  */ /g')
  activity=$(printf '%s' "$activity" | tr '\n\t\r' '   ' | sed 's/  */ /g')

  _emit_agent_json "$pane_addr" "$pane_id" "claude" "$model" "$status" \
    "$tok_used" "$tok_total" "$tok_pct" "$tok_source" "$tok_fresh" "$task" "$activity"
}

# ─────────────────────────────────────────────────────────────────────────────
# Shared agent JSON output
# ─────────────────────────────────────────────────────────────────────────────

_emit_agent_json() {
  local pane_addr=$1 pane_id=$2 engine=$3 model=$4 status=$5
  local tok_used=$6 tok_total=$7 tok_pct=$8 tok_source=$9 tok_fresh=${10}
  local task=${11} activity=${12}
  jq -nc \
    --arg pa "$pane_addr $pane_id" \
    --arg pi "$pane_id" \
    --arg e "$engine" \
    --arg m "$model" \
    --arg s "$status" \
    --argjson tu "${tok_used:-0}" \
    --argjson tt "${tok_total:-0}" \
    --argjson tp "${tok_pct:-0}" \
    --arg ts "$tok_source" \
    --argjson tf "$tok_fresh" \
    --arg ta "$task" \
    --arg ac "$activity" \
    '{pane_addr:$pa, pane_id:$pi, engine:$e, model:$m, status:$s,
      tokens:{used:$tu, total:$tt, pct:$tp, source:$ts, fresh:$tf},
      task:$ta, activity:$ac}'
}

# ─────────────────────────────────────────────────────────────────────────────
# Pane status inference (spinner/plan mode detection)
# ─────────────────────────────────────────────────────────────────────────────

_infer_status_from_pane() {
  local pane_id=$1 lines=${2:-8}
  local captured bottom
  captured=$(tmux capture-pane -p -t "$pane_id" -S "-$lines" 2>/dev/null) || return
  bottom=$(printf '%s' "$captured" | tail -"$lines")

  if printf '%s' "$bottom" | grep -qE '✢|✶|✻|✽|⠋|⠙|⠹|⠸|⠼|⠴|⠦|⠧|⠇|⠏'; then
    printf 'working'
  elif printf '%s' "$bottom" | grep -qE '⏸|plan mode'; then
    printf 'plan'
  fi
}

# ─────────────────────────────────────────────────────────────────────────────
# Codex pane collector
# ─────────────────────────────────────────────────────────────────────────────

_find_codex_session_file() {
  local pane_id="$1" pane_tty="${2:-}"
  local codex_pid session_file

  [[ -z "$pane_tty" ]] && pane_tty=$(tmux display-message -t "$pane_id" -p '#{pane_tty}' 2>/dev/null)
  [[ -z "$pane_tty" ]] && return

  codex_pid=$(ps -t "${pane_tty#/dev/}" -o pid=,comm= 2>/dev/null \
    | awk '$2=="codex" {print $1; exit}')
  [[ -z "$codex_pid" ]] && return

  if [[ -d "/proc/$codex_pid/fd" ]]; then
    session_file=$(readlink -f /proc/"$codex_pid"/fd/* 2>/dev/null \
      | grep -E '\.codex/sessions.*\.jsonl$' | head -1)
    [[ -n "$session_file" ]] && printf '%s' "$session_file"
  fi
}

_collect_codex_pane() {
  local pane_id=$1 pane_tty=${2:-} pane_addr=$3

  local model="Codex" status="idle" task="-" activity=""
  local tok_used=0 tok_total=0 tok_pct=0 tok_source="unknown" tok_fresh=true

  local session_file
  session_file=$(_find_codex_session_file "$pane_id" "$pane_tty")

  if [[ -n "$session_file" && -f "$session_file" ]]; then
    # Mtime-based cache: skip full reparse if file unchanged (#72)
    local file_stat cache_key
    cache_key="$session_file"
    file_stat=$(stat -c '%Y_%s' "$session_file" 2>/dev/null)

    local cached_stat="${_CODEX_CACHE_MTIME[$cache_key]:-}"
    if [[ "$file_stat" == "$cached_stat" && -n "${_CODEX_CACHE_DATA[$cache_key]:-}" ]]; then
      # Cache hit
      IFS=$'\t' read -r model tok_used tok_total task <<< "${_CODEX_CACHE_DATA[$cache_key]}"
    else
      # Cache miss: full parse with single jq call.
      # Coherent snapshot: used+total extracted from same .payload.info event (#74).
      # Text fields normalized to single-line via gsub.
      local raw_jq
      raw_jq=$(jq -rs '
        def last_ne(f): [.[] | f | select(. != null and . != "")] | if length == 0 then null else last end;
        (
          [.[] | select(.payload.info | type == "object") |
            { used: .payload.info.total_token_usage.total_tokens,
              total: .payload.info.model_context_window } |
            select(.used != null and .total != null)
          ] | if length == 0 then null else last end
        ) as $tok_pair |
        {
          model: last_ne(select(.type == "turn_context") | .payload.model),
          tok_used:  ($tok_pair.used // 0),
          tok_total: ($tok_pair.total // 0),
          msg:   (last_ne(select(.payload.type == "user_message") | .payload.message)
                 // last_ne(select(.type == "response_item" and .payload.role == "user") | .payload.content // .payload.message))
        } | [
          (.model // ""),
          (.tok_used | tostring),
          (.tok_total | tostring),
          ((.msg // "") | gsub("[\\n\\t\\r]"; " ") | gsub("  +"; " "))
        ] | @tsv
      ' "$session_file" 2>/dev/null)

      if [[ -n "$raw_jq" ]]; then
        local raw_model raw_tok_used raw_tok_total raw_msg
        IFS=$'\t' read -r raw_model raw_tok_used raw_tok_total raw_msg <<< "$raw_jq"
        [[ -n "$raw_model" ]] && model="$raw_model"
        [[ -n "$raw_tok_used" ]] && tok_used="$raw_tok_used"
        [[ -n "$raw_tok_total" ]] && tok_total="$raw_tok_total"
        [[ -n "$raw_msg" ]] && task="$raw_msg"

        # Update cache with new data
        _CODEX_CACHE_MTIME[$cache_key]="$file_stat"
        _CODEX_CACHE_DATA[$cache_key]=$(printf '%s\t%s\t%s\t%s' "$model" "$tok_used" "$tok_total" "$task")
      else
        # Parse failed (partial JSONL write): use last-good cache if available (#74)
        if [[ -n "${_CODEX_CACHE_DATA[$cache_key]:-}" ]]; then
          IFS=$'\t' read -r model tok_used tok_total task <<< "${_CODEX_CACHE_DATA[$cache_key]}"
          tok_fresh=false  # Stale since we couldn't read current data
        fi
        # Don't update cache - keep last-good state
      fi
    fi

    # Compute pct from coherent used/total pair (#74)
    if [[ -n "$tok_total" && "$tok_total" -gt 0 ]] 2>/dev/null; then
      if [[ -n "$tok_used" && "$tok_used" -gt 0 ]] 2>/dev/null; then
        tok_pct=$(( tok_used * 100 / tok_total ))
        (( tok_pct > 100 )) && tok_pct=100
      fi
      tok_source="session"
    fi
  fi

  # Pane scraping for status
  local captured bottom5
  captured=$(tmux capture-pane -p -t "$pane_id" -S -5 2>/dev/null)
  bottom5=$(printf '%s' "$captured" | tail -5)
  if printf '%s' "$bottom5" \
      | grep -qE '[⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏]|Working\.\.\.|Generating'; then
    status="working"
  fi

  # Final text normalization
  task=$(printf '%s' "$task" | tr '\n\t\r' '   ' | sed 's/  */ /g')

  _emit_agent_json "$pane_addr" "$pane_id" "codex" "$model" "$status" \
    "$tok_used" "$tok_total" "$tok_pct" "$tok_source" "$tok_fresh" "$task" "$activity"
}

# ─────────────────────────────────────────────────────────────────────────────
# PID liveness check with starttime verification
# ─────────────────────────────────────────────────────────────────────────────

_check_pid_alive() {
  # Usage: _check_pid_alive <pid> <stored_starttime>
  # Returns 0 if alive and starttime matches, 1 otherwise.
  local pid=$1 stored_start=${2:-}

  [[ -z "$pid" || "$pid" == "0" || "$pid" == "null" ]] && return 1
  kill -0 "$pid" 2>/dev/null || return 1

  # PID reuse protection: verify /proc/PID/stat field 22 (starttime)
  if [[ -n "$stored_start" && "$stored_start" != "null" && "$stored_start" != "" ]]; then
    local cur_start
    cur_start=$(awk '{print $22}' /proc/"$pid"/stat 2>/dev/null) || return 1
    [[ "$cur_start" != "$stored_start" ]] && return 1
  fi

  return 0
}

# ─────────────────────────────────────────────────────────────────────────────
# Orchestrator collection
# ─────────────────────────────────────────────────────────────────────────────

_collect_orchestrator() {
  local orch_dir=$1 pipeline_dir=$2
  local -a records=()

  local -a batch_files=()
  for f in "$orch_dir"/*/batch.state.json; do
    [[ -f "$f" ]] || continue
    batch_files+=("$f")
  done
  (( ${#batch_files[@]} == 0 )) && { printf '[]'; return; }

  # Cache ps output once for subprocess detection
  local ps_cache
  ps_cache=$(ps aux 2>/dev/null | grep "claude -p" | grep -v grep || true)

  local now_epoch
  now_epoch=$(date +%s)

  for batch_file in "${batch_files[@]}"; do
    [[ -f "$batch_file" ]] || continue

    # ── Extract metadata: single jq call, @tsv output (#72) ──
    # Previously used \x1f join with 2-variable read → only area was captured.
    # Now uses @tsv: all fields in one tab-separated line, read into all variables.
    local meta_tsv
    meta_tsv=$(jq -r '
      def cnt(v): [.status | to_entries[] | select(.value == v)] | length;
      [
        .area,
        .batchId,
        (cnt("completed") | tostring),
        (cnt("dispatched") | tostring),
        (cnt("pending") | tostring),
        (cnt("blocked") | tostring),
        (cnt("failed") | tostring),
        (.issues | length | tostring),
        (.orchestratorPid // 0 | tostring),
        (.orchestratorStartedAt // ""),
        (.createdAt // "")
      ] | @tsv
    ' "$batch_file" 2>/dev/null) || continue

    [[ -z "$meta_tsv" ]] && continue

    local area batch_id n_done n_active n_pending n_blocked n_failed n_total \
          orch_pid orch_started_at created_at
    IFS=$'\t' read -r area batch_id n_done n_active n_pending n_blocked n_failed \
      n_total orch_pid orch_started_at created_at <<< "$meta_tsv"

    # ── Batch liveness — dead PIDs are shown explicitly, not hidden (#108) ──
    local batch_alive=true
    _check_pid_alive "$orch_pid" "$orch_started_at" || batch_alive=false

    local n_terminal=$(( n_done + n_failed ))
    local batch_status="active"
    if ! $batch_alive; then
      batch_status="dead"
    elif (( n_terminal >= n_total )); then
      batch_status="done"
    fi

    # ── Elapsed ──
    local elapsed_str=""
    if [[ -n "$created_at" && "$created_at" != "null" ]]; then
      local created_ts
      created_ts=$(date -d "$created_at" +%s 2>/dev/null)
      [[ -n "$created_ts" ]] && elapsed_str=$(_orch_elapsed $(( now_epoch - created_ts )))
    fi

    # ── Dispatched issues: separate jq call, @tsv per row (#72) ──
    # Previously used \x1e join inside \x1f join → nested delimiter breakage.
    # Now each dispatched issue is a separate @tsv line.
    local dispatched_tsv
    dispatched_tsv=$(jq -r '
      . as $root | .dispatched | to_entries[]
      | select($root.status[.key] == "dispatched")
      | [.key, (.value.pid // 0 | tostring), (.value.dispatchedAt // "")]
      | @tsv
    ' "$batch_file" 2>/dev/null)

    # Build dispatched JSON array
    local -a dispatched_records=()
    if [[ -n "$dispatched_tsv" ]]; then
      while IFS=$'\t' read -r issue pid dispatched_at; do
        [[ -z "$issue" ]] && continue

        # Pipeline state for step + PR
        local step="-" pr_num=0
        local pf="$pipeline_dir/${area}/issue-${issue}.state.json"
        if [[ -f "$pf" ]]; then
          local praw
          praw=$(jq -r '[.step // "-", (.pr // 0 | tostring)] | @tsv' "$pf" 2>/dev/null)
          if [[ -n "$praw" ]]; then
            IFS=$'\t' read -r step pr_num <<< "$praw"
          fi
        fi

        # Process alive check
        local alive=false
        [[ -n "$pid" && "$pid" != "0" && "$pid" != "null" ]] \
          && kill -0 "$pid" 2>/dev/null && alive=true

        # Elapsed time
        local etime=""
        if [[ -n "$dispatched_at" ]]; then
          local ts
          ts=$(date -d "$dispatched_at" +%s 2>/dev/null)
          [[ -n "$ts" ]] && etime=$(_orch_elapsed $(( now_epoch - ts )))
        fi

        # Subprocess detection (review/resolve)
        local sub_json="null"
        if [[ -n "$pr_num" && "$pr_num" != "0" && -n "$ps_cache" ]]; then
          local sub_line
          sub_line=$(printf '%s' "$ps_cache" \
            | grep -E "dev-(review|resolve)" | grep "PR #${pr_num} " \
            | grep -v timeout | head -1)

          if [[ -n "$sub_line" ]]; then
            local sub_pid sub_type sub_alive sub_etime
            sub_pid=$(printf '%s' "$sub_line" | awk '{print $2}')
            if printf '%s' "$sub_line" | grep -q "dev-review"; then
              sub_type="review"
            else
              sub_type="resolve"
            fi
            sub_alive=false
            kill -0 "$sub_pid" 2>/dev/null && sub_alive=true
            sub_etime=""
            local sub_secs
            sub_secs=$(ps -o etimes= -p "$sub_pid" 2>/dev/null | tr -d ' ')
            [[ -n "$sub_secs" ]] && sub_etime=$(_orch_elapsed "$sub_secs")

            sub_json=$(jq -nc \
              --arg t "$sub_type" \
              --argjson a "$sub_alive" \
              --arg e "${sub_etime:-}" \
              --argjson p "$sub_pid" \
              '{type:$t, alive:$a, elapsed:$e, pid:$p}')
          fi
        fi

        dispatched_records+=("$(jq -nc \
          --arg i "$issue" \
          --argjson a "$alive" \
          --arg s "$step" \
          --argjson pr "${pr_num:-0}" \
          --arg e "${etime:-}" \
          --argjson sub "$sub_json" \
          '{issue:$i, alive:$a, step:$s, pr_num:$pr, elapsed:$e, sub:$sub}')")
      done <<< "$dispatched_tsv"
    fi

    local dispatched_array
    if (( ${#dispatched_records[@]} == 0 )); then
      dispatched_array="[]"
    else
      dispatched_array=$(printf '%s\n' "${dispatched_records[@]}" | jq -sc '.')
    fi

    records+=("$(jq -nc \
      --arg area "$area" \
      --arg bid "$batch_id" \
      --arg bs "$batch_status" \
      --argjson nd "${n_done:-0}" \
      --argjson nf "${n_failed:-0}" \
      --argjson nt "${n_total:-0}" \
      --arg ca "${created_at:-}" \
      --arg el "${elapsed_str:-}" \
      --argjson disp "$dispatched_array" \
      '{area:$area, batch_id:$bid, batch_status:$bs,
        n_done:$nd, n_failed:$nf, n_total:$nt,
        created_at:$ca, elapsed:$el, dispatched:$disp}')")
  done

  if (( ${#records[@]} == 0 )); then
    printf '[]'
  else
    printf '%s\n' "${records[@]}" | jq -sc '.'
  fi
}
