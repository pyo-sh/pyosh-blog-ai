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

# Stable pane identifier for on-statusline.sh (which runs as a child of this
# wrapper, so its own $PPID points here — unstable). Export our PPID (= Claude
# Code PID) so on-statusline.sh can use the same ID as on-status.sh. (#47)
export AGENT_TRACKER_PANE="${TMUX_PANE:-pid-$PPID}"

# Pre-compute tokens + last user message from transcript in a single pass.
# Uses tail to avoid slurping the entire file (O(fixed) instead of O(file size)).
# total_input_tokens excludes system prompt/tools/memory — transcript is accurate.
# See: github.com/anthropics/claude-code/issues/13652
_tp=$(printf '%s' "$input" | jq -r '.transcript_path // empty' 2>/dev/null)
export TRANSCRIPT_TOKENS=0 TRANSCRIPT_LAST_MSG=""
if [[ -n "$_tp" && -f "$_tp" ]]; then
  _raw=$(tail -n 200 "$_tp" | jq -rs '
    {
      tokens: (
        map(select(.message.usage and .isSidechain != true and .isApiErrorMessage != true)) |
        last |
        if . then
          (.message.usage.input_tokens // 0) +
          (.message.usage.cache_read_input_tokens // 0) +
          (.message.usage.cache_creation_input_tokens // 0)
        else 0 end
      ),
      last_msg: (
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
      )
    } | "\(.tokens)\u001e\(.last_msg)"
  ' 2>/dev/null || echo "0")
  if [[ -n "$_raw" ]]; then
    IFS=$'\x1e' read -r TRANSCRIPT_TOKENS TRANSCRIPT_LAST_MSG <<< "$_raw"
  fi
  export TRANSCRIPT_TOKENS TRANSCRIPT_LAST_MSG
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
