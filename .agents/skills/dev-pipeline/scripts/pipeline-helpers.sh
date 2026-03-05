#!/bin/bash
# pipeline-helpers.sh - Shell helpers for dev-pipeline skill
# Source this file or use functions individually via the AI's Bash tool.

# Source shared monorepo helpers for MONOREPO_ROOT and area resolution.
_PIPELINE_HELPERS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$_PIPELINE_HELPERS_DIR/../../../../.agents/scripts/monorepo-helpers.sh"
PIPELINE_DIR="$MONOREPO_ROOT/.workspace/pipeline"
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
  mkdir -p "$PIPELINE_DIR/$area" "$WORKTREE_DIR"
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
# tmux pane management
# ──────────────────────────────────────────────

pipeline_orchestrator_pane() {
  # Prefer $TMUX_PANE (process's own pane, not the focused pane, which
  # differs on --continue sessions). Fall back to tmux display-message
  # for contexts where $TMUX_PANE is unset.
  if [ -n "$TMUX_PANE" ]; then
    echo "$TMUX_PANE"
  else
    tmux display-message -p '#{pane_id}' 2>/dev/null
  fi
}

pipeline_open_pane() {
  # Usage: pipeline_open_pane <working_dir> <prompt> [agent] [target_pane]
  local workdir=$1
  local prompt=$2
  local agent=${3:-claude}
  local target_pane=$4

  local cmd
  if [ "$agent" = "codex" ]; then
    cmd="codex exec --dangerously-bypass-approvals-and-sandbox '$prompt'"
  else
    cmd="claude --dangerously-skip-permissions '$prompt'"
  fi

  if [ -n "$target_pane" ]; then
    tmux split-window -h -d -t "$target_pane" -P -F '#{pane_id}' \
      "cd '$workdir' && $cmd"
  else
    tmux split-window -h -d -P -F '#{pane_id}' \
      "cd '$workdir' && $cmd"
  fi
}

pipeline_kill_pane() {
  local pane_id=$1
  if [ -n "$pane_id" ]; then
    tmux kill-pane -t "$pane_id" 2>/dev/null
  fi
}

pipeline_pane_alive() {
  # Returns 0 if pane exists (any window/session), 1 if dead.
  local pane_id=$1
  tmux list-panes -a -F '#{pane_id}' 2>/dev/null | grep -qx "$pane_id"
}

pipeline_pane_alive_verified() {
  # Returns 0 only if pane exists AND runs a known agent command.
  # Prevents false positives after tmux server restart (pane ID reuse).
  # Usage: pipeline_pane_alive_verified <pane_id>
  local pane_id=$1
  if ! pipeline_pane_alive "$pane_id"; then
    return 1
  fi
  local actual_cmd
  actual_cmd=$(tmux display-message -t "$pane_id" -p '#{pane_current_command}' 2>/dev/null)
  case "$actual_cmd" in
    claude|codex) return 0 ;;
    *) return 1 ;;
  esac
}

pipeline_pane_snapshot() {
  # Outputs sorted list of all current tmux pane IDs.
  # Use before/after pane creation to detect orphans.
  tmux list-panes -a -F '#{pane_id}' 2>/dev/null | sort
}

pipeline_pane_orphan_cleanup() {
  # Kills panes that appeared between two snapshots (orphans from failed opens).
  # Usage: pipeline_pane_orphan_cleanup <before_file> <after_file>
  local before=$1
  local after=$2
  local orphans
  orphans=$(comm -13 "$before" "$after")
  local count=0
  for p in $orphans; do
    tmux kill-pane -t "$p" 2>/dev/null
    count=$((count + 1))
  done
  if [ "$count" -gt 0 ]; then
    >&2 echo "[pipeline] Cleaned up $count orphan pane(s): $orphans"
  fi
}

