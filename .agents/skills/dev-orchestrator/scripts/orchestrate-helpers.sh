#!/bin/bash
# orchestrate-helpers.sh — Shell helpers for dev-orchestrator skill
# Source this file at orchestrator start.

# Detect monorepo root
_GIT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
if [ -d "$_GIT_ROOT/../server" ] && [ -f "$_GIT_ROOT/../CLAUDE.md" ]; then
  MONOREPO_ROOT="$(cd "$_GIT_ROOT/.." && pwd)"
else
  MONOREPO_ROOT="$_GIT_ROOT"
fi
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
  # Usage: orch_init <area> <agent> <orchestrator_pane> <issues_json> <dag_json>
  # Creates initial batch state file.
  local area=$1
  local agent=$2
  local orch_pane=$3
  local issues_json=$4  # JSON array e.g. '[1,2,3]'
  local dag_json=$5     # JSON object e.g. '{"3":[1,2]}'

  mkdir -p "$ORCH_BASE/$area"

  local batch_id
  batch_id="batch-$(date +%Y%m%d-%H%M%S)"

  # Build initial status: pending for issues with no deps, blocked otherwise
  local status_json
  status_json=$(echo "$issues_json $dag_json" | jq -n \
    --argjson issues "$issues_json" \
    --argjson dag "$dag_json" \
    'reduce $issues[] as $n ({}; . + {($n|tostring): (if ($dag[($n|tostring)] // []) | length > 0 then "blocked" else "pending" end)})')

  jq -n \
    --arg area "$area" \
    --arg batchId "$batch_id" \
    --argjson issues "$issues_json" \
    --argjson dag "$dag_json" \
    --argjson status "$status_json" \
    --arg agent "$agent" \
    --arg orchPane "$orch_pane" \
    --arg now "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    '{area: $area, batchId: $batchId, issues: $issues, dag: $dag,
      status: $status, dispatched: {}, agent: $agent,
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
  local area=$1
  local filter=$2
  local path
  path=$(orch_state_path "$area")
  local tmp
  tmp=$(jq "($filter) | .updatedAt = \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"" "$path")
  echo "$tmp" > "$path"
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

orch_find_idle_panes() {
  # Usage: orch_find_idle_panes [exclude_pane]
  # Returns space-separated list of idle pane IDs in the current session.
  # Idle = shell (bash/zsh/sh/fish) with no foreground job.
  local exclude=${1:-""}

  tmux list-panes -s -F '#{pane_id} #{pane_current_command}' 2>/dev/null \
    | awk -v excl="$exclude" '
        $2 == "bash" || $2 == "zsh" || $2 == "sh" || $2 == "fish" {
          if ($1 != excl) print $1
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
  area=$(basename "$area_dir")
  # workspace area dir is monorepo root; area label is "workspace"
  if [ "$area_dir" = "$MONOREPO_ROOT" ]; then
    area="workspace"
  fi

  local prompt
  if [ "$agent" = "codex" ]; then
    prompt="/dev-pipeline ${area} #${issue}"
    tmux send-keys -t "$pane_id" \
      "codex exec --dangerously-bypass-approvals-and-sandbox '${prompt}'" Enter
  else
    prompt="/dev-pipeline ${area} #${issue}"
    tmux send-keys -t "$pane_id" \
      "claude --dangerously-skip-permissions '${prompt}'" Enter
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
# Completion detection
# ──────────────────────────────────────────────

orch_check_completion() {
  # Usage: orch_check_completion <issue> <area_dir>
  # Checks if a dispatched issue's pipeline has finished.
  # stdout: "completed", "failed", or "running"
  # Returns: 0 = completed/failed (terminal), 1 = still running
  local issue=$1
  local area_dir=$2
  local area
  area=$(basename "$area_dir")
  [ "$area_dir" = "$MONOREPO_ROOT" ] && area="workspace"

  # 1. Signal file
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

  # 2. Pipeline state gone = pipeline finished (check PR status)
  local pipeline_state="$PIPELINE_DIR/issue-${issue}.state.json"
  if [ ! -f "$pipeline_state" ]; then
    # Grace window: if recently dispatched, pipeline may not have created state yet
    local dispatch_time
    dispatch_time=$(orch_state_read "$area" | jq -r ".dispatched[\"$issue\"].dispatchedAt // empty")
    if [ -n "$dispatch_time" ]; then
      local dispatch_ts now_ts elapsed
      dispatch_ts=$(date -d "$dispatch_time" +%s 2>/dev/null || date -j -f "%Y-%m-%dT%H:%M:%SZ" "$dispatch_time" +%s 2>/dev/null)
      now_ts=$(date +%s)
      elapsed=$(( now_ts - dispatch_ts ))
      if [ "$elapsed" -lt 60 ]; then
        # Within startup grace window — pipeline may not have written state yet
        echo "running"; return 1
      fi
    fi

    # Check if PR is merged
    local pr_state
    pr_state=$(cd "$area_dir" && gh pr list \
      --search "Closes #${issue}" --state merged --json number --jq 'length' 2>/dev/null)
    if [ "${pr_state:-0}" -gt 0 ] 2>/dev/null; then
      echo "completed"; return 0
    fi
    # PR exists but not merged = pipeline may have cleaned up without merging
    local pr_open
    pr_open=$(cd "$area_dir" && gh pr list \
      --search "Closes #${issue}" --state open --json number --jq 'length' 2>/dev/null)
    if [ "${pr_open:-0}" -eq 0 ] 2>/dev/null; then
      # No state file, no open PR, no merged PR → failed or never started
      echo "failed"; return 0
    fi
  fi

  echo "running"; return 1
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
  # Returns: 0 = stalled (no activity > 10 min), 1 = active
  local area=$1
  local issue=$2
  local area_dir=$3
  local stall_seconds=600  # 10 minutes

  local state
  state=$(orch_state_read "$area")

  local last_activity
  last_activity=$(echo "$state" | jq -r ".dispatched[\"$issue\"].lastActivity // empty")
  [ -z "$last_activity" ] && return 1

  local last_ts
  last_ts=$(date -d "$last_activity" +%s 2>/dev/null || date -j -f "%Y-%m-%dT%H:%M:%SZ" "$last_activity" +%s 2>/dev/null)
  local now_ts
  now_ts=$(date +%s)
  local elapsed=$(( now_ts - last_ts ))

  if [ "$elapsed" -gt "$stall_seconds" ]; then
    # Verify no new commits since last check
    local last_sha
    last_sha=$(echo "$state" | jq -r ".dispatched[\"$issue\"].lastCommitSha // empty")
    local latest_sha
    latest_sha=$(cd "$area_dir" && gh pr list \
      --search "Closes #${issue}" --state open \
      --json number --jq '.[0].number' 2>/dev/null \
      | xargs -I{} gh api "repos/{owner}/{repo}/pulls/{}/commits" \
          --jq '.[-1].sha' 2>/dev/null)

    if [ -n "$latest_sha" ] && [ "$latest_sha" != "$last_sha" ]; then
      orch_update_last_activity "$area" "$issue" "$latest_sha"
      return 1
    fi
    return 0
  fi
  return 1
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

  # 2. Stall detection for still-dispatched issues
  state=$(orch_state_read "$area")
  dispatched_issues=$(echo "$state" | jq -r '.dispatched | keys[]')
  for issue in $dispatched_issues; do
    local cur_status
    cur_status=$(echo "$state" | jq -r ".status[\"$issue\"]")
    [ "$cur_status" != "dispatched" ] && continue

    if orch_detect_stall "$area" "$issue" "$area_dir"; then
      >&2 echo "[orchestrator] STALL detected: Issue #${issue} — no activity for 10+ minutes"
      >&2 echo "[orchestrator] Consider: inspect pane, retry, or skip"
    fi
  done

  # 3. Dispatch pending issues to idle panes
  state=$(orch_state_read "$area")
  local pending_issues
  pending_issues=$(echo "$state" | jq -r '.status | to_entries[] | select(.value == "pending") | .key')

  if [ -n "$pending_issues" ]; then
    local idle_panes
    idle_panes=$(orch_find_idle_panes "$orch_pane")
    local pane_array=($idle_panes)
    local pane_idx=0

    for issue in $pending_issues; do
      [ $pane_idx -ge ${#pane_array[@]} ] && break
      local pane="${pane_array[$pane_idx]}"

      orch_dispatch "$issue" "$pane" "$area_dir" "$agent"
      if [ $? -eq 0 ]; then
        orch_record_dispatch "$area" "$issue" "$pane"
        >&2 echo "[orchestrator] Dispatched #${issue} → pane $pane"
        pane_idx=$((pane_idx + 1))
      fi
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
      pr_url=$(cd "$area_dir" && gh pr list \
        --search "Closes #${issue}" --state merged \
        --json url --jq '.[0].url' 2>/dev/null)
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
