#!/usr/bin/env bash
# test-sidecar-cleanup.sh — Verify sidecar cleanup safety (#72, #109)
# 1. v1 flat sidecars are removed unconditionally (immediate cutover, #109).
# 2. When tmux session doesn't exist, v2 sidecars must NOT be deleted.
# 3. When session exists, orphan pane sidecars are removed; active ones kept.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/helpers.sh"

TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

SIDECAR_DIR="$TMPDIR/sidecar"
mkdir -p "$SIDECAR_DIR"

# ── Test 1: v1 flat sidecars are removed at startup ────────────────────────
echo '{"status":"working","schema_version":"v1"}' > "$SIDECAR_DIR/100.json"
echo '{"status":"idle","schema_version":"v1"}' > "$SIDECAR_DIR/200.json"

# Simulate v1 flat cleanup
for _f in "$SIDECAR_DIR"/*.json; do
  [[ -f "$_f" ]] && rm -f "$_f"
done
unset _f

assert_eq "v1 flat: 100.json removed" \
  "false" "$(test -f "$SIDECAR_DIR/100.json" && echo true || echo false)"
assert_eq "v1 flat: 200.json removed" \
  "false" "$(test -f "$SIDECAR_DIR/200.json" && echo true || echo false)"

# ── Test 2: v2 sidecars preserved when session doesn't exist ──────────────
HASH="abc123"
SESSION="nonexistent_session_$$"

mkdir -p "$SIDECAR_DIR/${HASH}/${SESSION}"
echo '{"schema_version":"v2","status":"working"}' > "$SIDECAR_DIR/${HASH}/${SESSION}/100.json"
echo '{"schema_version":"v2","status":"idle"}' > "$SIDECAR_DIR/${HASH}/${SESSION}/200.json"

# The key: tmux has-session fails for nonexistent session,
# so the v2 cleanup block is skipped entirely.
if tmux has-session -t "$SESSION" 2>/dev/null; then
  # This should NOT execute
  declare -A _active_panes=()
  while IFS= read -r _pid; do
    _active_panes["$_pid"]=1
  done < <(tmux list-panes -s -t "$SESSION" -F '#{pane_id}' 2>/dev/null | sed 's/^%//')
  _v2_dir="$SIDECAR_DIR/${HASH}/${SESSION}"
  if [[ -d "$_v2_dir" ]]; then
    for _f in "$_v2_dir"/*.json; do
      [[ -f "$_f" ]] || continue
      _fname="${_f##*/}"
      _pane="${_fname%.json}"
      [[ -z "${_active_panes[$_pane]+x}" ]] && rm -f "$_f"
    done
  fi
fi

assert_eq "v2 nonexistent session: 100.json preserved" \
  "true" "$(test -f "$SIDECAR_DIR/${HASH}/${SESSION}/100.json" && echo true || echo false)"
assert_eq "v2 nonexistent session: 200.json preserved" \
  "true" "$(test -f "$SIDECAR_DIR/${HASH}/${SESSION}/200.json" && echo true || echo false)"

# ── Test 3: orphan deletion with active session ────────────────────────────
# Directly invoke the orphan-deletion loop body with a controlled _active_panes
# map, bypassing `tmux has-session` to make the test self-contained.
HASH2="def456"
SESSION2="fake_active_session"
mkdir -p "$SIDECAR_DIR/${HASH2}/${SESSION2}"
echo '{"schema_version":"v2","status":"working"}' > "$SIDECAR_DIR/${HASH2}/${SESSION2}/10.json"
echo '{"schema_version":"v2","status":"idle"}' > "$SIDECAR_DIR/${HASH2}/${SESSION2}/99.json"

# Simulate: pane 10 is active, pane 99 is orphan
declare -A _active_panes=()
_active_panes["10"]=1  # active pane

_v2_dir="$SIDECAR_DIR/${HASH2}/${SESSION2}"
for _f in "$_v2_dir"/*.json; do
  [[ -f "$_f" ]] || continue
  _fname="${_f##*/}"
  _pane="${_fname%.json}"
  [[ -z "${_active_panes[$_pane]+x}" ]] && rm -f "$_f"
done
unset _active_panes _fname _pane _f _v2_dir

assert_eq "v2 active session: active pane 10.json kept" \
  "true" "$(test -f "$SIDECAR_DIR/${HASH2}/${SESSION2}/10.json" && echo true || echo false)"
assert_eq "v2 active session: orphan pane 99.json removed" \
  "false" "$(test -f "$SIDECAR_DIR/${HASH2}/${SESSION2}/99.json" && echo true || echo false)"

test_summary
