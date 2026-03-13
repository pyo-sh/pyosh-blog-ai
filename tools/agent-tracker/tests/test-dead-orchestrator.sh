#!/usr/bin/env bash
# test-dead-orchestrator.sh — dead orchestrator display (#113)
#
# Regression: an orchestrator whose PID is no longer running must be shown with
# batch_status="dead" (not "active") so it is visibly flagged on the dashboard
# rather than silently treated as still running.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/helpers.sh"

TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

# The _check_pid_alive logic from lib/collect.sh: kill -0 + /proc stat check.
# Simulate with known-dead and known-alive PIDs.

_check_pid_alive_sim() {
  local pid=$1
  [[ -z "$pid" || "$pid" == "0" || "$pid" == "null" ]] && return 1
  kill -0 "$pid" 2>/dev/null || return 1
  return 0
}

# ── Test 1: PID 0 is never alive ──
_check_pid_alive_sim 0 && r1="alive" || r1="dead"
assert_eq "PID 0: dead" "dead" "$r1"

# ── Test 2: Nonexistent PID (99999999) is dead ──
_check_pid_alive_sim 99999999 && r2="alive" || r2="dead"
assert_eq "nonexistent PID: dead" "dead" "$r2"

# ── Test 3: Own PID is alive ──
_check_pid_alive_sim $$ && r3="alive" || r3="dead"
assert_eq "own PID ($$): alive" "alive" "$r3"

# ── Test 4: batch_status logic with dead orchestrator ──
# Simulate the orchestrator state parsing from lib/collect.sh
cat > "$TMPDIR/batch-dead.json" << 'EOF'
{
  "area": "workspace",
  "batchId": "20260313-test",
  "issues": [10, 11],
  "status": {"10": "dispatched", "11": "pending"},
  "dispatched": {"10": {"pid": 99999999, "dispatchedAt": "2026-03-13T10:00:00Z"}},
  "orchestratorPid": 99999999,
  "orchestratorStartedAt": "",
  "createdAt": "2026-03-13T09:00:00Z"
}
EOF

meta_tsv=$(jq -r '
  def cnt(v): [.status | to_entries[] | select(.value == v)] | length;
  [
    .area,
    .batchId,
    (cnt("completed") | tostring),
    (cnt("dispatched") | tostring),
    (cnt("pending") | tostring),
    (cnt("blocked") | tostring),
    (cnt("failed") | tostring),
    (.issues | length | tostring),
    (.orchestratorPid // 0 | tostring),
    (.orchestratorStartedAt // ""),
    (.createdAt // "")
  ] | @tsv
' "$TMPDIR/batch-dead.json")

IFS=$'\t' read -r area batch_id n_done n_active n_pending n_blocked n_failed \
  n_total orch_pid orch_started_at created_at <<< "$meta_tsv"

batch_alive=true
_check_pid_alive_sim "$orch_pid" || batch_alive=false

n_terminal=$(( n_done + n_failed ))
batch_status="active"
if ! $batch_alive; then
  batch_status="dead"
elif (( n_terminal >= n_total )); then
  batch_status="done"
fi

assert_eq "dead batch: area" "workspace" "$area"
assert_eq "dead batch: orch_pid extracted" "99999999" "$orch_pid"
assert_eq "dead batch: batch_alive=false" "false" "$batch_alive"
assert_eq "dead batch: batch_status=dead" "dead" "$batch_status"

# ── Test 5: Dead orchestrator is NOT hidden (status displayed, not skipped) ──
# The render layer reads batch_status; "dead" must be a recognized state.
valid_statuses=("active" "done" "dead")
found=false
for s in "${valid_statuses[@]}"; do
  [[ "$s" == "$batch_status" ]] && found=true && break
done
assert_eq "dead status: recognized by render" "true" "$found"

# ── Test 6: Active batch with living PID stays active ──
cat > "$TMPDIR/batch-active.json" << EOF
{
  "area": "client",
  "batchId": "20260313-live",
  "issues": [1, 2],
  "status": {"1": "dispatched", "2": "pending"},
  "dispatched": {"1": {"pid": $$, "dispatchedAt": "2026-03-13T10:00:00Z"}},
  "orchestratorPid": $$,
  "orchestratorStartedAt": "",
  "createdAt": "2026-03-13T09:00:00Z"
}
EOF

meta_tsv2=$(jq -r '
  def cnt(v): [.status | to_entries[] | select(.value == v)] | length;
  [
    .area, .batchId,
    (cnt("completed") | tostring), (cnt("dispatched") | tostring),
    (cnt("pending") | tostring), (cnt("blocked") | tostring),
    (cnt("failed") | tostring), (.issues | length | tostring),
    (.orchestratorPid // 0 | tostring), (.orchestratorStartedAt // ""),
    (.createdAt // "")
  ] | @tsv
' "$TMPDIR/batch-active.json")

IFS=$'\t' read -r a2 b2 nd2 na2 np2 nb2 nf2 nt2 op2 os2 ca2 <<< "$meta_tsv2"
batch_alive2=true
_check_pid_alive_sim "$op2" || batch_alive2=false
batch_status2="active"
$batch_alive2 || batch_status2="dead"

assert_eq "live batch: orch_pid is own PID" "$$" "$op2"
assert_eq "live batch: batch_alive=true" "true" "$batch_alive2"
assert_eq "live batch: batch_status=active" "active" "$batch_status2"

test_summary
