#!/usr/bin/env bash
# tools/agent-tracker/hooks/on-statusline.sh
# Reads StatusLine JSON from stdin, writes sidecar file for agent-tracker dashboard.
# Called by statusline-wrapper.sh every ~300ms. Must be non-blocking.
#
# Sidecar v2 location: .workspace/agent-tracker/<socket-hash>/<session>/<pane>.json
#   socket-hash: first 6 chars of MD5 of tmux socket path (from $TMUX env)
#   session: tmux session name
#   pane: pane id without % prefix
# Falls back to PID-based filename when TMUX_PANE is not set.
# Uses flock to prevent race conditions with on-status.sh.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
SIDECAR_DIR="$REPO_ROOT/.workspace/agent-tracker"

# Determine pane identifier
# AGENT_TRACKER_PANE is exported by statusline-wrapper.sh with a stable value
# (wrapper's PPID = Claude Code PID). Without it, $PPID here would point to the
# wrapper process (different each ~300ms invocation). (#47)
pane_id="${TMUX_PANE:-${AGENT_TRACKER_PANE:-pid-$PPID}}"

# Sanitize pane_id for filename (remove % prefix)
pane_file="${pane_id#%}"

# Read JSON from stdin
input=$(cat)
[[ -z "$input" ]] && exit 0

# ── v2 namespace: socket-hash / session / pane ──────────────────────────────
# $TMUX format: socket_path,server_pid,session_id
_tmux_socket=""
_socket_hash="default"
_session="unknown"
if [[ -n "${TMUX:-}" ]]; then
  _tmux_socket="${TMUX%%,*}"
  _socket_hash=$(printf '%s' "$_tmux_socket" | md5sum | cut -c1-6)  # md5sum: GNU coreutils (Linux only)
  _session=$(tmux display-message -p '#{session_name}' 2>/dev/null || true)
  _session="${_session:-unknown}"
fi

mkdir -p "${SIDECAR_DIR}/${_socket_hash}/${_session}"

sidecar_path="${SIDECAR_DIR}/${_socket_hash}/${_session}/${pane_file}.json"
lock_path="${sidecar_path}.lock"

# Use pre-computed tokens from statusline-wrapper.sh when available (avoids duplicate jq).
# Standalone invocation falls back to current_usage extraction from input JSON.
_precomputed="${TRANSCRIPT_TOKENS:-0}"

# Build jq expression for the merge.
# Token priority: pre-computed > current_usage > used_percentage reverse-calc > 0.
jq_expr='
  ($input.model.display_name // $input.model.id) as $model_raw |
  ($input.context_window.context_window_size // 200000) as $max_tokens |
  (($input.context_window.used_percentage // 0) | floor) as $pct |
  (
    if $precomputed > 0 then $precomputed
    elif $input.context_window.current_usage != null then
      (($input.context_window.current_usage.input_tokens // 0) +
       ($input.context_window.current_usage.cache_creation_input_tokens // 0) +
       ($input.context_window.current_usage.cache_read_input_tokens // 0))
    elif $pct > 0 then
      ($max_tokens * $pct / 100 | floor)
    else 0 end
  ) as $used_tokens |
  ($existing * {
    schema_version: "v2",
    pane_id: $pane_id,
    session_name: $session,
    tmux_server: $tmux_socket,
    session_id: ($input.session_id // $existing.session_id // null),
    model: ($model_raw // $existing.model // "unknown"),
    tokens: {
      used: $used_tokens,
      max: $max_tokens,
      pct: (if $pct > 100 then 100 else $pct end)
    },
    cwd: ($input.cwd // $existing.cwd // null),
    transcript_path: ($input.transcript_path // $existing.transcript_path // null),
    updated_at: now
  }) |
  if $used_tokens > 0 then . + { tokens_updated_at: now } else . end
'

# Locked read-modify-write to prevent race with on-status.sh
(
  flock -n 9 || exit 0

  existing="{}"
  [[ -f "$sidecar_path" ]] && existing=$(cat "$sidecar_path" 2>/dev/null || echo "{}")

  updated=$(jq -n --argjson existing "$existing" --argjson input "$input" --arg pane_id "$pane_id" \
    --arg session "$_session" --arg tmux_socket "$_tmux_socket" \
    --argjson precomputed "${_precomputed:-0}" "$jq_expr" 2>/dev/null)

  if [[ -n "$updated" ]]; then
    tmp="${sidecar_path}.tmp.$$"
    printf '%s\n' "$updated" > "$tmp"
    mv -f "$tmp" "$sidecar_path"
  fi
) 9>"$lock_path"

exit 0
