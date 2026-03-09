#!/bin/bash
# orchestrate-helpers.sh - Shell helpers for dev-orchestrator skill
# Source this file at orchestrator start.
#
# Dispatch model: headless `claude -p` background processes (no tmux dependency).
# Each issue gets its own background process running /dev-pipeline.
#
# Key design decisions:
#   - attemptId: unique per dispatch attempt, prevents stale file collision
#   - setsid + PGID: process group based lifecycle management
#   - flock: state file locking for correctness
#   - provider health: circuit breaker for GitHub API failures
#   - exit file JSON: explicit completion signal with attemptId matching
#   - heartbeat: explicit activity signal from dispatch wrapper
#   - skipped_dep_failed: failed dependency propagation without dispatching

# Source shared monorepo helpers for MONOREPO_ROOT and area resolution.
_ORCH_HELPERS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$_ORCH_HELPERS_DIR/../../../../.agents/scripts/monorepo-helpers.sh"
ORCH_BASE="$MONOREPO_ROOT/.workspace/orchestrate"
PIPELINE_DIR="$MONOREPO_ROOT/.workspace/pipeline"

# ──────────────────────────────────────────────
# State management
# ──────────────────────────────────────────────

orch_state_path() {
  local area=$1
  echo "$ORCH_BASE/${area}/batch.state.json"
}

orch_terminal_path() {
  # Returns the terminal.json path for a dispatched issue.
  # The terminal file is the sole completion contract between the pipeline and orchestrator.
  local area=$1
  local issue=$2
  echo "$ORCH_BASE/${area}/issue-${issue}.terminal.json"
}

# Alias kept for call sites that used the old name; prefer orch_terminal_path.
orch_signal_path() {
  orch_terminal_path "$@"
}

orch_attempt_id() {
  # Generate a unique attempt identifier.
  # Format: {batchId}-issue{N}-attempt{M}
  local batch_id=$1
  local issue=$2
  local retry_count=$3
  echo "${batch_id}-issue${issue}-attempt${retry_count}"
}

