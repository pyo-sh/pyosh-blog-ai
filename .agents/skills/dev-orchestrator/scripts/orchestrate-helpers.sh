#!/bin/bash
# orchestrate-helpers.sh — Shell helpers for dev-orchestrator skill
# Source this file at orchestrator start.

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
  # Usage: orch_init <area> <agent> <orchestrator_pane> <issues_json> <dag_json> [max_concurrent]
  # Creates initial batch state file.
  local area=$1
  local agent=$2
  local orch_pane=$3
  local issues_json=$4  # JSON array e.g. '[1,2,3]'
  local dag_json=$5     # JSON object e.g. '{"3":[1,2]}'
  local max_concurrent=${6:-99}  # default: no practical limit

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
    --arg orchPane "$orch_pane" \
    --argjson maxConcurrent "$max_concurrent" \
    --arg now "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    '{area: $area, batchId: $batchId, issues: $issues, dag: $dag,
      status: $status, dispatched: {}, agent: $agent,
      maxConcurrent: $maxConcurrent,
      orchestratorPane: $orchPane,
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
# Pane management
# ──────────────────────────────────────────────

ORCH_WORK_WINDOWS="${ORCH_WORK_WINDOWS:-server1 server2 client1 client2}"

orch_find_idle_panes() {
  # Usage: orch_find_idle_panes [exclude_pane]
  # Returns space-separated list of idle pane IDs (one per work window).
  # Only considers the first pane (lowest index) of each window to prevent
  # dispatching to sub-panes. Uses head -1 instead of index == 0 to be
  # independent of tmux pane-base-index setting.
  # Idle = shell (bash/zsh/sh/fish) with no foreground job.
  local exclude=${1:-""}

  local current_session
  current_session=$(tmux display-message -p '#{session_id}' 2>/dev/null)

  for win in $ORCH_WORK_WINDOWS; do
    tmux list-panes -t "$win" \
      -F '#{session_id} #{pane_id} #{pane_current_command}' 2>/dev/null \
      | head -1
  done \
    | awk -v sess="$current_session" -v excl="$exclude" '
        $1 == sess && ($3 == "bash" || $3 == "zsh" || $3 == "sh" || $3 == "fish") {
          if ($2 != excl) print $2
        }' \
    | tr '\n' ' '
}

orch_pane_alive() {
  local pane_id=$1
  tmux list-panes -a -F '#{pane_id}' 2>/dev/null | grep -qx "$pane_id"
}

orch_dispatch() {
  # Usage: orch_dispatch <issue> <pane_id> <area_dir> <agent>
  # Sends /dev-pipeline #{issue} to the target pane.
  # Returns: 0 = sent, 1 = pane dead
  local issue=$1
  local pane_id=$2
  local area_dir=$3
  local agent=$4

  if ! orch_pane_alive "$pane_id"; then
    return 1
  fi

  local area
  area=$(monorepo_area_from_dir "$area_dir")

  # Always start from monorepo root so Claude/Codex can find root repo skills
  # (dev-pipeline, dev-review, dev-resolve). The area param in the prompt
  # tells /dev-pipeline which subdirectory to work in.
  local prompt
  if [ "$agent" = "codex" ]; then
    prompt="/dev-pipeline ${area} #${issue}. Use ${agent} for review and resolve panes."
    tmux send-keys -t "$pane_id" \
      "cd '${MONOREPO_ROOT}' && codex exec --dangerously-bypass-approvals-and-sandbox '${prompt}'" Enter
  else
    prompt="/dev-pipeline ${area} #${issue}. Use ${agent} for review and resolve panes."
    tmux send-keys -t "$pane_id" \
      "cd '${MONOREPO_ROOT}' && claude --dangerously-skip-permissions '${prompt}'" Enter
  fi

  return 0
}

orch_record_dispatch() {
  # Usage: orch_record_dispatch <area> <issue> <pane_id>
  local area=$1
  local issue=$2
  local pane_id=$3
  local now
  now=$(date -u +%Y-%m-%dT%H:%M:%SZ)

  orch_state_update "$area" \
    ".dispatched[\"$issue\"] = {pane: \"$pane_id\", dispatchedAt: \"$now\", lastActivity: \"$now\", lastCommitSha: null}"
  orch_status_set "$area" "$issue" "dispatched"
}

