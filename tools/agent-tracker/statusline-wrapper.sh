#!/usr/bin/env bash
# tools/agent-tracker/statusline-wrapper.sh
# Thin wrapper around context-bar.sh that also writes agent-tracker sidecar.
#
# Replaces the statusLine command in ~/.claude/settings.json:
#   "statusLine": { "type": "command", "command": ".../statusline-wrapper.sh" }
#
# Flow:
#   stdin (JSON) → transcript token calc (once)
#               → on-statusline.sh (background, fire-and-forget)
#               → context-bar.sh   (foreground, stdout for display)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Read stdin once
input=$(cat)

# Pre-compute tokens from transcript once, shared by both downstream scripts.
# total_input_tokens excludes system prompt/tools/memory — transcript is accurate.
# See: github.com/anthropics/claude-code/issues/13652
_tp=$(printf '%s' "$input" | jq -r '.transcript_path // empty' 2>/dev/null)
export TRANSCRIPT_TOKENS=0
if [[ -n "$_tp" && -f "$_tp" ]]; then
  TRANSCRIPT_TOKENS=$(jq -s '
    map(select(.message.usage and .isSidechain != true and .isApiErrorMessage != true)) |
    last |
    if . then
      (.message.usage.input_tokens // 0) +
      (.message.usage.cache_read_input_tokens // 0) +
      (.message.usage.cache_creation_input_tokens // 0)
    else 0 end
  ' < "$_tp" 2>/dev/null || echo 0)
  export TRANSCRIPT_TOKENS
fi

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