orch_init() {
  # Usage: orch_init <area> <agent> <issues_json> <dag_json> [max_concurrent]
  # Creates initial batch state file.
  local area=$1
  local agent=$2
  local issues_json=$3  # JSON array e.g. '[1,2,3]'
  local dag_json=$4     # JSON object e.g. '{"3":[1,2]}'
  local max_concurrent=${5:-4}

  mkdir -p "$ORCH_BASE/$area"

  local batch_id
  batch_id="batch-$(date +%Y%m%d-%H%M%S)"

  # Filter DAG: remove deps not in the batch to prevent permanent blocks.
  # External deps (closed issues, out-of-batch) are treated as already satisfied.
  local filtered_dag
  filtered_dag=$(jq -n \
    --argjson issues "$issues_json" \
    --argjson dag "$dag_json" \
    '$dag | to_entries
     | map(.value |= map(select(. as $d | $issues | any(. == $d))))
     | from_entries')

  # Build initial status: pending for issues with no deps, blocked otherwise
  local status_json
  status_json=$(jq -n \
    --argjson issues "$issues_json" \
    --argjson dag "$filtered_dag" \
    'reduce $issues[] as $n ({};
       . + {($n|tostring):
         (if ($dag[($n|tostring)] // []) | length > 0
          then "blocked" else "pending" end)})')

  jq -n \
    --arg area "$area" \
    --arg batchId "$batch_id" \
    --argjson issues "$issues_json" \
    --argjson dag "$filtered_dag" \
    --argjson status "$status_json" \
    --arg agent "$agent" \
    --argjson maxConcurrent "$max_concurrent" \
    --arg now "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    '{area: $area, batchId: $batchId, issues: $issues, dag: $dag,
      status: $status, dispatched: {}, agent: $agent,
      maxConcurrent: $maxConcurrent,
      providers: {github: {status: "healthy", consecutiveFailures: 0,
                           lastError: null, lastCheckedAt: null}},
      orchestratorPid: 0, orchestratorPane: "", orchestratorStartedAt: "",
      createdAt: $now, updatedAt: $now}' \
    > "$(orch_state_path "$area")"

  orch_register_self "$area"
}

orch_register_self() {
  # Usage: orch_register_self <area>
  # Records current orchestrator identity in batch state.
  # Call at orch_init AND on every resume/recovery to keep liveness info fresh.
  local area=$1
  local orch_pane="${TMUX_PANE:-}"
  local orch_pid=${BASHPID:-$$}
  local orch_started_at=""
  if [ -f "/proc/$orch_pid/stat" ]; then
    orch_started_at=$(awk '{print $22}' "/proc/$orch_pid/stat") || true
  fi
  if [ -z "$orch_started_at" ]; then
    >&2 echo "[orchestrator] WARNING: could not read start time from /proc/$orch_pid/stat"
  fi
  orch_state_update "$area" \
    ".orchestratorPid = $orch_pid | .orchestratorPane = \"$orch_pane\" | .orchestratorStartedAt = \"${orch_started_at:-}\""
}

orch_state_read() {
  local area=$1
  cat "$(orch_state_path "$area")"
}

orch_state_update() {
  # Usage: orch_state_update <area> <jq_filter>
  # Applies a jq filter to update the state file in place.
  # Uses flock for mutual exclusion + temp file + mv for atomicity.
  local area=$1
  local filter=$2
  local path
  path=$(orch_state_path "$area")
  (
    flock -n 9 || { >&2 echo "[orchestrator] state lock held by another process"; exit 1; }
    local tmp_file
    tmp_file=$(mktemp "$(dirname "$path")/.tmp.state.XXXXXX")
    if jq "($filter) | .updatedAt = \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"" "$path" > "$tmp_file"; then
      mv "$tmp_file" "$path"
    else
      rm -f "$tmp_file"
      >&2 echo "[orchestrator] orch_state_update: jq failed for area=$area, filter=$filter"
      exit 1
    fi
  ) 9>"${path}.lock"
}

orch_status_set() {
  # Usage: orch_status_set <area> <issue> <status>
  # Valid statuses: pending | blocked | dispatched | completed | failed | skipped_dep_failed
  local area=$1
  local issue=$2
  local status=$3
  orch_state_update "$area" ".status[\"$issue\"] = \"$status\""
}

# ──────────────────────────────────────────────
# Provider health (GitHub circuit breaker)
# ──────────────────────────────────────────────

orch_provider_health_get() {
  # Returns: "healthy" | "degraded" | "hard_fault"
  local area=$1
  orch_state_read "$area" | jq -r '.providers.github.status // "healthy"'
}

_orch_provider_health_record() {
  # Internal: update provider health in state.
  # result: "healthy" | "hard_fault" | "failure"
  local area=$1 result=$2 error=${3:-}
  local now
  now=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  # Safely encode error string for JSON embedding (handles quotes, newlines, etc.)
  local safe_error
  safe_error=$(printf '%s' "$error" | jq -Rs '.'  | sed 's/^"//;s/"$//')

  case "$result" in
    healthy)
      orch_state_update "$area" \
        ".providers.github.status = \"healthy\"
         | .providers.github.consecutiveFailures = 0
         | .providers.github.lastCheckedAt = \"$now\""
      ;;
    hard_fault)
      orch_state_update "$area" \
        ".providers.github.status = \"hard_fault\"
         | .providers.github.lastError = \"$safe_error\"
         | .providers.github.lastCheckedAt = \"$now\""
      ;;
    failure)
      orch_state_update "$area" \
        ".providers.github.consecutiveFailures = ((.providers.github.consecutiveFailures // 0) + 1)
         | .providers.github.status = (if .providers.github.consecutiveFailures >= 3 then \"degraded\" else .providers.github.status end)
         | .providers.github.lastError = \"$safe_error\"
         | .providers.github.lastCheckedAt = \"$now\""
      ;;
  esac
}

orch_gh() {
  # Wrapper for gh commands with provider health tracking.
  # Usage: orch_gh <area> <gh_subcommand> [args...]
  # Returns: gh exit code. stdout: gh output on success.
  # On auth failure (rc=4): sets hard_fault, blocks further calls.
  # On other failure: increments consecutiveFailures, logs to gh-errors.log.
  local area="$1"; shift

  local health
  health=$(orch_provider_health_get "$area")
  if [ "$health" = "hard_fault" ]; then
    >&2 echo "[orchestrator] GitHub provider hard fault - gh call blocked"
    return 5
  fi

  local err_file out rc
  err_file=$(mktemp)
  out=$(gh "$@" 2>"$err_file") && rc=0 || rc=$?
  local err_content
  err_content=$(cat "$err_file")
  rm -f "$err_file"

  if [ $rc -eq 0 ]; then
    # Only update state if transitioning from non-healthy
    if [ "$health" != "healthy" ]; then
      _orch_provider_health_record "$area" "healthy"
    fi
    echo "$out"
    return 0
  elif [ $rc -eq 4 ]; then
    _orch_provider_health_record "$area" "hard_fault" "$err_content"
    >&2 echo "[orchestrator] GitHub auth failure: $err_content"
    return 4
  else
    _orch_provider_health_record "$area" "failure" "$err_content"
    if [ -n "$err_content" ]; then
      local err_log="$ORCH_BASE/${area}/gh-errors.log"
      # Truncate if over 1MB to prevent unbounded growth
      if [ -f "$err_log" ] && [ "$(stat -c %s "$err_log")" -gt 1048576 ]; then
        tail -100 "$err_log" > "${err_log}.tmp" && mv "${err_log}.tmp" "$err_log"
      fi
      echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] gh rc=$rc: $err_content" >> "$err_log"
    fi
    return "$rc"
  fi
}

