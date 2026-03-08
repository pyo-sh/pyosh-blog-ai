#!/usr/bin/env bash
# test-orchestrator.sh — Verify orchestrator metadata + dispatched parsing (#72 item 2)
# Tests the @tsv-based extraction that replaces the broken \x1f/\x1e protocol.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/helpers.sh"

TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

# ── Test 1: Metadata extraction with @tsv ──
# This is the CRITICAL test. The old code joined all fields with \x1f,
# then read into only 2 variables, so meta only got the area field.
cat > "$TMPDIR/batch-multi.json" << 'EOF'
{
  "area": "server",
  "batchId": "20260308-abc",
  "issues": [42, 43, 44],
  "status": {"42": "dispatched", "43": "dispatched", "44": "completed"},
  "dispatched": {
    "42": {"pid": 12345, "dispatchedAt": "2026-03-08T10:01:00Z"},
    "43": {"pid": 12346, "dispatchedAt": "2026-03-08T10:02:00Z"}
  },
  "orchestratorPid": 99999,
  "orchestratorStartedAt": "1234567890",
  "createdAt": "2026-03-08T10:00:00Z"
}
EOF

# The new jq expression from lib/collect.sh
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
' "$TMPDIR/batch-multi.json")

IFS=$'\t' read -r area batch_id n_done n_active n_pending n_blocked n_failed \
  n_total orch_pid orch_started_at created_at <<< "$meta_tsv"

assert_eq "meta: area" "server" "$area"
assert_eq "meta: batch_id" "20260308-abc" "$batch_id"
assert_eq "meta: n_done (completed)" "1" "$n_done"
assert_eq "meta: n_active (dispatched)" "2" "$n_active"
assert_eq "meta: n_pending" "0" "$n_pending"
assert_eq "meta: n_blocked" "0" "$n_blocked"
assert_eq "meta: n_failed" "0" "$n_failed"
assert_eq "meta: n_total" "3" "$n_total"
# CRITICAL: these were always empty in the old code
assert_eq "meta: orch_pid extracted (was broken)" "99999" "$orch_pid"
assert_eq "meta: orch_started_at extracted" "1234567890" "$orch_started_at"
assert_eq "meta: created_at extracted" "2026-03-08T10:00:00Z" "$created_at"

# ── Test 2: Dispatched list extraction ──
# All dispatched issues must appear, not just the first one.
dispatched_tsv=$(jq -r '
  . as $root | .dispatched | to_entries[]
  | select($root.status[.key] == "dispatched")
  | [.key, (.value.pid // 0 | tostring), (.value.dispatchedAt // "")]
  | @tsv
' "$TMPDIR/batch-multi.json")

n_rows=$(printf '%s\n' "$dispatched_tsv" | grep -c .)
assert_eq "dispatched: count is 2" "2" "$n_rows"

# Read all rows
row_idx=0
while IFS=$'\t' read -r issue pid dispatched_at; do
  [[ -z "$issue" ]] && continue
  row_idx=$(( row_idx + 1 ))
  case "$issue" in
    42) assert_eq "dispatched #42: pid" "12345" "$pid" ;;
    43) assert_eq "dispatched #43: pid" "12346" "$pid" ;;
    *)  assert_eq "dispatched: unexpected issue" "42 or 43" "$issue" ;;
  esac
done <<< "$dispatched_tsv"
assert_eq "dispatched: iterated all rows" "2" "$row_idx"

# ── Test 3: Completed batch (all issues done) ──
cat > "$TMPDIR/batch-done.json" << 'EOF'
{
  "area": "client",
  "batchId": "20260308-xyz",
  "issues": [10, 11],
  "status": {"10": "completed", "11": "completed"},
  "dispatched": {
    "10": {"pid": 111, "dispatchedAt": "2026-03-08T09:00:00Z"},
    "11": {"pid": 222, "dispatchedAt": "2026-03-08T09:01:00Z"}
  },
  "orchestratorPid": 88888,
  "orchestratorStartedAt": "9876543210",
  "createdAt": "2026-03-08T09:00:00Z"
}
EOF

meta_tsv2=$(jq -r '
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
' "$TMPDIR/batch-done.json")

IFS=$'\t' read -r area2 bid2 nd2 na2 np2 nb2 nf2 nt2 op2 os2 ca2 <<< "$meta_tsv2"
assert_eq "done batch: area" "client" "$area2"
assert_eq "done batch: n_done" "2" "$nd2"
assert_eq "done batch: n_total" "2" "$nt2"

# batch_status = done when n_terminal >= n_total
n_terminal=$(( nd2 + nf2 ))
batch_status="active"
(( n_terminal >= nt2 )) && batch_status="done"
assert_eq "done batch: batch_status" "done" "$batch_status"

# No dispatched rows (all completed, not dispatched status)
dispatched_tsv2=$(jq -r '
  . as $root | .dispatched | to_entries[]
  | select($root.status[.key] == "dispatched")
  | [.key, (.value.pid // 0 | tostring), (.value.dispatchedAt // "")]
  | @tsv
' "$TMPDIR/batch-done.json")
assert_eq "done batch: no dispatched rows" "" "$dispatched_tsv2"

# ── Test 4: Pipeline state extraction ──
mkdir -p "$TMPDIR/pipeline/server"
cat > "$TMPDIR/pipeline/server/issue-42.state.json" << 'EOF'
{"step": "review", "pr": 15}
EOF

praw=$(jq -r '[.step // "-", (.pr // 0 | tostring)] | @tsv' \
  "$TMPDIR/pipeline/server/issue-42.state.json")
IFS=$'\t' read -r step pr_num <<< "$praw"
assert_eq "pipeline: step" "review" "$step"
assert_eq "pipeline: pr_num" "15" "$pr_num"

# ── Test 5: Empty batch file ──
cat > "$TMPDIR/batch-empty.json" << 'EOF'
{
  "area": "server",
  "batchId": "empty",
  "issues": [],
  "status": {},
  "dispatched": {},
  "orchestratorPid": 0,
  "orchestratorStartedAt": "",
  "createdAt": "2026-03-08T10:00:00Z"
}
EOF

meta_tsv3=$(jq -r '
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
' "$TMPDIR/batch-empty.json")

IFS=$'\t' read -r area3 bid3 nd3 na3 np3 nb3 nf3 nt3 op3 os3 ca3 <<< "$meta_tsv3"
assert_eq "empty batch: orch_pid is 0" "0" "$op3"
assert_eq "empty batch: n_total is 0" "0" "$nt3"

test_summary
