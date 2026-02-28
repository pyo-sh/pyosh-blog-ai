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
  local pane_id=$1
  tmux list-panes -F '#{pane_id}' 2>/dev/null | grep -q "$pane_id"
}

# ──────────────────────────────────────────────
# Review polling
# ──────────────────────────────────────────────

pipeline_poll_review() {
  # Usage: pipeline_poll_review <area_dir> <pr> <last_review_id> [max_wait]
  # Polls for a new /dev-review submission (body starts with "## Review Summary")
  # that has an ID greater than last_review_id.
  # Output: review ID on success, "TIMEOUT" on failure.
  local area_dir=$1
  local pr=$2
  local last_review_id=${3:-0}
  local max_wait=${4:-900}  # default 15 minutes
  local interval=30
  local elapsed=0

  while true; do
    local review_id
    review_id=$(cd "$area_dir" && gh api "repos/{owner}/{repo}/pulls/${pr}/reviews" \
      --jq "[.[] | select(.id > ${last_review_id})
                 | select(.body | startswith(\"## Review Summary\"))]
            | last // empty | .id" 2>/dev/null)

    if [ -n "$review_id" ] && [ "$review_id" != "null" ]; then
      echo "$review_id"
      return 0
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