# ──────────────────────────────────────────────
# Process management (headless dispatch via setsid + PGID)
# ──────────────────────────────────────────────

_orch_parse_agent() {
  # Usage: read -r tool model <<< "$(_orch_parse_agent "$agent")"
  # Parses agent string: "claude" | "claude:sonnet" | "claude:opus"
  local agent=$1
  local tool="${agent%%:*}"
  local model="${agent#*:}"
  [ "$model" = "$agent" ] && model=""
  echo "$tool" "$model"
}

orch_process_alive() {
  # Usage: orch_process_alive <pid>
  # Returns: 0 = alive, 1 = dead
  local pid=$1
  [ -n "$pid" ] && [ "$pid" != "null" ] && kill -0 "$pid" 2>/dev/null
}

orch_pgid_alive() {
  # Usage: orch_pgid_alive <pgid>
  # Returns: 0 = at least one process in group alive, 1 = all dead
  local pgid=$1
  [ -n "$pgid" ] && [ "$pgid" != "null" ] && kill -0 -"$pgid" 2>/dev/null
}

orch_dispatch() {
  # Usage: orch_dispatch <issue> <area_dir> <agent> [retryCount]
  # Atomic: launches background process AND records in state.
  # If state recording fails, kills the orphan process group.
  # stdout: wrapper PID (= PGID) of the background process
  # Returns: 0 = launched + recorded, 1 = failed
  local issue=$1
  local area_dir=$2
  local agent=$3
  local retry_count=${4:-0}

  local area
  area=$(monorepo_area_from_dir "$area_dir")
  local repo
  repo=$(monorepo_area_repo "$area")
  local batch_id
  batch_id=$(orch_state_read "$area" | jq -r '.batchId')

  local tool model
  read -r tool model <<< "$(_orch_parse_agent "$agent")"

  local log="$ORCH_BASE/${area}/issue-${issue}.log"
  local err_log="$ORCH_BASE/${area}/issue-${issue}.err"
  local terminal_file
  terminal_file=$(orch_terminal_path "$area" "$issue")
  local heartbeat_file="$ORCH_BASE/${area}/issue-${issue}.heartbeat"
  local pid_file="$ORCH_BASE/${area}/issue-${issue}.pid"
  local pipeline_state_file="$PIPELINE_DIR/${area}/issue-${issue}.state.json"
  local attempt_id
  attempt_id=$(orch_attempt_id "$batch_id" "$issue" "$retry_count")

  # Pre-dispatch cleanup: remove stale files from previous attempts.
  # attemptId matching provides safety, but cleanup prevents confusion.
  rm -f "$terminal_file" "$heartbeat_file" "$pid_file" "$log" "$err_log"

  local prompt="/dev-pipeline ${area} #${issue}. Repo: ${repo}.${model:+ Use model \"${model}\" for the review subprocess (pass to pipeline_run_review).} Running headlessly - auto-approve merge when review passes (no critical issues). Auto-re-review after resolve. After completing all steps, exit."

  local wrapper_script="$_ORCH_HELPERS_DIR/orch-dispatch-wrapper.sh"

  # Launch in a new session (setsid) for process group isolation.
  # The wrapper writes its PID (= PGID) to pid_file.
  # timeout -k sends SIGKILL 30s after initial signal as runtime upper bound.
  cd "$MONOREPO_ROOT" || return 1
  setsid bash "$wrapper_script" \
    "$attempt_id" "$terminal_file" "$heartbeat_file" "$pid_file" \
    "$issue" "$pipeline_state_file" -- \
    timeout -k 30 3600 claude -p \
    ${model:+--model "$model"} --dangerously-skip-permissions \
    --no-session-persistence \
    --allowedTools "Bash,Read,Edit,Write,Grep,Glob,Skill,Agent" \
    --max-turns 80 \
    "$prompt" > "$log" 2>"$err_log" &

  # Wait for wrapper to write its PID
  local wait_count=0
  while [ ! -f "$pid_file" ] && [ "$wait_count" -lt 5 ]; do
    sleep 1
    wait_count=$((wait_count + 1))
  done

  if [ ! -f "$pid_file" ]; then
    >&2 echo "[orchestrator] Process failed to start for issue #${issue} (no pid file after 5s)"
    return 1
  fi

  local pid
  pid=$(cat "$pid_file")
  local pgid=$pid  # setsid session leader: PGID = PID

  if ! orch_process_alive "$pid"; then
    >&2 echo "[orchestrator] Process died immediately for issue #${issue}"
    return 1
  fi

  # Atomic: record dispatch in state. Kill orphan if recording fails.
  local now
  now=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  if ! orch_state_update "$area" \
    ".dispatched[\"$issue\"] = {
       pid: $pid, pgid: $pgid, attemptId: \"$attempt_id\",
       log: \"$log\", dispatchedAt: \"$now\", lastActivity: \"$now\",
       lastCommitSha: null, lastCpuJiffies: \"0\",
       pipelineStarted: false, retryCount: $retry_count
     }
     | .status[\"$issue\"] = \"dispatched\""; then
    >&2 echo "[orchestrator] State recording failed for #${issue} - killing orphan PGID $pgid"
    orch_stop_process "$area" "$issue"
    return 1
  fi

  echo "$pid"
  return 0
}