# ──────────────────────────────────────────────
# PR lookup helper
# ──────────────────────────────────────────────

_orch_pr_list() {
  # Usage: _orch_pr_list <area_dir> <issue> <state> <json_fields> <jq_filter>
  # Finds PRs that close the given issue, matching Closes/Fixes/Resolves #N.
  local area_dir=$1 issue=$2 state=$3 json_fields=$4 jq_filter=$5
  cd "$area_dir" && gh pr list \
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
  #   1. Signal file (written by pipeline AI at end)
  #   2. Pane command (AI process still running?)
  #   3. PR status (merged/open/absent)
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

  # 2. Pane command check - if AI process is still running, it's running
  local state
  state=$(orch_state_read "$area")
  local pane_id
  pane_id=$(echo "$state" | jq -r ".dispatched[\"$issue\"].pane // empty")

  if [ -n "$pane_id" ] && orch_pane_alive "$pane_id"; then
    local cmd
    cmd=$(tmux display-message -t "$pane_id" -p '#{pane_current_command}' 2>/dev/null)
    if [[ "$cmd" == "claude" ]] || [[ "$cmd" == "codex" ]] || [[ "$cmd" == "node" ]]; then
      echo "running"; return 0
    fi
    # Pane alive but shell prompt (AI exited) - fall through to PR check
  fi

  # 3. AI process exited or pane dead - check PR status
  local pr_merged
  pr_merged=$(_orch_pr_list "$area_dir" "$issue" merged number 'length')
  if [ "${pr_merged:-0}" -gt 0 ] 2>/dev/null; then
    echo "completed"; return 0
  fi

  local pr_open
  pr_open=$(_orch_pr_list "$area_dir" "$issue" open number 'length')
  if [ "${pr_open:-0}" -gt 0 ] 2>/dev/null; then
    echo "running"; return 0
  fi

  # No signal, no AI process, no PR - failed
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
  # Usage: orch_detect_stall <area> <issue> <area_dir>
  # stdout: "stalled" or "active"
  # Always returns 0 (safe for set -e callers).
  local area=$1
  local issue=$2
  local area_dir=$3
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
    pr_number=$(_orch_pr_list "$area_dir" "$issue" open number '.[0].number')

    # No open PR yet - apply extended stall threshold (2x normal) for pre-PR phase
    if [ -z "$pr_number" ] || [ "$pr_number" = "null" ]; then
      local extended_stall=$(( stall_seconds * 2 ))
      if [ "$elapsed" -gt "$extended_stall" ]; then
        echo "stalled"; return 0
      fi
      echo "active"; return 0
    fi

    local latest_sha
    latest_sha=$(cd "$area_dir" && gh api "repos/{owner}/{repo}/pulls/${pr_number}/commits" \
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
  # Usage: orch_poll_cycle <area> <area_dir> <agent> <orchestrator_pane>
  # One polling iteration: check completion, detect stalls, unblock, dispatch.
  local area=$1
  local area_dir=$2
  local agent=$3
  local orch_pane=$4

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
      # Remove from dispatched to avoid re-checking
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

    if [ "$(orch_detect_stall "$area" "$issue" "$area_dir")" = "stalled" ]; then
      local pane_id
      pane_id=$(echo "$state" | jq -r ".dispatched[\"$issue\"].pane")
      local retry_count
      retry_count=$(echo "$state" | jq -r ".dispatched[\"$issue\"].retryCount // 0")

      if ! orch_pane_alive "$pane_id" && [ "$retry_count" -lt 1 ]; then
        # Pane died — attempt bounded retry (max 1)
        >&2 echo "[orchestrator] STALL: Issue #${issue} pane dead — retrying (attempt $((retry_count + 1)))"
        local idle_panes
        idle_panes=$(orch_find_idle_panes "$orch_pane")
        local retried=0
        for p in $idle_panes; do
          if orch_dispatch "$issue" "$p" "$area_dir" "$agent"; then
            local retry_now
            retry_now=$(date -u +%Y-%m-%dT%H:%M:%SZ)
            orch_state_update "$area" \
              ".dispatched[\"$issue\"].pane = \"$p\" | .dispatched[\"$issue\"].retryCount = $((retry_count + 1)) | .dispatched[\"$issue\"].dispatchedAt = \"$retry_now\" | .dispatched[\"$issue\"].lastActivity = \"$retry_now\""
            >&2 echo "[orchestrator] Re-dispatched #${issue} → pane $p"
            retried=1
            break
          fi
        done
        [ "$retried" -eq 0 ] && >&2 echo "[orchestrator] STALL: Issue #${issue} — no idle panes for retry"
      elif [ "$retry_count" -ge 1 ]; then
        # Already retried once — mark as failed
        >&2 echo "[orchestrator] STALL: Issue #${issue} — retry exhausted, marking failed"
        orch_status_set "$area" "$issue" "failed"
        orch_state_update "$area" "del(.dispatched[\"$issue\"])"
        local newly_unblocked
        newly_unblocked=$(orch_unblock "$area" "$issue")
        [ -n "$newly_unblocked" ] && >&2 echo "[orchestrator] Unblocked: $newly_unblocked"
      else
        >&2 echo "[orchestrator] STALL detected: Issue #${issue} — no activity for 10+ minutes"
        >&2 echo "[orchestrator] Consider: inspect pane, retry, or skip"
      fi
    fi
  done

  # 3. Dispatch pending issues to idle panes (respecting maxConcurrent)
  state=$(orch_state_read "$area")
  local max_concurrent
  max_concurrent=$(echo "$state" | jq -r '.maxConcurrent // 99')
  local active_count
  active_count=$(echo "$state" | jq '[.status | to_entries[] | select(.value == "dispatched")] | length')

  local pending_issues
  pending_issues=$(echo "$state" | jq -r '.status | to_entries[] | select(.value == "pending") | .key')

  if [ -n "$pending_issues" ] && [ "$active_count" -lt "$max_concurrent" ]; then
    local slots_available=$(( max_concurrent - active_count ))
    local idle_panes
    idle_panes=$(orch_find_idle_panes "$orch_pane")
    local pane_array=($idle_panes)
    local pane_idx=0
    local dispatched_count=0

    for issue in $pending_issues; do
      [ "$dispatched_count" -ge "$slots_available" ] && break
      [ $pane_idx -ge ${#pane_array[@]} ] && break
      local pane="${pane_array[$pane_idx]}"

      if orch_dispatch "$issue" "$pane" "$area_dir" "$agent"; then
        orch_record_dispatch "$area" "$issue" "$pane"
        if ! orch_verify_startup "$pane" 5; then
          >&2 echo "[orchestrator] Startup failed for #${issue} on pane $pane — reverting to pending"
          orch_status_set "$area" "$issue" "pending"
          orch_state_update "$area" "del(.dispatched[\"$issue\"])"
        else
          >&2 echo "[orchestrator] Dispatched #${issue} → pane $pane"
          dispatched_count=$((dispatched_count + 1))
        fi
      else
        >&2 echo "[orchestrator] Pane $pane dead — skipping for issue #${issue}"
      fi
      pane_idx=$((pane_idx + 1))  # always advance to skip dead panes
    done
  fi
}

# ──────────────────────────────────────────────
# Summary
# ──────────────────────────────────────────────

orch_print_summary() {
  # Usage: orch_print_summary <area> <area_dir>
  local area=$1
  local area_dir=$2

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
      pr_url=$(_orch_pr_list "$area_dir" "$issue" merged url '.[0].url')
    fi
    printf "%-8s %-12s %s\n" "#${issue}" "$status" "$pr_url"
  done
  echo "=================================="
}

# ──────────────────────────────────────────────
# Verify startup
# ──────────────────────────────────────────────

orch_verify_startup() {
  # Usage: orch_verify_startup <pane_id> [grace_seconds]
  # Returns: 0 = alive after grace period, 1 = died
  local pane_id=$1
  local grace=${2:-5}
  sleep "$grace"
  orch_pane_alive "$pane_id"
}
