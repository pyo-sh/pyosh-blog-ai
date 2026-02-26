#!/bin/bash
# pipeline-helpers.sh — Shell helpers for dev-pipeline skill
# Source this file or use functions individually via the AI's Bash tool.

WORKSPACE_ROOT="$(git rev-parse --show-toplevel)"
PIPELINE_DIR="$WORKSPACE_ROOT/.workspace/pipeline"
WORKTREE_DIR="$WORKSPACE_ROOT/.workspace/worktrees"

# ──────────────────────────────────────────────
# State management
# ──────────────────────────────────────────────

pipeline_state_path() {
  local issue=$1
  echo "$PIPELINE_DIR/issue-${issue}.state.json"
}

pipeline_init() {
  mkdir -p "$PIPELINE_DIR" "$WORKTREE_DIR"
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

pipeline_open_pane() {
  # Usage: pipeline_open_pane <working_dir> <prompt> [agent]
  # agent: "claude" (default) or "codex"
  local workdir=$1
  local prompt=$2
  local agent=${3:-claude}

  local cmd
  if [ "$agent" = "codex" ]; then
    cmd="codex --full-auto '$prompt'"
  else
    cmd="claude --dangerously-skip-permissions '$prompt'"
  fi

  tmux split-window -h -P -F '#{pane_id}' \
    "cd '$workdir' && $cmd"
}

pipeline_kill_pane() {
  local pane_id=$1
  if [ -n "$pane_id" ]; then
    tmux kill-pane -t "$pane_id" 2>/dev/null
  fi
}

pipeline_pane_alive() {
  local pane_id=$1
  tmux list-panes -F '#{pane_id}' 2>/dev/null | grep -q "$pane_id"
}

# ──────────────────────────────────────────────
# Review polling
# ──────────────────────────────────────────────

pipeline_poll_review() {
  # Usage: pipeline_poll_review <area_dir> <pr_number> [max_wait_seconds]
  local area_dir=$1
  local pr=$2
  local max_wait=${3:-900}  # default 15 minutes
  local interval=30
  local elapsed=0

  while [ "$elapsed" -lt "$max_wait" ]; do
    local state
    state=$(cd "$area_dir" && gh api "repos/{owner}/{repo}/pulls/${pr}/reviews" --jq '.[-1].state' 2>/dev/null)
    if [ -n "$state" ] && [ "$state" != "null" ]; then
      echo "$state"
      return 0
    fi
    sleep "$interval"
    elapsed=$((elapsed + interval))
  done

  echo "TIMEOUT"
  return 1
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

  # Remove worktree
  local wt="$WORKTREE_DIR/issue-${issue}"
  if [ -d "$wt" ]; then
    cd "$WORKSPACE_ROOT" && git worktree remove "$wt" 2>/dev/null
  fi

  # Delete branch (may already be deleted by --delete-branch)
  git branch -d "$branch" 2>/dev/null

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