orch_stop_process() {
  # Usage: orch_stop_process <area> <issue>
  # Stops the entire process group for a dispatched issue.
  # Sends SIGTERM to group, waits, then SIGKILL if needed.
  local area=$1
  local issue=$2
  local state
  state=$(orch_state_read "$area")
  local pgid
  pgid=$(echo "$state" | jq -r ".dispatched[\"$issue\"].pgid // empty")

  if [ -z "$pgid" ] || [ "$pgid" = "null" ]; then
    # Fallback: try PID-based kill (legacy state without pgid)
    local pid
    pid=$(echo "$state" | jq -r ".dispatched[\"$issue\"].pid // empty")
    if [ -n "$pid" ] && [ "$pid" != "null" ] && orch_process_alive "$pid"; then
      kill "$pid" 2>/dev/null
      sleep 3
      orch_process_alive "$pid" && kill -9 "$pid" 2>/dev/null
    fi
    return 0
  fi

  if ! orch_pgid_alive "$pgid"; then return 0; fi

  kill -- -"$pgid" 2>/dev/null
  sleep 3
  if orch_pgid_alive "$pgid"; then
    kill -9 -- -"$pgid" 2>/dev/null
  fi
}

# ──────────────────────────────────────────────
# PR lookup helper
# ──────────────────────────────────────────────

_orch_pr_list() {
  # Usage: _orch_pr_list <area> <issue> <state> <json_fields> <jq_filter>
  # Finds PRs that close the given issue via orch_gh (provider health aware).
  local area=$1 issue=$2 state=$3 json_fields=$4 jq_filter=$5
  local repo
  repo=$(monorepo_area_repo "$area")

  orch_gh "$area" pr list \
    -R "$repo" \
    --search "\"Closes #${issue}\" OR \"Fixes #${issue}\" OR \"Resolves #${issue}\"" \
    --state "$state" --json "$json_fields" --jq "$jq_filter"
}

# ──────────────────────────────────────────────
# Completion detection
# ──────────────────────────────────────────────