pipeline_kill_state_pane() {
  # Kills a pane recorded in state by field name.
  # Usage: pipeline_kill_state_pane <issue> <area> <field>
  local issue=$1
  local area=$2
  local field=$3
  if ! pipeline_state_exists "$issue" "$area"; then
    return
  fi
  local pane_id
  pane_id=$(pipeline_state_read "$issue" "$area" | jq -r ".${field} // empty")
  if [ -n "$pane_id" ]; then
    pipeline_kill_pane "$pane_id"
  fi
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

pipeline_open_pane_verified() {
  # Opens a side pane and verifies it survives startup (3-second grace period).
  # Single attempt only - no internal retry. On failure, captures dead pane output
  # for diagnosis via remain-on-exit, then cleans up.
  # stdout: pane_id on success, diagnostic token on failure
  # stderr: diagnosis info on failure (last 20 lines of dead pane output)
  # Returns: 0 = success, 2 = PANE_DEAD, 3 = PATH_INVALID
  local workdir=$1
  local prompt=$2
  local agent=${3:-claude}
  local target_pane=$4
  local issue=$5
  local area=$6

  # Phase 1: Validate path
  if [ ! -d "$workdir" ]; then
    if [ -n "$issue" ]; then
      workdir=$(pipeline_resolve_worktree_path "$issue" "$area")
      if [ $? -ne 0 ]; then
        echo "PATH_INVALID"
        return 3
      fi
    else
      echo "PATH_INVALID"
      return 3
    fi
  fi

  # Phase 2: Open pane with remain-on-exit for failure diagnosis
  local pane_id
  pane_id=$(pipeline_open_pane "$workdir" "$prompt" "$agent" "$target_pane")

  if [ -z "$pane_id" ]; then
    echo "PANE_DEAD"
    return 2
  fi

  # Enable remain-on-exit so dead panes stay visible for diagnosis
  tmux set-option -t "$pane_id" remain-on-exit on 2>/dev/null

  # Phase 3: Verify startup (3-second grace period)
  # With remain-on-exit on, dead panes still appear in list-panes.
  # Check #{pane_dead} flag instead of pane existence.
  sleep 3
  local is_dead
  is_dead=$(tmux display-message -t "$pane_id" -p '#{pane_dead}' 2>/dev/null)
  if [ "$is_dead" != "1" ]; then
    # Pane survived - disable remain-on-exit for normal operation
    tmux set-option -t "$pane_id" remain-on-exit off 2>/dev/null
    echo "$pane_id"
    return 0
  fi

  # Phase 4: Pane died - capture output for diagnosis, then clean up
  >&2 echo "[pipeline] Pane $pane_id died within 3s of startup"
  local diagnosis
  diagnosis=$(tmux capture-pane -t "$pane_id" -p 2>/dev/null | tail -20)
  tmux kill-pane -t "$pane_id" 2>/dev/null

  if [ -n "$diagnosis" ]; then
    >&2 echo "[pipeline] Last output from dead pane:"
    >&2 echo "$diagnosis"
  fi

  echo "PANE_DEAD"
  return 2
}

pipeline_open_pane_with_retry() {
  # State-based retry wrapper around pipeline_open_pane_verified.
  # Reads/increments retry count from state so retry limits survive across sessions.
  # Usage: pipeline_open_pane_with_retry <issue> <area> <field> <workdir> <prompt> <agent> <target_pane>
  # field: "reviewPane" or "resolvePane" (determines retry counter key)
  # stdout: pane_id on success, diagnostic token on failure
  # Returns: 0 = success, 2 = PANE_DEAD, 3 = PATH_INVALID, 5 = MAX_RETRIES
  local issue=$1
  local area=$2
  local field=$3
  local workdir=$4
  local prompt=$5
  local agent=$6
  local target_pane=$7

  # Read retry count and max from state (single read)
  local retry_key="${field}Retries"
  local state
  state=$(pipeline_state_read "$issue" "$area")
  local retries
  retries=$(echo "$state" | jq -r ".${retry_key} // 0")
  local max_retries
  max_retries=$(echo "$state" | jq -r ".maxPaneRetries // 2")

  if [ "$retries" -ge "$max_retries" ]; then
    >&2 echo "[pipeline] Max retries ($max_retries) reached for $field"
    echo "MAX_RETRIES"
    return 5
  fi

  # Increment retry count BEFORE attempting (crash-safe)
  pipeline_state_update "$issue" "$area" ".${retry_key} = $((retries + 1))"

  # Kill previous pane for this field if still alive
  pipeline_kill_state_pane "$issue" "$area" "$field"

  # Single attempt
  pipeline_open_pane_verified "$workdir" "$prompt" "$agent" "$target_pane" "$issue" "$area"
}

# ──────────────────────────────────────────────
# Polling (review & commits)
# ──────────────────────────────────────────────

pipeline_poll_review() {
  # Polls for a new /dev-review submission (body starts with "## Review Summary")
  # that has an ID greater than last_review_id.
  # Returns: 0 = found, 1 = timeout, 2 = pane died
  local area_dir=$1
  local pr=$2
  local last_review_id=${3:-0}
  local max_wait=${4:-900}
  local review_pane_id=$5
  local interval=30
  local elapsed=0

  while true; do
    local review_id
    review_id=$(cd "$area_dir" && gh api "repos/{owner}/{repo}/pulls/${pr}/reviews" \
      --jq "[.[] | select(.id > ${last_review_id})
                 | select(.body | startswith(\"## Review Summary\"))]
            | last // empty | .id")

    if [ -n "$review_id" ] && [ "$review_id" != "null" ]; then
      echo "$review_id"
      return 0
    fi

    if [ -n "$review_pane_id" ] && ! pipeline_pane_alive "$review_pane_id"; then
      review_id=$(cd "$area_dir" && gh api "repos/{owner}/{repo}/pulls/${pr}/reviews" \
        --jq "[.[] | select(.id > ${last_review_id})
                   | select(.body | startswith(\"## Review Summary\"))]
              | last // empty | .id")
      if [ -n "$review_id" ] && [ "$review_id" != "null" ]; then
        echo "$review_id"
        return 0
      fi
      echo "PANE_DEAD"
      return 2
    fi

    elapsed=$((elapsed + interval))
    if [ "$elapsed" -gt "$max_wait" ]; then
      echo "TIMEOUT"
      return 1
    fi
    sleep "$interval"
  done
}

pipeline_fetch_review() {
  local area_dir=$1
  local pr=$2
  local review_id=$3
  cd "$area_dir" && gh api "repos/{owner}/{repo}/pulls/${pr}/reviews/${review_id}" \
    --jq '{state: .state, body: .body}'
}

pipeline_poll_commits() {
  # Polls for new commits on a PR after a known commit SHA.
  # Returns: 0 = new commit, 1 = timeout, 2 = pane died
  local area_dir=$1
  local pr=$2
  local last_commit_sha=$3
  local max_wait=${4:-900}
  local resolve_pane_id=$5
  local interval=30
  local elapsed=0

  while true; do
    local latest_sha
    latest_sha=$(cd "$area_dir" && gh api "repos/{owner}/{repo}/pulls/${pr}/commits" \
      --jq '.[-1].sha')

    if [ -n "$latest_sha" ] && [ "$latest_sha" != "null" ] && [ "$latest_sha" != "$last_commit_sha" ]; then
      echo "$latest_sha"
      return 0
    fi

    if [ -n "$resolve_pane_id" ] && ! pipeline_pane_alive "$resolve_pane_id"; then
      latest_sha=$(cd "$area_dir" && gh api "repos/{owner}/{repo}/pulls/${pr}/commits" \
        --jq '.[-1].sha')
      if [ -n "$latest_sha" ] && [ "$latest_sha" != "null" ] && [ "$latest_sha" != "$last_commit_sha" ]; then
        echo "$latest_sha"
        return 0
      fi
      echo "PANE_DEAD"
      return 2
    fi

    elapsed=$((elapsed + interval))
    if [ "$elapsed" -gt "$max_wait" ]; then
      echo "TIMEOUT"
      return 1
    fi
    sleep "$interval"
  done
}

# ──────────────────────────────────────────────
# Pre-checks (recovery: detect work completed by previous session)
# ──────────────────────────────────────────────

pipeline_check_review_exists() {
  # Check if a review already exists (from a previous session's pane that completed).
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

pipeline_check_new_commits() {
  # Check if new commits exist (from a previous session's resolve that completed).
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
# Cleanup
# ──────────────────────────────────────────────

pipeline_cleanup() {
  local issue=$1
  local area=$2
  local branch=$3
  local review_pane=$4
  local resolve_pane=$5

  pipeline_kill_pane "$review_pane"
  pipeline_kill_pane "$resolve_pane"

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
