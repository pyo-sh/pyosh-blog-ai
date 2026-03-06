#!/bin/bash
# pipeline-helpers.sh - Shell helpers for dev-pipeline skill
# Source this file or use functions individually via the AI's Bash tool.

# Source shared monorepo helpers for MONOREPO_ROOT and area resolution.
_PIPELINE_HELPERS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$_PIPELINE_HELPERS_DIR/../../../../.agents/scripts/monorepo-helpers.sh"
PIPELINE_DIR="$MONOREPO_ROOT/.workspace/pipeline"
PIPELINE_LOG_DIR="$PIPELINE_DIR/logs"
WORKTREE_DIR="$MONOREPO_ROOT/.workspace/worktrees"

# ──────────────────────────────────────────────
# State management
# ──────────────────────────────────────────────

pipeline_state_path() {
  local issue=$1
  local area=$2
  echo "$PIPELINE_DIR/${area}/issue-${issue}.state.json"
}

pipeline_init() {
  local area=$1
  mkdir -p "$PIPELINE_DIR/$area" "$PIPELINE_LOG_DIR" "$WORKTREE_DIR"
}

pipeline_state_exists() {
  local issue=$1
  local area=$2
  [ -f "$(pipeline_state_path "$issue" "$area")" ]
}

pipeline_state_read() {
  local issue=$1
  local area=$2
  cat "$(pipeline_state_path "$issue" "$area")"
}

pipeline_state_write() {
  # Atomic write: write to .tmp then mv (POSIX atomic rename).
  # Prevents half-written JSON on crash.
  local issue=$1
  local area=$2
  local json=$3
  local path
  path=$(pipeline_state_path "$issue" "$area")
  local tmp
  tmp=$(mktemp "${path}.XXXXXX")
  echo "$json" > "$tmp" && mv "$tmp" "$path" || { rm -f "$tmp"; return 1; }
}

pipeline_state_update() {
  # Update specific fields in state via jq expression.
  # Usage: pipeline_state_update <issue> <area> <jq_expr>
  # Example: pipeline_state_update 42 client '.step = "review" | .reviewRound += 1'
  local issue=$1
  local area=$2
  local jq_expr=$3
  local current
  current=$(pipeline_state_read "$issue" "$area")
  local updated
  if ! updated=$(echo "$current" | jq "$jq_expr | .updatedAt = (now | todate)"); then
    >&2 echo "[pipeline] jq failed for expression: $jq_expr"
    return 1
  fi
  if [ -z "$updated" ] || [ "$updated" = "null" ]; then
    >&2 echo "[pipeline] jq produced empty/null output for: $jq_expr"
    return 1
  fi
  pipeline_state_write "$issue" "$area" "$updated"
}

pipeline_state_delete() {
  local issue=$1
  local area=$2
  rm -f "$(pipeline_state_path "$issue" "$area")"
}

# ──────────────────────────────────────────────
# Headless execution (synchronous)
# ──────────────────────────────────────────────

pipeline_run_headless() {
  # Run claude -p synchronously (blocking). Returns when subprocess exits.
  # Usage: pipeline_run_headless <workdir> <prompt> <issue> <area> <stage>
  # stage: "review" or "resolve" (determines tool allowlist and max-turns)
  # stdout: log file path
  # Returns: exit code from claude -p (0=success, 124=timeout, other=error)
  local workdir=$1
  local prompt=$2
  local issue=$3
  local area=$4
  local stage=$5

  local log="$PIPELINE_LOG_DIR/issue-${issue}-${stage}.log"

  local tools max_turns timeout_sec
  case "$stage" in
    review)
      tools="Bash,Read,Skill"
      max_turns=15
      timeout_sec=900
      ;;
    resolve)
      tools="Bash,Read,Edit,Write,Grep,Glob,Skill"
      max_turns=25
      timeout_sec=900
      ;;
  esac

  echo "$log"

  cd "$workdir" || return 3
  CLAUDECODE= timeout "$timeout_sec" claude -p \
    --dangerously-skip-permissions \
    --no-session-persistence \
    --allowedTools "$tools" \
    --max-turns "$max_turns" \
    "$prompt" > "$log" 2>"${log%.log}.err"
}

