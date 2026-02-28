#!/bin/bash
# pipeline-helpers.sh — Shell helpers for dev-pipeline skill
# Source this file or use functions individually via the AI's Bash tool.

# Detect monorepo root — if inside area repo (server/client), go up one level
_GIT_ROOT="$(git rev-parse --show-toplevel)"
if [ -d "$_GIT_ROOT/../server" ] && [ -f "$_GIT_ROOT/../CLAUDE.md" ]; then
  MONOREPO_ROOT="$(cd "$_GIT_ROOT/.." && pwd)"
else
  MONOREPO_ROOT="$_GIT_ROOT"
fi
PIPELINE_DIR="$MONOREPO_ROOT/.workspace/pipeline"
WORKTREE_DIR="$MONOREPO_ROOT/.workspace/worktrees"

# ──────────────────────────────────────────────
# State management
# ──────────────────────────────────────────────

pipeline_state_path() {
  local issue=$1
  echo "$PIPELINE_DIR/issue-${issue}.state.json"
}

pipeline_init() {
  mkdir -p "$PIPELINE_DIR" "$WORKTREE_DIR"
  # Ensure area's .gitignore doesn't need updating — worktrees live at monorepo root
}

pipeline_state_exists() {
  local issue=$1
  [ -f "$(pipeline_state_path "$issue")" ]
}

pipeline_state_read() {
  local issue=$1
  cat "$(pipeline_state_path "$issue")"
}

pipeline_state_delete() {
  local issue=$1
  rm -f "$(pipeline_state_path "$issue")"
}

# ──────────────────────────────────────────────
# tmux pane management
# ──────────────────────────────────────────────

pipeline_orchestrator_pane() {
  # Capture the current pane ID — call at pipeline start to anchor splits
  tmux display-message -p '#{pane_id}'
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
    tmux split-window -h -t "$target_pane" -P -F '#{pane_id}' \
      "cd '$workdir' && $cmd"
  else
    tmux split-window -h -P -F '#{pane_id}' \
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
            | last // empty | .id" 2>/dev/null)

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
              | last // empty | .id" 2>/dev/null)
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

pipeline_analyze_review() {
  # Usage: pipeline_analyze_review <area_dir> <pr> <review_id>
  # Fetches a specific review by ID and parses severity counts from body table.
  # Output (eval-friendly):
  #   STATE=COMMENTED|CHANGES_REQUESTED|APPROVED
  #   CRITICAL=N
  #   WARNING=N
  #   SUGGESTION=N
  local area_dir=$1
  local pr=$2
  local review_id=$3

  local review_json
  review_json=$(cd "$area_dir" && gh api "repos/{owner}/{repo}/pulls/${pr}/reviews/${review_id}" 2>/dev/null)

  local state body
  state=$(echo "$review_json" | jq -r '.state')
  body=$(echo "$review_json" | jq -r '.body')

  local critical warning suggestion
  critical=$(echo "$body" | awk -F'|' '/\[CRITICAL\]/{gsub(/ /,"",$3); print $3}')
  warning=$(echo "$body" | awk -F'|' '/\[WARNING\]/{gsub(/ /,"",$3); print $3}')
  suggestion=$(echo "$body" | awk -F'|' '/\[SUGGESTION\]/{gsub(/ /,"",$3); print $3}')

  echo "STATE=${state}"
  echo "CRITICAL=${critical:-0}"
  echo "WARNING=${warning:-0}"
  echo "SUGGESTION=${suggestion:-0}"
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
      --jq '.[-1].sha' 2>/dev/null)

    if [ -n "$latest_sha" ] && [ "$latest_sha" != "null" ] && [ "$latest_sha" != "$last_commit_sha" ]; then
      echo "$latest_sha"
      return 0
    fi

    # 2. Then check pane health
    if [ -n "$resolve_pane_id" ] && ! pipeline_pane_alive "$resolve_pane_id"; then
      # Final commit check
      latest_sha=$(cd "$area_dir" && gh api "repos/{owner}/{repo}/pulls/${pr}/commits" \
        --jq '.[-1].sha' 2>/dev/null)
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

  # Remove worktree (must run from the area repo that owns it)
  local wt="$WORKTREE_DIR/issue-${issue}"
  if [ -d "$wt" ]; then
    cd "$MONOREPO_ROOT/$area" && git worktree remove "$wt" 2>/dev/null
  fi

  # Delete branch (may already be deleted by --delete-branch)
  cd "$MONOREPO_ROOT/$area" && git branch -d "$branch" 2>/dev/null

  # Remove state file
  pipeline_state_delete "$issue"
}

# ──────────────────────────────────────────────
# Listing active pipelines
# ──────────────────────────────────────────────

pipeline_list() {
  if [ -d "$PIPELINE_DIR" ]; then
    for f in "$PIPELINE_DIR"/issue-*.state.json; do
      [ -f "$f" ] || continue
      local issue step
      issue=$(jq -r '.issue' "$f")
      step=$(jq -r '.step' "$f")
      echo "Issue #${issue}: step=${step}"
    done
  else
    echo "No active pipelines"
  fi
}
