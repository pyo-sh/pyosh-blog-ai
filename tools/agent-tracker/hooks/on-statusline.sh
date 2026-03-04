#!/usr/bin/env bash
# tools/agent-tracker/hooks/on-statusline.sh
# Reads StatusLine JSON from stdin, writes sidecar file for agent-tracker dashboard.
# Called by statusline-wrapper.sh every ~300ms. Must be non-blocking.
#
# Sidecar location: /tmp/agent-tracker/{pane_id}.json
# Falls back to PID-based filename when TMUX_PANE is not set.
# Uses flock to prevent race conditions with on-status.sh.

set -euo pipefail

SIDECAR_DIR="/tmp/agent-tracker"

# Determine pane identifier
pane_id="${TMUX_PANE:-pid-$$}"

# Sanitize pane_id for filename (remove % prefix)
pane_file="${pane_id#%}"

# Read JSON from stdin
input=$(cat)
[[ -z "$input" ]] && exit 0

# Ensure sidecar directory exists
mkdir -p "$SIDECAR_DIR"

sidecar_path="${SIDECAR_DIR}/${pane_file}.json"
lock_path="${sidecar_path}.lock"

# Calculate tokens from transcript (more accurate than total_input_tokens
# which excludes system prompt/tools/memory).
# See: github.com/anthropics/claude-code/issues/13652
transcript_path=$(printf '%s' "$input" | jq -r '.transcript_path // empty' 2>/dev/null)
used_tokens=0
if [[ -n "$transcript_path" && -f "$transcript_path" ]]; then
  used_tokens=$(jq -s '
    map(select(.message.usage and .isSidechain != true and .isApiErrorMessage != true)) |
    last |
    if . then
      (.message.usage.input_tokens // 0) +
      (.message.usage.cache_read_input_tokens // 0) +
      (.message.usage.cache_creation_input_tokens // 0)
    else 0 end
  ' < "$transcript_path" 2>/dev/null || echo 0)
fi

# Build jq expression for the merge
jq_expr='
  ($input.model.display_name // $input.model.id // "Claude") as $model |
  ($input.context_window.context_window_size // 200000) as $max_tokens |
  (if $max_tokens > 0 then ($used_tokens * 100 / $max_tokens | floor) else 0 end) as $pct |
  $existing * {
    pane_id: $pane_id,
    session_id: ($input.session_id // $existing.session_id // null),
    model: $model,
    tokens: {
      used: $used_tokens,
      max: $max_tokens,
      pct: (if $pct > 100 then 100 else $pct end)
    },
    cwd: ($input.cwd // $existing.cwd // null),
    transcript_path: ($input.transcript_path // $existing.transcript_path // null),
    updated_at: now
  }
'

# Locked read-modify-write to prevent race with on-status.sh
(
  flock -n 9 || exit 0

  existing="{}"
  [[ -f "$sidecar_path" ]] && existing=$(cat "$sidecar_path" 2>/dev/null || echo "{}")

  updated=$(jq -n --argjson existing "$existing" --argjson input "$input" --arg pane_id "$pane_id" \
    --argjson used_tokens "${used_tokens:-0}" "$jq_expr" 2>/dev/null)

  if [[ -n "$updated" ]]; then
    tmp="${sidecar_path}.tmp.$$"
    printf '%s\n' "$updated" > "$tmp"
    mv -f "$tmp" "$sidecar_path"
  fi
) 9>"$lock_path"

exit 0
