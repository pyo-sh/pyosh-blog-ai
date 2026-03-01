#!/usr/bin/env bash
# tools/agent-tracker/hooks/on-statusline.sh
# Reads StatusLine JSON from stdin, writes sidecar file for agent-tracker dashboard.
# Called by statusline-wrapper.sh every ~300ms. Must be non-blocking.
#
# Sidecar location: /tmp/agent-tracker/{pane_id}.json
# Falls back to PID-based filename when TMUX_PANE is not set.

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

# Extract fields from StatusLine JSON using jq
# Merge into existing sidecar to preserve status and task set by on-status.sh
existing="{}"
[[ -f "$sidecar_path" ]] && existing=$(cat "$sidecar_path" 2>/dev/null || echo "{}")

updated=$(jq -n --argjson existing "$existing" --argjson input "$input" --arg pane_id "$pane_id" '
  # Extract model display name
  ($input.model.display_name // $input.model.id // "Claude") as $model |
  # Extract token info
  ($input.context_window.context_window_size // 200000) as $max_tokens |
  ($input.context_window.total_input_tokens // 0) as $used_tokens |
  (if $max_tokens > 0 then ($used_tokens * 100 / $max_tokens | floor) else 0 end) as $pct |
  # Merge: new data overwrites, but preserve status/task from existing
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
' 2>/dev/null)

# Atomic write via temp file
if [[ -n "$updated" ]]; then
  tmp="${sidecar_path}.tmp.$$"
  printf '%s\n' "$updated" > "$tmp"
  mv -f "$tmp" "$sidecar_path"
fi

exit 0