orch_check_completion() {
  # Usage: orch_check_completion <issue> <area_dir>
  # Checks if a dispatched issue's pipeline has finished.
  # stdout: "completed", "failed", "abnormal_exit", or "running"
  # Always returns 0 (safe for set -e callers).
  #
  # Contract: terminal.json is the sole basis for a "completed" or "failed" result.
  # PR status is supplementary - used only to distinguish "abnormal_exit" from
  # "failed" when the process dies without writing terminal.json.
  #
  # Detection priority:
  #   1. terminal.json (explicit, with attemptId match) - only source of "completed"
  #   2. Process group alive (PGID check) -> "running"
  #   3. Grace period (60s) after process death -> "running"
  #   4. PR status (supplementary only, provider health aware)
  #      - merged or open PR -> "abnormal_exit" (process died without terminal.json)
  #      - no PR or gh failed -> "failed"
  local issue=$1
  local area_dir=$2
  local area
  area=$(monorepo_area_from_dir "$area_dir")

  local state
  state=$(orch_state_read "$area")
  local current_attempt
  current_attempt=$(echo "$state" | jq -r ".dispatched[\"$issue\"].attemptId // empty")
  local pgid
  pgid=$(echo "$state" | jq -r ".dispatched[\"$issue\"].pgid // empty")
  local pid
  pid=$(echo "$state" | jq -r ".dispatched[\"$issue\"].pid // empty")

  # 1. terminal.json (sole source of "completed" / "failed" results)
  local terminal_file
  terminal_file=$(orch_terminal_path "$area" "$issue")
  if [ -f "$terminal_file" ]; then
    local terminal_json
    terminal_json=$(cat "$terminal_file")
    local file_attempt
    file_attempt=$(echo "$terminal_json" | jq -r '.attemptId // empty')

    if [ -n "$current_attempt" ] && [ "$file_attempt" != "$current_attempt" ]; then
      # Stale terminal file from a different attempt - ignore
      >&2 echo "[orchestrator] Ignoring stale terminal file for #${issue} (attempt mismatch: file=$file_attempt, current=$current_attempt)"
    else
      local terminal_status
      terminal_status=$(echo "$terminal_json" | jq -r '.status // "failed"')
      if [ "$terminal_status" = "completed" ]; then
        echo "completed"; return 0
      else
        echo "failed"; return 0
      fi
    fi
  fi

  # 2. Process group alive check
  local group_alive=false
  if [ -n "$pgid" ] && orch_pgid_alive "$pgid"; then
    group_alive=true
  elif [ -n "$pid" ] && orch_process_alive "$pid"; then
    # Fallback for legacy state without pgid
    group_alive=true
  fi

  if [ "$group_alive" = "true" ]; then
    # Track pipelineStarted for observability
    local pipeline_state="$PIPELINE_DIR/${area}/issue-${issue}.state.json"
    local seen
    seen=$(echo "$state" | jq -r ".dispatched[\"$issue\"].pipelineStarted // false")
    if [ -f "$pipeline_state" ] && [ "$seen" != "true" ]; then
      orch_state_update "$area" ".dispatched[\"$issue\"].pipelineStarted = true" || true
    fi
    echo "running"; return 0
  fi

  # 3. Process dead, no terminal file.
  # Allow 60s grace period for the exit trap to finish writing terminal.json
  # (race between process exit and trap handler / filesystem flush).
  local dispatched_at
  dispatched_at=$(echo "$state" | jq -r ".dispatched[\"$issue\"].dispatchedAt // empty")
  if [ -n "$dispatched_at" ]; then
    local dispatch_ts now_ts
    dispatch_ts=$(date -d "$dispatched_at" +%s) || dispatch_ts=0
    now_ts=$(date +%s)
    local alive_duration=$((now_ts - dispatch_ts))
    # If process just died (< 60s since dispatch), wait for exit file
    if [ "$alive_duration" -lt 60 ]; then
      echo "running"; return 0
    fi
  fi

  # 4. PR status (supplementary only - never produces "completed").
  # Process is dead and terminal.json was not written (SIGKILL or trap failure).
  # PR evidence helps distinguish "abnormal_exit" (work may be done) from "failed"
  # (no sign of progress), but cannot confirm completion without terminal.json.
  local gh_health
  gh_health=$(orch_provider_health_get "$area")
  if [ "$gh_health" = "degraded" ]; then
    # Don't make PR-based judgments during degraded state
    echo "running"; return 0
  fi

  local pr_states
  if ! pr_states=$(_orch_pr_list "$area" "$issue" all "number,state" '[.[].state]'); then
    # gh command failed - don't judge on API error
    echo "running"; return 0
  fi

  if echo "$pr_states" | grep -q '"MERGED"'; then
    echo "completed"; return 0
  fi
  if echo "$pr_states" | grep -q '"OPEN"'; then
    # PR exists but process dead and no exit file - abnormal exit
    echo "abnormal_exit"; return 0
  fi

  # No terminal file, no process, no PR found
  echo "failed"; return 0
}

orch_update_last_activity() {
  # Usage: orch_update_last_activity <area> <issue> [commit_sha]
  local area=$1
  local issue=$2
  local sha=${3:-}
  local now
  now=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  local filter=".dispatched[\"$issue\"].lastActivity = \"$now\""
  if [ -n "$sha" ]; then
    filter="$filter | .dispatched[\"$issue\"].lastCommitSha = \"$sha\""
  fi
  orch_state_update "$area" "$filter"
}

# ──────────────────────────────────────────────
# Stall detection (heartbeat + composite signals)
# ──────────────────────────────────────────────

