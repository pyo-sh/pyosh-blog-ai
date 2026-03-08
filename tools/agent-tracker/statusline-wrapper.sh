#!/usr/bin/env bash
# tools/agent-tracker/statusline-wrapper.sh
# Thin wrapper around context-bar.sh that also writes agent-tracker sidecar.
#
# Replaces the statusLine command in ~/.claude/settings.json:
#   "statusLine": { "type": "command", "command": ".../statusline-wrapper.sh" }
#
# Flow:
#   stdin (JSON) → current_usage token calc + transcript last msg
#               → on-statusline.sh (background, fire-and-forget)
#               → context-bar.sh   (foreground, stdout for display)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Read stdin once
input=$(cat)

# Stable pane identifier for on-statusline.sh (which runs as a child of this
# wrapper, so its own $PPID points here — unstable). Export our PPID (= Claude
# Code PID) so on-statusline.sh can use the same ID as on-status.sh. (#47)
export AGENT_TRACKER_PANE="${TMUX_PANE:-pid-$PPID}"

# Pre-compute tokens from current_usage for context-bar.sh compatibility.
# context-bar.sh has its own fallback when this env var is missing.
# SYNC:token-calc-fallback — keep in sync with context-bar.sh fallback
TRANSCRIPT_TOKENS=$(printf '%s' "$input" | jq -r '
  .context_window |
  if .current_usage != null then
    ((.current_usage.input_tokens // 0) +
     (.current_usage.cache_creation_input_tokens // 0) +
     (.current_usage.cache_read_input_tokens // 0))
  elif (.used_percentage // 0) > 0 then
    ((.context_window_size // 200000) * (.used_percentage // 0) / 100 | floor)
  else 0 end
' 2>/dev/null)
export TRANSCRIPT_TOKENS="${TRANSCRIPT_TOKENS:-0}"

# Pre-compute last user message from transcript.
# SYNC:last-user-msg — keep in sync with context-bar.sh fallback
_tp=$(printf '%s' "$input" | jq -r '.transcript_path // empty' 2>/dev/null)
export TRANSCRIPT_LAST_MSG=""
if [[ -n "$_tp" && -f "$_tp" ]]; then
  TRANSCRIPT_LAST_MSG=$(tail -n 200 "$_tp" | jq -rs '
    def is_unhelpful:
      startswith("[Request interrupted") or
      startswith("[Request cancelled") or
      . == "";
    [.[] | select(.type == "user") |
     select(.message.content | type == "string" or
            (type == "array" and any(.[]; .type == "text")))] |
    reverse |
    map(.message.content |
      if type == "string" then .
      else [.[] | select(.type == "text") | .text] | join(" ") end |
      gsub("\n"; " ") | gsub("  +"; " ")) |
    map(select(is_unhelpful | not)) |
    first // ""
  ' 2>/dev/null || echo "")
  export TRANSCRIPT_LAST_MSG
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