pipeline_resolve_worktree_path() {
  # Resolves actual worktree directory, checking current path first, then legacy.
  # stdout: absolute path on success, "PATH_INVALID" on failure
  # Returns: 0 = found, 3 = not found
  local issue=$1
  local area=$2

  local current_path="$WORKTREE_DIR/issue-${issue}"
  if [ -d "$current_path" ]; then
    echo "$current_path"
    return 0
  fi

  if [ -n "$area" ]; then
    local legacy_path="$MONOREPO_ROOT/$area/.workspace/worktrees/issue-${issue}"
    if [ -d "$legacy_path" ]; then
      echo "$legacy_path"
      return 0
    fi
  fi

  echo "PATH_INVALID"
  return 3
}

# ──────────────────────────────────────────────
# API checks (single-shot, no polling)
# ──────────────────────────────────────────────

pipeline_check_review_exists() {
  # Check if a review exists with body starting "## Review Summary".
  # Returns: 0 = found (review_id on stdout), 1 = not found
  local area_dir=$1
  local pr=$2
  local last_review_id=${3:-0}

  local review_id
  review_id=$(cd "$area_dir" && gh api "repos/{owner}/{repo}/pulls/${pr}/reviews" \
    --jq "[.[] | select(.id > ${last_review_id})
               | select(.body | startswith(\"## Review Summary\"))]
          | last // empty | .id")

  if [ -n "$review_id" ] && [ "$review_id" != "null" ]; then
    echo "$review_id"
    return 0
  fi
  return 1
}

pipeline_fetch_review() {
  local area_dir=$1
  local pr=$2
  local review_id=$3
  cd "$area_dir" && gh api "repos/{owner}/{repo}/pulls/${pr}/reviews/${review_id}" \
    --jq '{state: .state, body: .body}'
}

pipeline_check_new_commits() {
  # Check if new commits exist after a known SHA.
  # Returns: 0 = found (new_sha on stdout), 1 = not found
  local area_dir=$1
  local pr=$2
  local last_commit_sha=$3

  local latest_sha
  latest_sha=$(cd "$area_dir" && gh api "repos/{owner}/{repo}/pulls/${pr}/commits" \
    --jq '.[-1].sha')

  if [ -n "$latest_sha" ] && [ "$latest_sha" != "null" ] && [ "$latest_sha" != "$last_commit_sha" ]; then
    echo "$latest_sha"
    return 0
  fi
  return 1
}

# ──────────────────────────────────────────────
# Self-healing (stage retry + recovery log)
# ──────────────────────────────────────────────

pipeline_stage_retry() {
  # Increment stage retry counter, check against max.
  # Usage: pipeline_stage_retry <issue> <area> <stage>
  # Returns: 0 = can retry, 1 = max reached
  local issue=$1
  local area=$2
  local stage=$3
  local state
  state=$(pipeline_state_read "$issue" "$area")
  local retries
  retries=$(echo "$state" | jq -r ".stageRetries.${stage} // 0")
  local max
  max=$(echo "$state" | jq -r ".maxStageRetries // 3")
  if [ "$retries" -ge "$max" ]; then
    return 1
  fi
  pipeline_state_update "$issue" "$area" ".stageRetries.${stage} = $((retries + 1))"
}

pipeline_recovery_log() {
  # Append a recovery attempt to recoveryLog.
  # Usage: pipeline_recovery_log <issue> <area> <stage> <error> <action> <result>
  local issue=$1
  local area=$2
  local stage=$3
  local error=$4
  local action=$5
  local result=$6
  local entry
  entry=$(jq -n --arg s "$stage" --arg e "$error" --arg a "$action" --arg r "$result" \
    '{stage:$s, error:$e, action:$a, result:$r, timestamp:(now|todate)}')
  pipeline_state_update "$issue" "$area" ".recoveryLog += [$entry]"
}

pipeline_format_escalation() {
  # Format recovery log for user escalation.
  # Usage: pipeline_format_escalation <issue> <area> <stage>
  local issue=$1
  local area=$2
  local stage=$3
  local state
  state=$(pipeline_state_read "$issue" "$area")

  local info
  info=$(echo "$state" | jq -r --arg stage "$stage" '
    "[pipeline] Stage \"\($stage)\" failed after \(.maxStageRetries // 3) recovery attempts.\n",
    "Recovery log:",
    (.recoveryLog // [] | map(select(.stage == $stage))
      | .[] | "  #\(.timestamp) \(.error) -> \(.action) -> \(.result)"),
    "",
    "Worktree: \(.worktree)",
    "Branch: \(.branch)",
    "PR: #\(.pr)",
    "",
    "Action needed: fix manually, then resume with /dev-pipeline"')
  echo "$info"
}

# ──────────────────────────────────────────────
# Merge queue (lock-based serialization)
# ──────────────────────────────────────────────

pipeline_acquire_merge_lock() {
  # Acquire area-level merge lock. Only one pipeline can merge at a time.
  # Uses mkdir for atomic creation + PID file for stale lock detection.
  # Usage: pipeline_acquire_merge_lock <area> <issue>
  # Returns: 0 = acquired, 1 = timeout
  local area=$1
  local issue=$2
  local lock_dir="$PIPELINE_DIR/${area}/merge.lock"
  local max_wait=300  # 5 minutes
  local interval=10
  local waited=0

  while ! mkdir "$lock_dir" 2>/dev/null; do
    # Check if holder is still alive (stale lock recovery)
    local holder_pid
    holder_pid=$(cat "$lock_dir/pid" 2>/dev/null)
    if [ -n "$holder_pid" ] && ! kill -0 "$holder_pid" 2>/dev/null; then
      >&2 echo "[pipeline] Stale merge lock (PID $holder_pid dead) - reclaiming"
      rm -rf "$lock_dir"
      continue
    fi

    if [ "$waited" -ge "$max_wait" ]; then
      local holder_issue
      holder_issue=$(cat "$lock_dir/issue" 2>/dev/null)
      >&2 echo "[pipeline] Merge lock timeout after ${max_wait}s (held by issue #${holder_issue:-unknown})"
      return 1
    fi

    >&2 echo "[pipeline] Merge lock held - waiting (${waited}s/${max_wait}s)"
    sleep "$interval"
    waited=$((waited + interval))
  done

  # Write lock metadata
  echo "$$" > "$lock_dir/pid"
  echo "$issue" > "$lock_dir/issue"
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$lock_dir/acquired"
  return 0
}

pipeline_release_merge_lock() {
  # Release area-level merge lock.
  # Usage: pipeline_release_merge_lock <area>
  local area=$1
  local lock_dir="$PIPELINE_DIR/${area}/merge.lock"
  rm -rf "$lock_dir"
}

# ──────────────────────────────────────────────
# Cleanup
# ──────────────────────────────────────────────

pipeline_cleanup() {
  local issue=$1
  local area=$2
  local branch=$3

  # Clean up log files
  rm -f "$PIPELINE_LOG_DIR"/issue-"${issue}"-*.log "$PIPELINE_LOG_DIR"/issue-"${issue}"-*.err

  local wt="$WORKTREE_DIR/issue-${issue}"
  if [ -d "$wt" ]; then
    cd "$MONOREPO_ROOT/$area" && git worktree remove "$wt" --force
    git worktree prune
  fi

  cd "$MONOREPO_ROOT/$area" && git branch -D "$branch" 2>/dev/null
  pipeline_state_delete "$issue" "$area"
}

# ──────────────────────────────────────────────
# Listing active pipelines
# ──────────────────────────────────────────────

pipeline_list() {
  if [ -d "$PIPELINE_DIR" ]; then
    local found=0
    for f in "$PIPELINE_DIR"/*/issue-*.state.json; do
      [ -f "$f" ] || continue
      found=1
      local issue step area
      issue=$(jq -r '.issue' "$f")
      area=$(jq -r '.area' "$f")
      step=$(jq -r '.step' "$f")
      echo "Issue #${issue} (${area}): step=${step}"
    done
    [ "$found" -eq 0 ] && echo "No active pipelines"
  else
    echo "No active pipelines"
  fi
}