orch_detect_stall() {
  # Usage: orch_detect_stall <area> <issue>
  # stdout: "stalled" or "active"
  # Always returns 0 (safe for set -e callers).
  #
  # Detection priority:
  #   1. Heartbeat file (strongest - explicit signal from dispatch wrapper)
  #   2. Elapsed time check against threshold
  #   3. Composite signals: log mtime | CPU jiffies | commit SHA change
  #   4. Threshold exceeded with no positive signals = stalled
  local area=$1
  local issue=$2
  local stall_seconds=600       # 10 minutes (post-PR)
  local pre_pr_stall=1200       # 20 minutes (pre-PR)

  local state
  state=$(orch_state_read "$area")

  # Batch-extract all needed fields from state in one jq call
  local fields
  fields=$(echo "$state" | jq -r --arg i "$issue" '
    .dispatched[$i] // {} |
    [.pgid // "", .pid // "", .lastActivity // "",
     .lastCpuJiffies // "0", .lastCommitSha // ""] | @tsv')
  local pgid wrapper_pid last_activity last_cpu last_sha
  IFS=$'\t' read -r pgid wrapper_pid last_activity last_cpu last_sha <<< "$fields"

  # 1. Heartbeat check (strongest signal)
  local hb_file="$ORCH_BASE/${area}/issue-${issue}.heartbeat"
  if [ -f "$hb_file" ]; then
    local hb_ts now_ts
    hb_ts=$(cat "$hb_file")
    now_ts=$(date +%s)
    # 2 min tolerance (heartbeat fires every 60s)
    if [ $((now_ts - hb_ts)) -lt 120 ]; then
      echo "active"; return 0
    fi
  fi

  # 2. Check elapsed time since lastActivity
  if [ -z "$last_activity" ]; then
    echo "active"; return 0
  fi

  local last_ts now_ts elapsed
  last_ts=$(date -d "$last_activity" +%s) || { echo "active"; return 0; }
  now_ts=$(date +%s)
  elapsed=$((now_ts - last_ts))

  # Determine threshold: pre-PR vs post-PR (single PR lookup, reused for commit check)
  local threshold=$stall_seconds
  local pr_number=""
  pr_number=$(_orch_pr_list "$area" "$issue" open number '.[0].number') || true
  if [ -z "$pr_number" ] || [ "$pr_number" = "null" ]; then
    threshold=$pre_pr_stall
  fi

  if [ "$elapsed" -lt "$threshold" ]; then
    echo "active"; return 0
  fi

  # 3. Composite check: any positive signal = active
  local stall_reason="no heartbeat"

  # 3a. Log file mtime
  local log_file="$ORCH_BASE/${area}/issue-${issue}.log"
  if [ -f "$log_file" ]; then
    local log_mtime
    log_mtime=$(stat -c %Y "$log_file")
    if [ $((now_ts - log_mtime)) -lt "$threshold" ]; then
      orch_update_last_activity "$area" "$issue"
      echo "active"; return 0
    fi
  fi

  # 3b. CPU jiffies change
  if [ -n "$wrapper_pid" ] && [ -f "/proc/$wrapper_pid/stat" ]; then
    local cpu_now
    cpu_now=$(awk '{print $14+$15}' "/proc/$wrapper_pid/stat") || cpu_now="0"
    if [ "$cpu_now" != "$last_cpu" ] && [ "$cpu_now" != "0" ]; then
      orch_state_update "$area" ".dispatched[\"$issue\"].lastCpuJiffies = \"$cpu_now\""
      orch_update_last_activity "$area" "$issue"
      echo "active"; return 0
    fi
  fi

  # 3c. Commit SHA change (reuses pr_number from threshold check above)
  if [ -n "$pr_number" ] && [ "$pr_number" != "null" ]; then
    local repo
    repo=$(monorepo_area_repo "$area")
    local latest_sha
    latest_sha=$(orch_gh "$area" api "repos/${repo}/pulls/${pr_number}/commits" \
      --jq '.[-1].sha') || true
    if [ -n "$latest_sha" ] && [ "$latest_sha" != "$last_sha" ]; then
      orch_update_last_activity "$area" "$issue" "$latest_sha"
      echo "active"; return 0
    fi
  fi

  # 4. No positive signals - stalled
  if [ -n "$pgid" ] && orch_pgid_alive "$pgid"; then
    stall_reason="$stall_reason, process group alive but no log/cpu/commit activity for ${elapsed}s"
  else
    stall_reason="$stall_reason, process group dead"
  fi
  orch_state_update "$area" \
    ".dispatched[\"$issue\"].stallReason = \"$stall_reason\"" || true

  echo "stalled"; return 0
}

# ──────────────────────────────────────────────
# Unblocking (with skipped_dep_failed propagation)
# ──────────────────────────────────────────────

orch_unblock() {
  # Usage: orch_unblock <area> <completed_issue>
  # Finds issues that were blocked only by completed_issue and updates status:
  #   - All deps completed -> pending (ready to dispatch)
  #   - All deps resolved but >= 1 failed -> skipped_dep_failed (not dispatched)
  # stdout: space-separated list of newly-unblocked issue numbers
  local area=$1
  local done_issue=$2

  local state
  state=$(orch_state_read "$area")

  local dag
  dag=$(echo "$state" | jq -r '.dag')
  local all_issues
  all_issues=$(echo "$state" | jq -r '.issues[]')

  local unblocked=""
  for n in $all_issues; do
    local status
    status=$(echo "$state" | jq -r ".status[\"$n\"]")
    [ "$status" != "blocked" ] && continue

    local deps
    deps=$(echo "$dag" | jq -r ".[\"$n\"] // [] | .[]")

    local still_blocked=0
    local has_failed_dep=0
    for dep in $deps; do
      local dep_status
      dep_status=$(echo "$state" | jq -r ".status[\"$dep\"]")
      if [ "$dep_status" = "failed" ] || [ "$dep_status" = "skipped_dep_failed" ]; then
        has_failed_dep=1
      elif [ "$dep_status" != "completed" ]; then
        still_blocked=1
        break
      fi
    done

    if [ "$still_blocked" -eq 0 ]; then
      if [ "$has_failed_dep" -eq 1 ]; then
        orch_status_set "$area" "$n" "skipped_dep_failed"
      else
        orch_status_set "$area" "$n" "pending"
      fi
      unblocked="$unblocked $n"
    fi
  done

  echo "$unblocked"
}

_orch_mark_failed_and_unblock() {
  # Internal helper: mark issue failed, remove from dispatched, unblock dependents.
  local area=$1 issue=$2
  orch_status_set "$area" "$issue" "failed"
  orch_state_update "$area" "del(.dispatched[\"$issue\"])"
  local newly_unblocked
  newly_unblocked=$(orch_unblock "$area" "$issue")
  [ -n "$newly_unblocked" ] && >&2 echo "[orchestrator] Unblocked: $newly_unblocked"
}

# ──────────────────────────────────────────────
# Poll cycle
# ──────────────────────────────────────────────

orch_poll_cycle() {
  # Usage: orch_poll_cycle <area> <area_dir> <agent>
  # One polling iteration: check completion, detect stalls, unblock, dispatch.
  local area=$1
  local area_dir=$2
  local agent=$3

  # Check provider health - halt cycle on hard fault
  local gh_health
  gh_health=$(orch_provider_health_get "$area")
  if [ "$gh_health" = "hard_fault" ]; then
    >&2 echo "[orchestrator] HARD FAULT: GitHub auth failure - poll cycle halted"
    >&2 echo "[orchestrator] Fix auth and restart orchestrator"
    return 1
  fi

  local state
  state=$(orch_state_read "$area")
  local dispatched_issues
  dispatched_issues=$(echo "$state" | jq -r '.dispatched | keys[]')

  # 1. Check completion for dispatched (non-terminal) issues
  for issue in $dispatched_issues; do
    local cur_status
    cur_status=$(echo "$state" | jq -r ".status[\"$issue\"]")
    [ "$cur_status" = "completed" ] || [ "$cur_status" = "failed" ] && continue

    local result
    result=$(orch_check_completion "$issue" "$area_dir")

    case "$result" in
      completed|failed)
        orch_status_set "$area" "$issue" "$result"
        orch_state_update "$area" "del(.dispatched[\"$issue\"])"
        >&2 echo "[orchestrator] Issue #${issue}: ${result}"
        local newly_unblocked
        newly_unblocked=$(orch_unblock "$area" "$issue")
        [ -n "$newly_unblocked" ] && >&2 echo "[orchestrator] Unblocked: $newly_unblocked"
        ;;
      abnormal_exit)
        local retry_count
        retry_count=$(echo "$state" | jq -r ".dispatched[\"$issue\"].retryCount // 0")
        if [ "$retry_count" -lt 1 ]; then
          # Before re-dispatching, check if the PR is already merged.
          # A merged PR with no terminal.json means the process was SIGKILL-ed after
          # merge but before the exit trap could write the file. Re-dispatching would
          # create a duplicate pipeline run against a branch that no longer exists.
          local merged_pr
          merged_pr=$(_orch_pr_list "$area" "$issue" merged "number" '.[0].number') || true
          if [ -n "$merged_pr" ] && [ "$merged_pr" != "null" ]; then
            >&2 echo "[orchestrator] Abnormal exit for #${issue}: PR #${merged_pr} already merged but no terminal.json (process killed before exit trap). Marking failed - manual review recommended."
            # Record a durable signal in batch state so operators can detect this edge case
            # without digging through logs. Visible in orch_print_summary output.
            local _now
            _now=$(date -u +%Y-%m-%dT%H:%M:%SZ)
            orch_state_update "$area" \
              ".mergedWithoutTerminal = ((.mergedWithoutTerminal // []) + [{issue: ($issue | tonumber), pr: ($merged_pr | tonumber), detectedAt: \"$_now\"}])" || true
            _orch_mark_failed_and_unblock "$area" "$issue"
          else
            >&2 echo "[orchestrator] Abnormal exit for #${issue} - retrying"
            orch_state_update "$area" "del(.dispatched[\"$issue\"])"
            local new_pid
            new_pid=$(orch_dispatch "$issue" "$area_dir" "$agent" "$((retry_count + 1))")
            if [ -n "$new_pid" ]; then
              >&2 echo "[orchestrator] Re-dispatched #${issue} - PID $new_pid"
            else
              >&2 echo "[orchestrator] Re-dispatch failed for #${issue} - marking failed"
              _orch_mark_failed_and_unblock "$area" "$issue"
            fi
          fi
        else
          >&2 echo "[orchestrator] Issue #${issue}: abnormal_exit (retry exhausted)"
          _orch_mark_failed_and_unblock "$area" "$issue"
        fi
        ;;
      # "running" - no action
    esac
  done

  # 2. Stall detection + bounded auto-retry for still-dispatched issues
  state=$(orch_state_read "$area")
  dispatched_issues=$(echo "$state" | jq -r '.dispatched | keys[]')
  for issue in $dispatched_issues; do
    local cur_status
    cur_status=$(echo "$state" | jq -r ".status[\"$issue\"]")
    [ "$cur_status" != "dispatched" ] && continue

    if [ "$(orch_detect_stall "$area" "$issue")" = "stalled" ]; then
      local pgid
      pgid=$(echo "$state" | jq -r ".dispatched[\"$issue\"].pgid // empty")
      local retry_count
      retry_count=$(echo "$state" | jq -r ".dispatched[\"$issue\"].retryCount // 0")
      local group_alive=false
      [ -n "$pgid" ] && orch_pgid_alive "$pgid" && group_alive=true

      if [ "$group_alive" = "false" ] && [ "$retry_count" -lt 1 ]; then
        >&2 echo "[orchestrator] STALL: Issue #${issue} process dead - retrying (attempt $((retry_count + 1)))"
        orch_state_update "$area" "del(.dispatched[\"$issue\"])"
        local new_pid
        new_pid=$(orch_dispatch "$issue" "$area_dir" "$agent" "$((retry_count + 1))")
        if [ -n "$new_pid" ]; then
          >&2 echo "[orchestrator] Re-dispatched #${issue} - PID $new_pid"
        else
          >&2 echo "[orchestrator] Re-dispatch failed for #${issue}"
        fi
      elif [ "$retry_count" -ge 1 ]; then
        >&2 echo "[orchestrator] STALL: Issue #${issue} - retry exhausted, marking failed"
        orch_stop_process "$area" "$issue"
        _orch_mark_failed_and_unblock "$area" "$issue"
      else
        >&2 echo "[orchestrator] STALL detected: Issue #${issue} - no activity for threshold period"
        >&2 echo "[orchestrator] Process group alive. Consider: stop, retry, or skip"
      fi
    fi
  done

  # 3. Dispatch pending issues (respecting maxConcurrent)
  state=$(orch_state_read "$area")
  local max_concurrent
  max_concurrent=$(echo "$state" | jq -r '.maxConcurrent // 4')
  local active_count
  active_count=$(echo "$state" | jq '[.status | to_entries[] | select(.value == "dispatched")] | length')

  local pending_issues
  pending_issues=$(echo "$state" | jq -r '.status | to_entries[] | select(.value == "pending") | .key')

  if [ -n "$pending_issues" ] && [ "$active_count" -lt "$max_concurrent" ]; then
    local slots_available=$(( max_concurrent - active_count ))
    local dispatched_count=0

    for issue in $pending_issues; do
      [ "$dispatched_count" -ge "$slots_available" ] && break

      local pid
      pid=$(orch_dispatch "$issue" "$area_dir" "$agent")
      if [ -n "$pid" ]; then
        >&2 echo "[orchestrator] Dispatched #${issue} - PID $pid"
        dispatched_count=$((dispatched_count + 1))
      else
        >&2 echo "[orchestrator] Failed to dispatch #${issue}"
      fi
    done
  fi
}

