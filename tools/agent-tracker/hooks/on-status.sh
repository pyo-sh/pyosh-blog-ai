#!/usr/bin/env bash
# tools/agent-tracker/hooks/on-status.sh
# Handles UserPromptSubmit / Stop / PreToolUse(AskUserQuestion) hooks.
# Updates status and task fields in the agent-tracker sidecar file.
#
# Status transitions:
#   UserPromptSubmit → working (+ captures task from prompt)
#   Stop             → idle
#   PreToolUse       → needs-input (only for AskUserQuestion, via matcher)

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
    # Extract user prompt as task, truncate to 200 chars
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
      '. + {status: $status, task: $task, pane_id: $pane_id, updated_at: now}')
    ;;
  Stop)
    updated=$(printf '%s' "$existing" | jq \
      --arg pane_id "$pane_id" \
      '. + {status: "idle", pane_id: $pane_id, updated_at: now}')
    ;;
  PreToolUse)
    # Only AskUserQuestion triggers needs-input (matcher handles filtering)
    updated=$(printf '%s' "$existing" | jq \
      --arg pane_id "$pane_id" \
      '. + {status: "needs-input", pane_id: $pane_id, updated_at: now}')
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
