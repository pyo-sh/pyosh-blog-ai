#!/bin/bash
# pipeline-helpers.sh — Shell helpers for dev-pipeline skill
# Source this file or use functions individually via the AI's Bash tool.

# Detect monorepo root via git worktree list — always returns the main worktree path,
# regardless of whether this script is sourced from a linked worktree or an area repo.
MONOREPO_ROOT="$(git worktree list --porcelain | awk 'NR==1{print $2}')"
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
  local issue=$1
  local area=$2
  local json=$3
  echo "$json" > "$(pipeline_state_path "$issue" "$area")"
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
  # Capture the current pane ID — prefer $TMUX_PANE (process's own pane,
  # not the focused pane, which differs on --continue sessions).
  # Fall back to tmux display-message for atypical invocation contexts where
  # $TMUX_PANE is unset (e.g. sourced from a non-tmux shell inside a tmux session).
  if [ -n "$TMUX_PANE" ]; then
    echo "$TMUX_PANE"
  else
    tmux display-message -p '#{pane_id}' 2>/dev/null
  fi
}

pipeline_open_pane() {
  # Usage: pipeline_open_pane <working_dir> <prompt> [agent] [target_pane]
  # agent: "claude" (default) or "codex"
  # target_pane: pane ID to split from (avoids splitting user's active pane)
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
  # Usage: pipeline_pane_alive <pane_id>
  # Returns 0 if pane exists (any window/session), 1 if dead.
  local pane_id=$1
  tmux list-panes -a -F '#{pane_id}' 2>/dev/null | grep -qx "$pane_id"
}

pipeline_resolve_worktree_path() {
  # Usage: pipeline_resolve_worktree_path <issue> [area]
  # Resolves actual worktree directory, checking current path first, then legacy.
  # stdout: absolute path on success, "PATH_INVALID" on failure
  # Returns: 0 = found, 3 = not found
  local issue=$1
  local area=$2

  # Current path: $MONOREPO_ROOT/.workspace/worktrees/issue-{N}
  local current_path="$WORKTREE_DIR/issue-${issue}"
  if [ -d "$current_path" ]; then
    echo "$current_path"
    return 0
  fi

  # Legacy path: $MONOREPO_ROOT/{area}/.workspace/worktrees/issue-{N}
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
  # Usage: pipeline_open_pane_verified <working_dir> <prompt> [agent] [target_pane] [issue] [area]
  # Opens a side pane and verifies it survives startup (3-second grace period).
  # On failure, retries once with re-resolved worktree path (if issue/area provided).
  # stdout: pane_id on success, diagnostic token on failure
  # Returns: 0 = success, 2 = PANE_DEAD, 3 = PATH_INVALID, 4 = RETRY_FAILED
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

  # Phase 2: Open pane
  local pane_id
  pane_id=$(pipeline_open_pane "$workdir" "$prompt" "$agent" "$target_pane")

  if [ -z "$pane_id" ]; then
    echo "PANE_DEAD"
    return 2
  fi

  # Phase 3: Verify startup (3-second grace period)
  sleep 3
  if pipeline_pane_alive "$pane_id"; then
    echo "$pane_id"
    return 0
  fi

  # Pane died — attempt one retry with re-resolved path
  >&2 echo "[pipeline] Pane $pane_id died within 3s of startup"

  if [ -n "$issue" ]; then
    local resolved_path
    resolved_path=$(pipeline_resolve_worktree_path "$issue" "$area")
    if [ $? -ne 0 ]; then
      echo "PATH_INVALID"
      return 3
    fi

    >&2 echo "[pipeline] Retrying with resolved path: $resolved_path"
    pane_id=$(pipeline_open_pane "$resolved_path" "$prompt" "$agent" "$target_pane")

    if [ -z "$pane_id" ]; then
      echo "RETRY_FAILED"
      return 4
    fi

    sleep 3
    if pipeline_pane_alive "$pane_id"; then
      echo "$pane_id"
      return 0
    fi

    >&2 echo "[pipeline] Retry pane $pane_id also died"
    echo "RETRY_FAILED"
    return 4
  fi

  echo "PANE_DEAD"
  return 2
}