# ──────────────────────────────────────────────
# Summary
# ──────────────────────────────────────────────

orch_print_summary() {
  # Usage: orch_print_summary <area>
  local area=$1

  local state
  state=$(orch_state_read "$area")

  echo ""
  echo "=== Orchestrator Batch Summary ==="
  printf "%-8s %-20s %s\n" "Issue" "Status" "PR"
  echo "--------------------------------------------"

  local issues
  issues=$(echo "$state" | jq -r '.issues[]')
  for issue in $issues; do
    local status
    status=$(echo "$state" | jq -r ".status[\"$issue\"]")
    local pr_url=""
    if [ "$status" = "completed" ]; then
      pr_url=$(_orch_pr_list "$area" "$issue" merged url '.[0].url') || true
    fi
    printf "%-8s %-20s %s\n" "#${issue}" "$status" "$pr_url"
  done
  echo "============================================"

  # Warn about merged-without-terminal cases (SIGKILL edge case, manual review needed)
  local mwt_count
  mwt_count=$(echo "$state" | jq '(.mergedWithoutTerminal // []) | length')
  if [ "$mwt_count" -gt 0 ]; then
    echo ""
    echo "WARNING: ${mwt_count} issue(s) had PR merged but no terminal.json written (SIGKILL edge case)."
    echo "These are marked 'failed' but the PR was actually merged. Manual review recommended:"
    echo "$state" | jq -r '(.mergedWithoutTerminal // [])[] | "  Issue #\(.issue) - PR #\(.pr) - detected \(.detectedAt)"'
  fi
}
