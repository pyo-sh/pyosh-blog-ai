#!/usr/bin/env bash
# tools/agent-tracker/statusline-wrapper.sh
# Thin wrapper around context-bar.sh that also writes agent-tracker sidecar.
#
# Replaces the statusLine command in ~/.claude/settings.json:
#   "statusLine": { "type": "command", "command": ".../statusline-wrapper.sh" }
#
# Flow:
#   stdin (JSON) → tee → on-statusline.sh (background, fire-and-forget)
#                      → context-bar.sh    (foreground, stdout for display)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Read stdin once
input=$(cat)

# Write sidecar in background (fire-and-forget, never block display)
printf '%s' "$input" | "$SCRIPT_DIR/hooks/on-statusline.sh" &>/dev/null &

# Pass to context-bar.sh for status line display
# Resolve context-bar.sh relative to repo root
CONTEXT_BAR="${SCRIPT_DIR}/../../scripts/context-bar.sh"
if [[ -x "$CONTEXT_BAR" ]]; then
  printf '%s' "$input" | "$CONTEXT_BAR"
else
  # Fallback: minimal display
  model=$(printf '%s' "$input" | jq -r '.model.display_name // .model.id // "?"' 2>/dev/null)
  printf '%s' "$model"
fi
