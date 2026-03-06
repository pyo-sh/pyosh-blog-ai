#!/bin/bash
# orchestrate-helpers.sh — Shell helpers for dev-orchestrator skill
# Source this file at orchestrator start.
#
# Dispatch model: headless `claude -p` background processes (no tmux dependency).
# Each issue gets its own background process running /dev-pipeline.

# Source shared monorepo helpers for MONOREPO_ROOT and area resolution.
# → .agents/references/monorepo-layout.md
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

orch_signal_path() {
  local area=$1
  local issue=$2
  echo "$ORCH_BASE/${area}/issue-${issue}.exit"
}

orch_init() {
  # Usage: orch_init <area> <agent> <issues_json> <dag_json> [max_concurrent]
  # Creates initial batch state file.
  local area=$1
  local agent=$2
  local issues_json=$3  # JSON array e.g. '[1,2,3]'
  local dag_json=$4     # JSON object e.g. '{"3":[1,2]}'
  local max_concurrent=${5:-4}  # default: 4 concurrent processes

  mkdir -p "$ORCH_BASE/$area"

  local batch_id
  batch_id="batch-$(date +%Y%m%d-%H%M%S)"

  # Filter DAG: remove deps not in the batch to prevent permanent blocks.
  # External deps (closed issues, out-of-batch) are treated as already satisfied.
  local filtered_dag
  filtered_dag=$(jq -n \
    --argjson issues "$issues_json" \
    --argjson dag "$dag_json" \
    '$dag | to_entries | map(.value |= map(select(. as $d | $issues | any(. == $d)))) | from_entries')

  # Build initial status: pending for issues with no deps, blocked otherwise
  local status_json
  status_json=$(jq -n \
    --argjson issues "$issues_json" \
    --argjson dag "$filtered_dag" \
    'reduce $issues[] as $n ({}; . + {($n|tostring): (if ($dag[($n|tostring)] // []) | length > 0 then "blocked" else "pending" end)})')

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
      createdAt: $now, updatedAt: $now}' \
    > "$(orch_state_path "$area")"
}

orch_state_read() {
  local area=$1
  cat "$(orch_state_path "$area")"
}

orch_state_update() {
  # Usage: orch_state_update <area> <jq_filter>
  # Applies a jq filter to update the state file in place.
  # Writes atomically via temp file + mv to prevent state corruption on jq failure.
  local area=$1
  local filter=$2
  local path
  path=$(orch_state_path "$area")
  local tmp_file
  tmp_file=$(mktemp "$(dirname "$path")/.tmp.state.XXXXXX")
  if jq "($filter) | .updatedAt = \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"" "$path" > "$tmp_file"; then
    mv "$tmp_file" "$path"
  else
    rm -f "$tmp_file"
    >&2 echo "[orchestrator] orch_state_update: jq failed for area=$area, filter=$filter"
    return 1
  fi
}

orch_status_set() {
  # Usage: orch_status_set <area> <issue> <status>
  # status: pending | blocked | dispatched | completed | failed
  local area=$1
  local issue=$2
  local status=$3
  orch_state_update "$area" ".status[\"$issue\"] = \"$status\""
}

# ──────────────────────────────────────────────
# Process management (headless dispatch)
# ──────────────────────────────────────────────