# ──────────────────────────────────────────────
# Polling (review & commits)
# ──────────────────────────────────────────────

pipeline_poll_review() {
  # Usage: pipeline_poll_review <area_dir> <pr> <last_review_id> [max_wait] [review_pane_id]
  # Polls for a new /dev-review submission (body starts with "## Review Summary")
  # that has an ID greater than last_review_id.
  # Output: review ID on success, "TIMEOUT" on timeout, "PANE_DEAD" on pane death.
  # Returns: 0 = found, 1 = timeout, 2 = pane died
  local area_dir=$1
  local pr=$2
  local last_review_id=${3:-0}
  local max_wait=${4:-900}  # default 15 minutes
  local review_pane_id=$5   # optional: pane to monitor
  local interval=30
  local elapsed=0

  while true; do
    # 1. Check API first — pane may have exited normally after posting review
    local review_id
    review_id=$(cd "$area_dir" && gh api "repos/{owner}/{repo}/pulls/${pr}/reviews" \
      --jq "[.[] | select(.id > ${last_review_id})
                 | select(.body | startswith(\"## Review Summary\"))]
            | last // empty | .id")

    if [ -n "$review_id" ] && [ "$review_id" != "null" ]; then
      echo "$review_id"
      return 0
    fi

    # 2. Then check pane health (only if no review found)
    if [ -n "$review_pane_id" ] && ! pipeline_pane_alive "$review_pane_id"; then
      # Final API check — review might have been posted just before pane died
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
  # Usage: pipeline_fetch_review <area_dir> <pr> <review_id>
  # Fetches a specific review by ID and outputs raw JSON (state + body).
  # The AI reads STATE and severity counts directly from the output.
  local area_dir=$1
  local pr=$2
  local review_id=$3

  cd "$area_dir" && gh api "repos/{owner}/{repo}/pulls/${pr}/reviews/${review_id}" \
    --jq '{state: .state, body: .body}'
}

pipeline_poll_commits() {
  # Usage: pipeline_poll_commits <area_dir> <pr> <last_commit_sha> [max_wait] [resolve_pane_id]
  # Polls for new commits on a PR after a known commit SHA.
  # Output: new SHA on success, "TIMEOUT" on timeout, "PANE_DEAD" on pane death.
  # Returns: 0 = new commit, 1 = timeout, 2 = pane died
  local area_dir=$1
  local pr=$2
  local last_commit_sha=$3
  local max_wait=${4:-900}
  local resolve_pane_id=$5
  local interval=30
  local elapsed=0

  while true; do
    # 1. Check for new commits first
    local latest_sha
    latest_sha=$(cd "$area_dir" && gh api "repos/{owner}/{repo}/pulls/${pr}/commits" \
      --jq '.[-1].sha')

    if [ -n "$latest_sha" ] && [ "$latest_sha" != "null" ] && [ "$latest_sha" != "$last_commit_sha" ]; then
      echo "$latest_sha"
      return 0
    fi

    # 2. Then check pane health
    if [ -n "$resolve_pane_id" ] && ! pipeline_pane_alive "$resolve_pane_id"; then
      # Final commit check
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
# Cleanup
# ──────────────────────────────────────────────

pipeline_cleanup() {
  # Usage: pipeline_cleanup <issue> <area> <branch> <review_pane> <resolve_pane>
  local issue=$1
  local area=$2
  local branch=$3
  local review_pane=$4
  local resolve_pane=$5

  # Kill panes
  pipeline_kill_pane "$review_pane"
  pipeline_kill_pane "$resolve_pane"

  # Remove worktree (--force handles uncommitted changes or detached HEAD post-merge)
  local wt="$WORKTREE_DIR/issue-${issue}"
  if [ -d "$wt" ]; then
    cd "$MONOREPO_ROOT/$area" && git worktree remove "$wt" --force
    git worktree prune
  fi

  # Delete branch (-D required after squash merge; branch commits not in main ancestry)
  cd "$MONOREPO_ROOT/$area" && git branch -D "$branch" 2>/dev/null

  # Remove state file
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
