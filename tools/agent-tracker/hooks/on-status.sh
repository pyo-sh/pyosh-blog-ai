#!/usr/bin/env bash
# tools/agent-tracker/hooks/on-status.sh
# Handles UserPromptSubmit / Stop / PreToolUse / PostToolUse hooks.
# Updates status, task, and activity fields in the agent-tracker sidecar file.
#
# Status transitions:
#   UserPromptSubmit → working (+ captures task from prompt, clears activity)
#   Stop             → idle (clears activity)
#   PreToolUse       → activity: "{ToolName}: {key_arg}"
#                      + needs-input (AskUserQuestion only)
#   PostToolUse      → clears activity

set -euo pipefail

SIDECAR_DIR="/tmp/agent-tracker"

# Determine pane identifier
pane_id="${TMUX_PANE:-pid-$$}"
pane_file="${pane_id#%}"

# Read hook JSON from stdin
input=$(cat)
[[ -z "$input" ]] && exit 0

# Determine event type
event=$(printf '%s' "$input" | jq -r '.hook_event_name // empty')
[[ -z "$event" ]] && exit 0

# Ensure sidecar directory exists
mkdir -p "$SIDECAR_DIR"

sidecar_path="${SIDECAR_DIR}/${pane_file}.json"

# Read existing sidecar (may not exist yet if on-statusline hasn't run)
existing="{}"
[[ -f "$sidecar_path" ]] && existing=$(cat "$sidecar_path" 2>/dev/null || echo "{}")

case "$event" in
  UserPromptSubmit)
    # Extract user prompt as task, truncate to 200 chars; clear activity
    task=$(printf '%s' "$input" | jq -r '
      .prompt // "" |
      gsub("\n"; " ") | gsub("  +"; " ") |
      ltrimstr(" ") | rtrimstr(" ") |
      if length > 200 then .[:200] + "..." else . end
    ')
    updated=$(printf '%s' "$existing" | jq \
      --arg status "working" \
      --arg task "$task" \
      --arg pane_id "$pane_id" \
      '. + {status: $status, task: $task, activity: null, pane_id: $pane_id, updated_at: now}')
    ;;
  Stop)
    updated=$(printf '%s' "$existing" | jq \
      --arg pane_id "$pane_id" \
      '. + {status: "idle", activity: null, pane_id: $pane_id, updated_at: now}')
    ;;
  PreToolUse)
    # Build activity string: "{ToolName}: {key_arg}"
    tool_name=$(printf '%s' "$input" | jq -r '.tool_name // empty')
    if [[ -n "$tool_name" ]]; then
      key_arg=$(printf '%s' "$input" | jq -r --arg tn "$tool_name" '
        .tool_input // {} |
        if   $tn == "Bash"         then .description // .command // ""
        elif $tn == "Read"         then (.file_path // "" | split("/") | last)
        elif $tn == "Edit"         then (.file_path // "" | split("/") | last)
        elif $tn == "Write"        then (.file_path // "" | split("/") | last)
        elif $tn == "Grep"         then .pattern // ""
        elif $tn == "Glob"         then .pattern // ""
        elif $tn == "Agent"        then .description // ""
        elif $tn == "Skill"        then ((.skill // "") + (if .args then " " + .args else "" end))
        elif $tn == "WebSearch"    then .query // ""
        elif $tn == "WebFetch"     then .url // ""
        elif $tn == "NotebookEdit" then (.notebook_path // "" | split("/") | last)
        elif $tn == "TaskCreate"   then .subject // ""
        elif $tn == "TaskUpdate"   then .taskId // ""
        else ""
        end |
        gsub("\n"; " ") | gsub("  +"; " ") |
        ltrimstr(" ") | rtrimstr(" ")
      ')
      activity="${tool_name}: ${key_arg}"
    else
      activity=""
    fi

    # AskUserQuestion → also set needs-input status
    if [[ "$tool_name" == "AskUserQuestion" ]]; then
      updated=$(printf '%s' "$existing" | jq \
        --arg activity "$activity" \
        --arg pane_id "$pane_id" \
        '. + {status: "needs-input", activity: $activity, pane_id: $pane_id, updated_at: now}')
    else
      updated=$(printf '%s' "$existing" | jq \
        --arg activity "$activity" \
        --arg pane_id "$pane_id" \
        '. + {activity: $activity, pane_id: $pane_id, updated_at: now}')
    fi
    ;;
  PostToolUse)
    # Clear activity after tool completes
    updated=$(printf '%s' "$existing" | jq \
      --arg pane_id "$pane_id" \
      '. + {activity: null, pane_id: $pane_id, updated_at: now}')
    ;;
  *)
    exit 0
    ;;
esac

# Atomic write
if [[ -n "${updated:-}" ]]; then
  tmp="${sidecar_path}.tmp.$$"
  printf '%s\n' "$updated" > "$tmp"
  mv -f "$tmp" "$sidecar_path"
fi

exit 0
