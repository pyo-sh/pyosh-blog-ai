#!/usr/bin/env bash
# tools/agent-tracker/lib/collect.sh
# Data collection layer — produces a JSON snapshot.
#
# All data boundaries are JSON. No \x1e/\x1f/newline-based delimiter protocols.
# Text fields are normalized to single-line at collection time.
#
# Output schema:
# {
#   "agents": [{ pane_addr, pane_id, engine, model, status, pct, tok_k, task, activity }],
#   "orchestrator": [{ area, batch_id, batch_alive, batch_status, n_done, n_failed, n_total,
#                      created_at, elapsed, dispatched: [...] }]
# }
#
# Status enum: idle, working, plan, needs-input, done, error, unknown

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
      record=$(_collect_claude_pane "$pane_id" "$sidecar_dir" "$pane_addr")
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
  local pane_id=$1 sidecar_dir=$2 pane_addr=$3
  local pane_file="${pane_id#%}"
  local sidecar_path="${sidecar_dir}/${pane_file}.json"

  local model="Claude" status="idle" pct=0 tok_k=0 task="-" activity=""

  if [[ -f "$sidecar_path" ]]; then
    # Read sidecar: single jq call, normalize text to single-line, output @tsv.
    # jq @tsv properly escapes \t and \n in values, making read safe.
    local raw
    raw=$(jq -r '[
      (.model // "Claude"),
      (.status // "idle"),
      (.tokens.pct // 0 | tostring),
      ((.tokens.used // 0) / 1000 | floor | tostring),
      ((.task // "-") | gsub("[\\n\\t\\r]"; " ") | gsub("  +"; " ")),
      ((.activity // "") | gsub("[\\n\\t\\r]"; " ") | gsub("  +"; " ")),
      (.updated_at // 0 | tostring)
    ] | @tsv' "$sidecar_path" 2>/dev/null)

    if [[ -n "$raw" ]]; then
      local updated_at
      IFS=$'\t' read -r model status pct tok_k task activity updated_at <<< "$raw"

      # Stale sidecar detection: >30s without update + non-idle → reset (#47)
      if [[ "$status" != "idle" && -n "$updated_at" && "$updated_at" != "0" ]]; then
        local now_epoch age
        now_epoch=$(date +%s)
        age=$(( now_epoch - ${updated_at%.*} ))
        if (( age > 30 )); then
          status="idle"
          activity=""
        fi
      fi
    else
      # jq failed to parse sidecar → unknown, not silent idle (#72)
      status="unknown"
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

    # Token % from scraping — extract actual window size, not hardcoded 200k (#72)
    local captured
    captured=$(tmux capture-pane -p -t "$pane_id" -S -50 2>/dev/null)
    if [[ -n "$captured" ]]; then
      local tok tok_total
      tok=$(printf '%s' "$captured" \
        | grep -oE '[0-9]+% of [0-9]+k tokens' | tail -1)
      if [[ -n "$tok" ]]; then
        pct=$(printf '%s' "$tok" | grep -oE '^[0-9]+')
        tok_total=$(printf '%s' "$tok" | grep -oE 'of [0-9]+k' | grep -oE '[0-9]+')
        if [[ -n "$tok_total" && -n "$pct" ]]; then
          tok_k=$(( pct * tok_total / 100 ))
        fi
      fi

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

  # Status promotion: "(Done) " prefix → done
  if [[ "$status" == "idle" && "$task" == "(Done) "* ]]; then
    status="done"
  fi

  # Final text normalization (belt-and-suspenders for any path)
  task=$(printf '%s' "$task" | tr '\n\t\r' '   ' | sed 's/  */ /g')
  activity=$(printf '%s' "$activity" | tr '\n\t\r' '   ' | sed 's/  */ /g')

  # Output JSON record
  jq -nc \
    --arg pa "$pane_addr $pane_id" \
    --arg pi "$pane_id" \
    --arg e "claude" \
    --arg m "$model" \
    --arg s "$status" \
    --argjson p "${pct:-0}" \
    --argjson tk "${tok_k:-0}" \
    --arg ta "$task" \
    --arg ac "$activity" \
    '{pane_addr:$pa, pane_id:$pi, engine:$e, model:$m, status:$s, pct:$p, tok_k:$tk, task:$ta, activity:$ac}'
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

  local model="Codex" status="idle" pct=0 tok_k=0 task="-" activity=""

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
      IFS=$'\t' read -r model tok_k pct task <<< "${_CODEX_CACHE_DATA[$cache_key]}"
    else
      # Cache miss: full parse with single jq call.
      # Text fields normalized to single-line via gsub.
      local raw_jq
      raw_jq=$(jq -rs '
        def last_ne(f): [.[] | f | select(. != null and . != "")] | if length == 0 then null else last end;
        {
          model:     last_ne(select(.type == "turn_context") | .payload.model),
          total_tok: last_ne(select(.payload.info | type == "object") | .payload.info.total_token_usage.total_tokens),
          ctx_win:   last_ne(select(.payload.info | type == "object") | .payload.info.model_context_window),
          msg:       (last_ne(select(.payload.type == "user_message") | .payload.message)
                     // last_ne(select(.type == "response_item" and .payload.role == "user") | .payload.content // .payload.message))
        } | [
          (.model // ""),
          (.total_tok // 0 | tostring),
          (.ctx_win // 0 | tostring),
          ((.msg // "") | gsub("[\\n\\t\\r]"; " ") | gsub("  +"; " "))
        ] | @tsv
      ' "$session_file" 2>/dev/null)

      if [[ -n "$raw_jq" ]]; then
        local raw_model raw_total_tok raw_ctx_win raw_msg
        IFS=$'\t' read -r raw_model raw_total_tok raw_ctx_win raw_msg <<< "$raw_jq"
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

      # Update cache
      _CODEX_CACHE_MTIME[$cache_key]="$file_stat"
      _CODEX_CACHE_DATA[$cache_key]=$(printf '%s\t%s\t%s\t%s' "$model" "$tok_k" "$pct" "$task")
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

  # Output JSON record
  jq -nc \
    --arg pa "$pane_addr $pane_id" \
    --arg pi "$pane_id" \
    --arg e "codex" \
    --arg m "$model" \
    --arg s "$status" \
    --argjson p "${pct:-0}" \
    --argjson tk "${tok_k:-0}" \
    --arg ta "$task" \
    --arg ac "$activity" \
    '{pane_addr:$pa, pane_id:$pi, engine:$e, model:$m, status:$s, pct:$p, tok_k:$tk, task:$ta, activity:$ac}'
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

    # ── Batch liveness ──
    _check_pid_alive "$orch_pid" "$orch_started_at" || continue

    local n_terminal=$(( n_done + n_failed ))
    local batch_status="active"
    (( n_terminal >= n_total )) && batch_status="done"

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
