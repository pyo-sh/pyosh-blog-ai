#!/usr/bin/env bash
# test-path-traversal.sh — path traversal block (#113)
#
# Regression: pane_id values that are not purely numeric (e.g. "../../../etc")
# must be rejected by the guard in _collect_claude_pane before any file I/O.
# This prevents a malformed pane_id from constructing a path outside the sidecar
# directory.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/helpers.sh"

# The guard from lib/collect.sh and backend/collector.py:
#   [[ ! "$pane_id" =~ ^%[0-9]+$ ]] && return   (bash)
#   if not re.match(r"^\d+$", pane_file): return None  (Python)
#
# pane_id format: "%N" where N is digits only.

_pane_id_valid() {
  local pane_id="$1"
  [[ "$pane_id" =~ ^%[0-9]+$ ]] && echo "valid" || echo "rejected"
}

# ── Test 1: Normal numeric pane IDs are accepted ──
assert_eq "pane_id %0: valid"    "valid"    "$(_pane_id_valid '%0')"
assert_eq "pane_id %1: valid"    "valid"    "$(_pane_id_valid '%1')"
assert_eq "pane_id %42: valid"   "valid"    "$(_pane_id_valid '%42')"
assert_eq "pane_id %100: valid"  "valid"    "$(_pane_id_valid '%100')"

# ── Test 2: Path traversal patterns are rejected ──
assert_eq "pane_id %../etc: rejected"          "rejected" "$(_pane_id_valid '%../etc')"
assert_eq "pane_id %0/../../../: rejected"     "rejected" "$(_pane_id_valid '%0/../../../')"
assert_eq "pane_id %../../passwd: rejected"    "rejected" "$(_pane_id_valid '%../../passwd')"

# ── Test 3: Shell injection characters are rejected ──
assert_eq "pane_id %; rm -rf: rejected"        "rejected" "$(_pane_id_valid '%; rm -rf')"
assert_eq "pane_id %\$(cmd): rejected"         "rejected" "$(_pane_id_valid '%$(cmd)')"
assert_eq "pane_id %0|cmd: rejected"           "rejected" "$(_pane_id_valid '%0|cmd')"
assert_eq "pane_id %0 extra: rejected"         "rejected" "$(_pane_id_valid '%0 extra')"

# ── Test 4: Missing % prefix is rejected ──
assert_eq "pane_id 42 (no %): rejected"        "rejected" "$(_pane_id_valid '42')"
assert_eq "pane_id empty: rejected"            "rejected" "$(_pane_id_valid '')"
assert_eq "pane_id %: rejected (no digits)"    "rejected" "$(_pane_id_valid '%')"

# ── Test 5: Verify the sidecar path construction is safe for valid IDs ──
# pane_id "%5" → pane_file "5" → sidecar path SIDECAR_DIR/HASH/SESSION/5.json
TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

SIDECAR_DIR="$TMPDIR/sidecar"
HASH="abc123"
SESSION="lab"
mkdir -p "$SIDECAR_DIR/$HASH/$SESSION"
echo '{"status":"working"}' > "$SIDECAR_DIR/$HASH/$SESSION/5.json"

pane_id="%5"
if [[ "$pane_id" =~ ^%[0-9]+$ ]]; then
  pane_file="${pane_id#%}"
  sidecar_path="$SIDECAR_DIR/$HASH/$SESSION/${pane_file}.json"
  path_resolved=$(realpath "$sidecar_path" 2>/dev/null || echo "$sidecar_path")
  expected="$SIDECAR_DIR/$HASH/$SESSION/5.json"
  assert_eq "valid pane_id: path is inside sidecar_dir" "$expected" "$path_resolved"
fi

# ── Test 6: Traversal attempt would escape sidecar_dir (verify the guard is needed) ──
# Without the guard, %../../../etc would become sidecar_dir/hash/session/../../../etc.
bad_pane_id="%../../../etc"
guard_triggered="no"
if [[ ! "$bad_pane_id" =~ ^%[0-9]+$ ]]; then
  guard_triggered="yes"
fi
assert_eq "traversal pane_id: guard triggers" "yes" "$guard_triggered"

test_summary
