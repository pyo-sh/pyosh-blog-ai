#!/usr/bin/env bash
# test-list-panes-failure.sh — list-panes failure skips v2 orphan cleanup (#113)
#
# Regression: if tmux has-session succeeds but list-panes fails (race condition),
# the cleanup block must skip orphan deletion rather than deleting ALL sidecars
# because _active_panes would be empty, incorrectly marking every sidecar as orphan.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/helpers.sh"

TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

SIDECAR_DIR="$TMPDIR/sidecar"
HASH="abc123"
SESSION="lab"
mkdir -p "$SIDECAR_DIR/$HASH/$SESSION"

# Create two v2 sidecars simulating active panes
echo '{"schema_version":"v2","status":"working"}' > "$SIDECAR_DIR/$HASH/$SESSION/10.json"
echo '{"schema_version":"v2","status":"idle"}' > "$SIDECAR_DIR/$HASH/$SESSION/20.json"

# ── Scenario: list-panes returns empty (simulating failure / timeout) ──
# When _pane_ids is empty, cleanup must be skipped entirely.
_pane_ids=""  # simulate list-panes failure

if [[ -n "$_pane_ids" ]]; then
  # Would delete all sidecars because _active_panes is empty
  declare -A _active_panes=()
  while IFS= read -r _pid; do
    [[ -n "$_pid" ]] && _active_panes["${_pid#%}"]=1
  done <<< "$_pane_ids"
  _v2_dir="$SIDECAR_DIR/$HASH/$SESSION"
  for _f in "$_v2_dir"/*.json; do
    [[ -f "$_f" ]] || continue
    _fname="${_f##*/}"
    _pane="${_fname%.json}"
    [[ -z "${_active_panes[$_pane]+x}" ]] && rm -f "$_f"
  done
fi

# Both sidecars must survive because list-panes returned empty (failure)
assert_eq "list-panes failure: 10.json preserved" \
  "true" "$(test -f "$SIDECAR_DIR/$HASH/$SESSION/10.json" && echo true || echo false)"
assert_eq "list-panes failure: 20.json preserved" \
  "true" "$(test -f "$SIDECAR_DIR/$HASH/$SESSION/20.json" && echo true || echo false)"

# ── Scenario: list-panes succeeds — orphan is removed, active is kept ──
echo '{"schema_version":"v2","status":"working"}' > "$SIDECAR_DIR/$HASH/$SESSION/30.json"
echo '{"schema_version":"v2","status":"idle"}' > "$SIDECAR_DIR/$HASH/$SESSION/99.json"

# Simulate successful list-panes: pane %10, %20, %30 are active; %99 is orphan
_pane_ids="%10
%20
%30"

if [[ -n "$_pane_ids" ]]; then
  declare -A _active_panes=()
  while IFS= read -r _pid; do
    [[ -n "$_pid" ]] && _active_panes["${_pid#%}"]=1
  done <<< "$_pane_ids"
  _v2_dir="$SIDECAR_DIR/$HASH/$SESSION"
  for _f in "$_v2_dir"/*.json; do
    [[ -f "$_f" ]] || continue
    _fname="${_f##*/}"
    _pane="${_fname%.json}"
    [[ -z "${_active_panes[$_pane]+x}" ]] && rm -f "$_f"
  done
  unset _active_panes _fname _pane _f _v2_dir _pid
fi
unset _pane_ids

assert_eq "list-panes success: active 10.json kept" \
  "true" "$(test -f "$SIDECAR_DIR/$HASH/$SESSION/10.json" && echo true || echo false)"
assert_eq "list-panes success: active 20.json kept" \
  "true" "$(test -f "$SIDECAR_DIR/$HASH/$SESSION/20.json" && echo true || echo false)"
assert_eq "list-panes success: active 30.json kept" \
  "true" "$(test -f "$SIDECAR_DIR/$HASH/$SESSION/30.json" && echo true || echo false)"
assert_eq "list-panes success: orphan 99.json removed" \
  "false" "$(test -f "$SIDECAR_DIR/$HASH/$SESSION/99.json" && echo true || echo false)"

test_summary
