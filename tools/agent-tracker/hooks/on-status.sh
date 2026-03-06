#!/usr/bin/env bash
# tools/agent-tracker/hooks/on-status.sh
# Handles UserPromptSubmit / Stop / PreToolUse / PostToolUse / SessionEnd hooks.
# Updates status, task, and activity fields in the agent-tracker sidecar file.
#
# Status transitions:
#   UserPromptSubmit → working (+ captures task from prompt, clears activity)
#                      /clear → resets sidecar to idle (#32)
#   Stop             → idle (adds "(Done) " prefix to task if set, clears activity) (#32)
#   PreToolUse       → activity: "{ToolName}: {key_arg}"
#                      + needs-input (AskUserQuestion only)
#   PostToolUse      → clears activity, restores needs-input → working (#47)
#   SessionEnd       → deletes sidecar file for this pane (#32)
#
# Uses flock to prevent race conditions with on-statusline.sh.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
SIDECAR_DIR="$REPO_ROOT/.workspace/agent-tracker"

# Determine pane identifier
# PPID fallback: stable across hook invocations (same Claude Code parent). (#47)
pane_id="${TMUX_PANE:-pid-$PPID}"
pane_file="${pane_id#%}"

# Read hook JSON from stdin
input=$(cat)
[[ -z "$input" ]] && exit 0

# Determine event type
event=$(printf '%s' "$input" | jq -r '.hook_event_name // empty')
[[ -z "$event" ]] && exit 0

sidecar_path="${SIDECAR_DIR}/${pane_file}.json"
lock_path="${sidecar_path}.lock"

# ── SessionEnd: delete sidecar file immediately, no lock needed (#32) ────────
if [[ "$event" == "SessionEnd" ]]; then
  rm -f "$sidecar_path" "$lock_path"
  exit 0
fi

mkdir -p "$SIDECAR_DIR"

# ── Prepare update fields from input (outside lock to minimize lock time) ──

jq_args=()
jq_expr=""

case "$event" in
  UserPromptSubmit)
    task=$(printf '%s' "$input" | jq -r '
      .prompt // "" |
      gsub("\n"; " ") | gsub("  +"; " ") |
      gsub("[[:cntrl:]]"; "") |
      ltrimstr(" ") | rtrimstr(" ") |
      if length > 200 then .[:200] + "..." else . end
    ')
    # /clear resets sidecar to initial state (#32)
    if [[ "$task" == "/clear" ]]; then
      jq_args=(--arg pane_id "$pane_id")
      jq_expr='. + {status: "idle", task: "—", activity: null, pane_id: $pane_id, updated_at: now}'
    else
      jq_args=(--arg status "working" --arg task "$task" --arg pane_id "$pane_id")
      jq_expr='. + {status: $status, task: $task, activity: null, pane_id: $pane_id, updated_at: now}'
    fi
    ;;
  Stop)
    # Add "(Done) " prefix to task when a task was active (#32)
    jq_args=(--arg pane_id "$pane_id")
    jq_expr='
      . + {status: "idle", activity: null, pane_id: $pane_id, updated_at: now} |
      if (.task != null and .task != "—" and (.task | startswith("(Done) ") | not))
      then .task = "(Done) " + .task
      else . end
    '
    ;;
  PreToolUse)
    tool_name=$(printf '%s' "$input" | jq -r '.tool_name // empty')
    if [[ -n "$tool_name" ]]; then
      key_arg=$(printf '%s' "$input" | jq -r --arg tn "$tool_name" '
        (.tool_input // {}) | if type != "object" then {} else . end |
        if   $tn == "Bash"         then .description // .command // ""
        elif $tn == "Read"         then (.file_path // "" | split("/") | last)
        elif $tn == "Edit"         then (.file_path // "" | split("/") | last)
        elif $tn == "Write"        then (.file_path // "" | split("/") | last)
        elif $tn == "Grep"         then .pattern // ""
        elif $tn == "Glob"         then .pattern // ""
        elif $tn == "Agent"        then .description // ""
        elif $tn == "Skill"        then ((.skill // "") + (if .args == null then "" else " " + (.args | tostring) end))
        elif $tn == "WebSearch"    then .query // ""
        elif $tn == "WebFetch"     then .url // ""
        elif $tn == "NotebookEdit" then (.notebook_path // "" | split("/") | last)
        elif $tn == "TaskCreate"   then .subject // ""
        elif $tn == "TaskUpdate"   then .taskId // ""
        else ""
        end |
        tostring |
        gsub("\n"; " ") | gsub("  +"; " ") |
        gsub("[[:cntrl:]]"; "") |
        ltrimstr(" ") | rtrimstr(" ")
      ')
      if [[ -n "$key_arg" ]]; then
        activity="${tool_name}: ${key_arg}"
      else
        activity="${tool_name}"
      fi
    else
      activity=""
    fi

    if [[ "$tool_name" == "AskUserQuestion" ]]; then
      jq_args=(--arg activity "$activity" --arg pane_id "$pane_id")
      jq_expr='. + {status: "needs-input", activity: $activity, pane_id: $pane_id, updated_at: now}'
    else
      jq_args=(--arg activity "$activity" --arg pane_id "$pane_id")
      jq_expr='. + {activity: $activity, pane_id: $pane_id, updated_at: now}'
    fi
    ;;
  PostToolUse)
    # Reset needs-input → working when AskUserQuestion completes (#47)
    jq_args=(--arg pane_id "$pane_id")
    jq_expr='
      . + {activity: null, pane_id: $pane_id, updated_at: now} |
      if .status == "needs-input" then .status = "working" else . end
    '
    ;;
  *)
    exit 0
    ;;
esac

# ── Locked read-modify-write ──────────────────────────────────────────────

(
  flock -w 1 9 || exit 0

  existing="{}"
  [[ -f "$sidecar_path" ]] && existing=$(cat "$sidecar_path" 2>/dev/null || echo "{}")

  updated=$(printf '%s' "$existing" | jq "${jq_args[@]}" "$jq_expr")

  tmp="${sidecar_path}.tmp.$$"
  printf '%s\n' "$updated" > "$tmp"
  mv -f "$tmp" "$sidecar_path"
) 9>"$lock_path"

exit 0