_orch_parse_agent() {
  # Usage: read -r tool model <<< "$(_orch_parse_agent "$agent")"
  # Parses structured agent string: "claude" | "claude:sonnet" | "claude:opus"
  # stdout: two words - tool model (model may be empty)
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

orch_dispatch() {
  # Usage: orch_dispatch <issue> <area_dir> <agent>
  # Launches a headless claude -p background process for /dev-pipeline.
  # stdout: PID of the background process
  # Returns: 0 = launched, 1 = launch failed
  local issue=$1
  local area_dir=$2
  local agent=$3

  local area
  area=$(monorepo_area_from_dir "$area_dir")
  local repo
  repo=$(monorepo_area_repo "$area")

  local tool model
  read -r tool model <<< "$(_orch_parse_agent "$agent")"

  local log="$ORCH_BASE/${area}/issue-${issue}.log"
  local err_log="$ORCH_BASE/${area}/issue-${issue}.err"

  # Pipeline prompt: auto-approve merge since this is batch orchestration.
  # No stdin available in -p mode, so pipeline must make autonomous decisions.
  local prompt="/dev-pipeline ${area} #${issue}. Repo: ${repo}. Running headlessly - auto-approve merge when review passes (no critical issues). Auto-re-review after resolve. After completing all steps, exit."

  cd "$MONOREPO_ROOT" && CLAUDECODE= timeout 3600 claude -p \
    ${model:+--model "$model"} --dangerously-skip-permissions \
    --no-session-persistence \
    --allowedTools "Bash,Read,Edit,Write,Grep,Glob,Skill,Agent" \
    --max-turns 80 \
    "$prompt" > "$log" 2>"$err_log" &

  local pid=$!

  # Brief check that process started
  sleep 1
  if ! orch_process_alive "$pid"; then
    >&2 echo "[orchestrator] Process failed to start for issue #${issue}"
    return 1
  fi

  echo "$pid"
  return 0
}

orch_stop_process() {
  # Usage: orch_stop_process <pid>
  # Gracefully stops a headless process. Sends SIGTERM, waits, then SIGKILL.
  local pid=$1
  if [ -z "$pid" ] || [ "$pid" = "null" ]; then return 0; fi
  if ! orch_process_alive "$pid"; then return 0; fi

  kill "$pid" 2>/dev/null
  sleep 3
  if orch_process_alive "$pid"; then
    kill -9 "$pid" 2>/dev/null
  fi
}

orch_record_dispatch() {
  # Usage: orch_record_dispatch <area> <issue> <pid>
  local area=$1
  local issue=$2
  local pid=$3
  local now
  now=$(date -u +%Y-%m-%dT%H:%M:%SZ)

  orch_state_update "$area" \
    ".dispatched[\"$issue\"] = {pid: $pid, log: \"$ORCH_BASE/${area}/issue-${issue}.log\", dispatchedAt: \"$now\", lastActivity: \"$now\", lastCommitSha: null, pipelineStarted: false, retryCount: 0} | .status[\"$issue\"] = \"dispatched\""
}

# ──────────────────────────────────────────────
# PR lookup helper
# ──────────────────────────────────────────────

_orch_pr_list() {
  # Usage: _orch_pr_list <area> <issue> <state> <json_fields> <jq_filter>
  # Finds PRs that close the given issue. Uses -R for explicit repo targeting.
  # Avoid deprecated fields (projectCards etc.) - use number,title,state,body,url only.
  local area=$1 issue=$2 state=$3 json_fields=$4 jq_filter=$5
  local repo
  repo=$(monorepo_area_repo "$area")

  gh pr list \
    -R "$repo" \
    --search "\"Closes #${issue}\" OR \"Fixes #${issue}\" OR \"Resolves #${issue}\"" \
    --state "$state" --json "$json_fields" --jq "$jq_filter" 2>/dev/null
}

# ──────────────────────────────────────────────
# Completion detection
# ──────────────────────────────────────────────

orch_check_completion() {
  # Usage: orch_check_completion <issue> <area_dir>
  # Checks if a dispatched issue's pipeline has finished.
  # stdout: "completed", "failed", or "running"
  # Always returns 0 (safe for set -e callers).
  #
  # Detection priority:
  #   1. Signal file (explicit completion, if present)
  #   2. Process alive (PID still running?)
  #   3. Pipeline state file (absent + previously seen = completed)
  #   4. PR status (merged/open/absent)
  local issue=$1
  local area_dir=$2
  local area
  area=$(monorepo_area_from_dir "$area_dir")

  # 1. Signal file (highest priority - explicit completion signal)
  local signal
  signal=$(orch_signal_path "$area" "$issue")
  if [ -f "$signal" ]; then
    local content
    content=$(cat "$signal")
    if [ "$content" = "ok" ]; then
      echo "completed"; return 0
    else
      echo "failed"; return 0
    fi
  fi

  # Shared across checks 2-3
  local state
  state=$(orch_state_read "$area")
  local pid
  pid=$(echo "$state" | jq -r ".dispatched[\"$issue\"].pid // empty")
  local pipeline_state="$PIPELINE_DIR/${area}/issue-${issue}.state.json"
  local seen
  seen=$(echo "$state" | jq -r ".dispatched[\"$issue\"].pipelineStarted // false")

  # 2. Process alive check (replaces tmux pane command check)
  if [ -n "$pid" ] && orch_process_alive "$pid"; then
    # Process running - check if pipeline state file exists (to track pipelineStarted)
    if [ -f "$pipeline_state" ]; then
      if [ "$seen" != "true" ]; then
        orch_state_update "$area" ".dispatched[\"$issue\"].pipelineStarted = true" || true
      fi
    else
      # State file absent while process running - completed only if previously seen
      if [ "$seen" = "true" ]; then
        echo "completed"; return 0
      fi
    fi
    echo "running"; return 0
  fi

  # 3. Pipeline state file check (process exited)
  # Uses $pipeline_state and $seen from above
  if [ ! -f "$pipeline_state" ] && [ "$seen" = "true" ]; then
    echo "completed"; return 0
  fi

  # 4. PR status (process exited, state file inconclusive)
  local pr_states
  pr_states=$(_orch_pr_list "$area" "$issue" all "number,state" '[.[].state]')
  if echo "$pr_states" | grep -q '"MERGED"'; then
    echo "completed"; return 0
  fi
  if echo "$pr_states" | grep -q '"OPEN"'; then
    echo "running"; return 0
  fi

  # No signal, no process, no PR - failed
  echo "failed"; return 0
}

orch_update_last_activity() {
  # Usage: orch_update_last_activity <area> <issue> <commit_sha>
  local area=$1
  local issue=$2
  local sha=$3
  local now
  now=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  orch_state_update "$area" \
    ".dispatched[\"$issue\"].lastActivity = \"$now\" | .dispatched[\"$issue\"].lastCommitSha = \"$sha\""
}

# ──────────────────────────────────────────────
# Stall detection
# ──────────────────────────────────────────────

orch_detect_stall() {
  # Usage: orch_detect_stall <area> <issue>
  # stdout: "stalled" or "active"
  # Always returns 0 (safe for set -e callers).
  local area=$1
  local issue=$2
  local stall_seconds=600  # 10 minutes

  local state
  state=$(orch_state_read "$area")

  local last_activity
  last_activity=$(echo "$state" | jq -r ".dispatched[\"$issue\"].lastActivity // empty")
  if [ -z "$last_activity" ]; then
    echo "active"; return 0
  fi

  local last_ts
  last_ts=$(date -d "$last_activity" +%s 2>/dev/null || date -j -f "%Y-%m-%dT%H:%M:%SZ" "$last_activity" +%s 2>/dev/null)
  local now_ts
  now_ts=$(date +%s)
  local elapsed=$(( now_ts - last_ts ))

  if [ "$elapsed" -gt "$stall_seconds" ]; then
    # Verify no new commits since last check
    local last_sha
    last_sha=$(echo "$state" | jq -r ".dispatched[\"$issue\"].lastCommitSha // empty")

    local pr_number
    pr_number=$(_orch_pr_list "$area" "$issue" open number '.[0].number')

    # No open PR yet - apply extended stall threshold (2x normal) for pre-PR phase
    if [ -z "$pr_number" ] || [ "$pr_number" = "null" ]; then
      local extended_stall=$(( stall_seconds * 2 ))
      if [ "$elapsed" -gt "$extended_stall" ]; then
        echo "stalled"; return 0
      fi
      echo "active"; return 0
    fi

    local repo
    repo=$(monorepo_area_repo "$area")
    local latest_sha
    latest_sha=$(gh api "repos/${repo}/pulls/${pr_number}/commits" \
      --jq '.[-1].sha' 2>/dev/null)

    if [ -n "$latest_sha" ] && [ "$latest_sha" != "$last_sha" ]; then
      orch_update_last_activity "$area" "$issue" "$latest_sha"
      echo "active"; return 0
    fi
    echo "stalled"; return 0
  fi
  echo "active"; return 0
}

# ──────────────────────────────────────────────
# Unblocking
# ──────────────────────────────────────────────

orch_unblock() {
  # Usage: orch_unblock <area> <completed_issue>
  # Finds issues that were blocked only by completed_issue and marks them pending.
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

    # Get this issue's deps
    local deps
    deps=$(echo "$dag" | jq -r ".[\"$n\"] // [] | .[]")

    # Remove completed_issue from deps; check if remaining deps are all completed
    local still_blocked=0
    for dep in $deps; do
      [ "$dep" = "$done_issue" ] && continue
      local dep_status
      dep_status=$(echo "$state" | jq -r ".status[\"$dep\"]")
      if [ "$dep_status" != "completed" ] && [ "$dep_status" != "failed" ]; then
        still_blocked=1
        break
      fi
    done

    if [ "$still_blocked" -eq 0 ]; then
      orch_status_set "$area" "$n" "pending"
      unblocked="$unblocked $n"
    fi
  done

  echo "$unblocked"
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

  local state
  state=$(orch_state_read "$area")
  local dispatched_issues
  dispatched_issues=$(echo "$state" | jq -r '.dispatched | keys[]')

  # 1. Check completion for dispatched (non-terminal) issues only
  for issue in $dispatched_issues; do
    local cur_status
    cur_status=$(echo "$state" | jq -r ".status[\"$issue\"]")
    # Skip already-terminal issues
    [ "$cur_status" = "completed" ] || [ "$cur_status" = "failed" ] && continue

    local result
    result=$(orch_check_completion "$issue" "$area_dir")
    if [ "$result" = "completed" ] || [ "$result" = "failed" ]; then
      orch_status_set "$area" "$issue" "$result"
      orch_state_update "$area" "del(.dispatched[\"$issue\"])"
      >&2 echo "[orchestrator] Issue #${issue}: ${result}"

      local newly_unblocked
      newly_unblocked=$(orch_unblock "$area" "$issue")
      [ -n "$newly_unblocked" ] && >&2 echo "[orchestrator] Unblocked: $newly_unblocked"
    fi
  done

  # 2. Stall detection + bounded auto-retry for still-dispatched issues
  state=$(orch_state_read "$area")
  dispatched_issues=$(echo "$state" | jq -r '.dispatched | keys[]')
  for issue in $dispatched_issues; do
    local cur_status
    cur_status=$(echo "$state" | jq -r ".status[\"$issue\"]")
    [ "$cur_status" != "dispatched" ] && continue

    if [ "$(orch_detect_stall "$area" "$issue")" = "stalled" ]; then
      local pid
      pid=$(echo "$state" | jq -r ".dispatched[\"$issue\"].pid")
      local retry_count
      retry_count=$(echo "$state" | jq -r ".dispatched[\"$issue\"].retryCount // 0")

      if ! orch_process_alive "$pid" && [ "$retry_count" -lt 1 ]; then
        # Process died - attempt bounded retry (max 1)
        >&2 echo "[orchestrator] STALL: Issue #${issue} process dead - retrying (attempt $((retry_count + 1)))"
        local new_pid
        new_pid=$(orch_dispatch "$issue" "$area_dir" "$agent")
        if [ -n "$new_pid" ]; then
          local retry_now
          retry_now=$(date -u +%Y-%m-%dT%H:%M:%SZ)
          orch_state_update "$area" \
            ".dispatched[\"$issue\"].pid = $new_pid | .dispatched[\"$issue\"].retryCount = $((retry_count + 1)) | .dispatched[\"$issue\"].dispatchedAt = \"$retry_now\" | .dispatched[\"$issue\"].lastActivity = \"$retry_now\" | .dispatched[\"$issue\"].pipelineStarted = false"
          >&2 echo "[orchestrator] Re-dispatched #${issue} - PID $new_pid"
        else
          >&2 echo "[orchestrator] STALL: Issue #${issue} - re-dispatch failed"
        fi
      elif [ "$retry_count" -ge 1 ]; then
        # Already retried once - mark as failed
        >&2 echo "[orchestrator] STALL: Issue #${issue} - retry exhausted, marking failed"
        orch_stop_process "$pid"
        orch_status_set "$area" "$issue" "failed"
        orch_state_update "$area" "del(.dispatched[\"$issue\"])"
        local newly_unblocked
        newly_unblocked=$(orch_unblock "$area" "$issue")
        [ -n "$newly_unblocked" ] && >&2 echo "[orchestrator] Unblocked: $newly_unblocked"
      else
        >&2 echo "[orchestrator] STALL detected: Issue #${issue} - no activity for 10+ minutes"
        >&2 echo "[orchestrator] Process PID $pid still alive. Consider: stop, retry, or skip"
      fi
    fi
  done

  # 3. Dispatch pending issues as background processes (respecting maxConcurrent)
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
        orch_record_dispatch "$area" "$issue" "$pid"
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
  printf "%-8s %-12s %s\n" "Issue" "Status" "PR"
  echo "----------------------------------------"

  local issues
  issues=$(echo "$state" | jq -r '.issues[]')
  for issue in $issues; do
    local status
    status=$(echo "$state" | jq -r ".status[\"$issue\"]")
    local pr_url=""
    if [ "$status" = "completed" ]; then
      pr_url=$(_orch_pr_list "$area" "$issue" merged url '.[0].url')
    fi
    printf "%-8s %-12s %s\n" "#${issue}" "$status" "$pr_url"
  done
  echo "=================================="
}
