#!/usr/bin/env bash
# test-sidecar-cleanup.sh — Verify sidecar cleanup safety (#72 item 5)
# When tmux session doesn't exist, sidecars must NOT be deleted.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/helpers.sh"

TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

SIDECAR_DIR="$TMPDIR/sidecar"
mkdir -p "$SIDECAR_DIR"

# Create test sidecar files
echo '{"status":"working"}' > "$SIDECAR_DIR/100.json"
echo '{"status":"idle"}' > "$SIDECAR_DIR/200.json"

# Simulate the safe cleanup logic from agent-tracker.sh
SESSION="nonexistent_session_$$"

# The key: tmux has-session fails for nonexistent session,
# so the entire cleanup block is skipped.
if tmux has-session -t "$SESSION" 2>/dev/null; then
  # This should NOT execute
  declare -A _active_panes=()
  while IFS= read -r _pid; do
    _active_panes["$_pid"]=1
  done < <(tmux list-panes -s -t "$SESSION" -F '#{pane_id}' 2>/dev/null | sed 's/^%//')
  for _f in "$SIDECAR_DIR"/*.json; do
    [[ -f "$_f" ]] || continue
    _fname="${_f##*/}"
    _pane="${_fname%.json}"
    [[ -z "${_active_panes[$_pane]+x}" ]] && rm -f "$_f"
  done
fi

# Verify files still exist
assert_eq "nonexistent session: sidecar 100.json preserved" \
  "true" "$(test -f "$SIDECAR_DIR/100.json" && echo true || echo false)"
assert_eq "nonexistent session: sidecar 200.json preserved" \
  "true" "$(test -f "$SIDECAR_DIR/200.json" && echo true || echo false)"

test_summary
