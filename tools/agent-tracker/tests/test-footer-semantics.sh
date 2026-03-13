#!/usr/bin/env bash
# test-footer-semantics.sh — footer aggregation correctly separates fault/unknown from idle (#114)
#
# Regression: fault and unknown agents must not be counted as idle.
# Dead orchestrators must appear in the footer summary.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/helpers.sh"

TRACKER_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$TRACKER_DIR/lib/util.sh"

# ── Simulate the status aggregation from render.sh ──

_aggregate_statuses() {
  local statuses_json=$1
  local n_working=0 n_plan=0 n_idle=0 n_stale=0 n_fault=0 n_unknown=0 n_total=0

  local agents_tsv
  agents_tsv=$(printf '%s' "$statuses_json" | jq -r '.agents[] | .status' 2>/dev/null)

  while IFS= read -r status; do
    [[ -z "$status" ]] && continue
    (( ++n_total ))
    case "$status" in
      working|needs-input) (( ++n_working )) ;;
      plan)                (( ++n_plan ))    ;;
      stale)               (( ++n_stale ))   ;;
      fault)               (( ++n_fault ))   ;;
      unknown)             (( ++n_unknown )) ;;
      *)                   (( ++n_idle ))    ;;
    esac
  done <<< "$agents_tsv"

  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s' \
    "$n_total" "$n_working" "$n_plan" "$n_stale" "$n_fault" "$n_unknown" "$n_idle"
}

# ── Test 1: fault is not counted as idle ──
snapshot1=$(jq -nc '{
  "agents": [
    {"pane_addr":"1:0 %1","pane_id":"%1","engine":"claude","model":"sonnet","status":"idle","tokens":{"pct":10,"used":10000,"total":100000,"source":"sidecar","fresh":true},"task":"-","activity":null},
    {"pane_addr":"1:1 %2","pane_id":"%2","engine":"claude","model":"sonnet","status":"fault","tokens":{"pct":0,"used":0,"total":0,"source":"unknown","fresh":true},"task":"-","activity":null}
  ],
  "orchestrators": []
}')

IFS=$'\t' read -r n_total n_working n_plan n_stale n_fault n_unknown n_idle \
  <<< "$(_aggregate_statuses "$snapshot1")"

assert_eq "fault test: n_total=2"   "2" "$n_total"
assert_eq "fault test: n_fault=1"   "1" "$n_fault"
assert_eq "fault test: n_idle=1"    "1" "$n_idle"
assert_eq "fault test: n_unknown=0" "0" "$n_unknown"

# ── Test 2: unknown is not counted as idle ──
snapshot2=$(jq -nc '{
  "agents": [
    {"pane_addr":"1:0 %1","pane_id":"%1","engine":"claude","model":"sonnet","status":"idle","tokens":{"pct":0,"used":0,"total":0,"source":"unknown","fresh":true},"task":"-","activity":null},
    {"pane_addr":"1:1 %2","pane_id":"%2","engine":"codex","model":"Codex","status":"unknown","tokens":{"pct":0,"used":0,"total":0,"source":"unknown","fresh":true},"task":"-","activity":null}
  ],
  "orchestrators": []
}')

IFS=$'\t' read -r n_total n_working n_plan n_stale n_fault n_unknown n_idle \
  <<< "$(_aggregate_statuses "$snapshot2")"

assert_eq "unknown test: n_total=2"   "2" "$n_total"
assert_eq "unknown test: n_unknown=1" "1" "$n_unknown"
assert_eq "unknown test: n_idle=1"    "1" "$n_idle"
assert_eq "unknown test: n_fault=0"   "0" "$n_fault"

# ── Test 3: stale is not counted as idle ──
snapshot3=$(jq -nc '{
  "agents": [
    {"pane_addr":"1:0 %1","pane_id":"%1","engine":"claude","model":"sonnet","status":"stale","tokens":{"pct":50,"used":50000,"total":100000,"source":"sidecar","fresh":false},"task":"some task","activity":null},
    {"pane_addr":"1:1 %2","pane_id":"%2","engine":"claude","model":"sonnet","status":"idle","tokens":{"pct":0,"used":0,"total":0,"source":"unknown","fresh":true},"task":"-","activity":null}
  ],
  "orchestrators": []
}')

IFS=$'\t' read -r n_total n_working n_plan n_stale n_fault n_unknown n_idle \
  <<< "$(_aggregate_statuses "$snapshot3")"

assert_eq "stale test: n_total=2"  "2" "$n_total"
assert_eq "stale test: n_stale=1"  "1" "$n_stale"
assert_eq "stale test: n_idle=1"   "1" "$n_idle"
assert_eq "stale test: n_fault=0"  "0" "$n_fault"

# ── Test 4: mixed states — correct split ──
snapshot4=$(jq -nc '{
  "agents": [
    {"pane_addr":"1:0 %1","pane_id":"%1","engine":"claude","model":"sonnet","status":"working","tokens":{"pct":30,"used":30000,"total":100000,"source":"sidecar","fresh":true},"task":"doing work","activity":"Editing file.txt"},
    {"pane_addr":"1:1 %2","pane_id":"%2","engine":"claude","model":"sonnet","status":"idle","tokens":{"pct":0,"used":0,"total":0,"source":"unknown","fresh":true},"task":"-","activity":null},
    {"pane_addr":"1:2 %3","pane_id":"%3","engine":"claude","model":"sonnet","status":"fault","tokens":{"pct":0,"used":0,"total":0,"source":"unknown","fresh":true},"task":"-","activity":null},
    {"pane_addr":"1:3 %4","pane_id":"%4","engine":"codex","model":"Codex","status":"unknown","tokens":{"pct":0,"used":0,"total":0,"source":"unknown","fresh":true},"task":"-","activity":null},
    {"pane_addr":"1:4 %5","pane_id":"%5","engine":"claude","model":"sonnet","status":"stale","tokens":{"pct":80,"used":80000,"total":100000,"source":"sidecar","fresh":false},"task":"old task","activity":null}
  ],
  "orchestrators": []
}')

IFS=$'\t' read -r n_total n_working n_plan n_stale n_fault n_unknown n_idle \
  <<< "$(_aggregate_statuses "$snapshot4")"

assert_eq "mixed test: n_total=5"    "5" "$n_total"
assert_eq "mixed test: n_working=1"  "1" "$n_working"
assert_eq "mixed test: n_idle=1"     "1" "$n_idle"
assert_eq "mixed test: n_fault=1"    "1" "$n_fault"
assert_eq "mixed test: n_unknown=1"  "1" "$n_unknown"
assert_eq "mixed test: n_stale=1"    "1" "$n_stale"
assert_eq "mixed test: n_plan=0"     "0" "$n_plan"

# ── Test 5: dead orchestrator counted via .orchestrators key (Python backend) ──
snapshot5=$(jq -nc '{
  "agents": [],
  "orchestrators": [
    {"area":"workspace","batch_id":"20260314-abc","batch_status":"dead","n_done":0,"n_failed":0,"n_total":2,"elapsed":"5m30s","dispatched":[]},
    {"area":"client","batch_id":"20260314-xyz","batch_status":"active","n_done":1,"n_failed":0,"n_total":3,"elapsed":"2m10s","dispatched":[]}
  ]
}')

n_dead_orch=$(printf '%s' "$snapshot5" | jq -r '
  (.orchestrators // .orchestrator // [])[] |
  select(.batch_status == "dead" and (.area | type == "string") and .area != "") | .area
' 2>/dev/null | grep -c .)

assert_eq "dead orch: count via .orchestrators" "1" "$n_dead_orch"

# ── Test 6: dead orchestrator counted via .orchestrator key (legacy) ──
snapshot6=$(jq -nc '{
  "agents": [],
  "orchestrator": [
    {"area":"server","batch_id":"20260314-leg","batch_status":"dead","n_done":0,"n_failed":0,"n_total":1,"elapsed":"1m00s","dispatched":[]},
    {"area":"workspace","batch_id":"20260314-leg2","batch_status":"dead","n_done":0,"n_failed":0,"n_total":1,"elapsed":"2m00s","dispatched":[]}
  ]
}')

n_dead_leg=$(printf '%s' "$snapshot6" | jq -r '
  (.orchestrators // .orchestrator // [])[] |
  select(.batch_status == "dead" and (.area | type == "string") and .area != "") | .area
' 2>/dev/null | grep -c .)

assert_eq "dead orch: count via .orchestrator (legacy)" "2" "$n_dead_leg"

# ── Test 7: no dead orchestrators returns 0 ──
snapshot7=$(jq -nc '{
  "agents": [],
  "orchestrators": [
    {"area":"workspace","batch_id":"20260314-ok","batch_status":"active","n_done":0,"n_failed":0,"n_total":1,"elapsed":"30s","dispatched":[]}
  ]
}')

dead_tsv7=$(printf '%s' "$snapshot7" | jq -r '
  (.orchestrators // .orchestrator // [])[] |
  select(.batch_status == "dead" and (.area | type == "string") and .area != "") | .area
' 2>/dev/null)

n_dead_ok=0
[[ -n "$dead_tsv7" ]] && n_dead_ok=$(printf '%s\n' "$dead_tsv7" | grep -c .)
assert_eq "no dead orch: count is 0" "0" "$n_dead_ok"

# ── Test 8: null-area dead orchestrator is not counted (#114) ──
snapshot8=$(jq -nc '{
  "agents": [],
  "orchestrators": [
    {"area":null,"batch_id":"20260314-null","batch_status":"dead","n_done":0,"n_failed":0,"n_total":1,"elapsed":"1m","dispatched":[]},
    {"area":"workspace","batch_id":"20260314-real","batch_status":"dead","n_done":0,"n_failed":0,"n_total":1,"elapsed":"2m","dispatched":[]}
  ]
}')

dead_tsv8=$(printf '%s' "$snapshot8" | jq -r '
  (.orchestrators // .orchestrator // [])[] |
  select(.batch_status == "dead" and (.area | type == "string") and .area != "") | .area
' 2>/dev/null)

n_dead8=0
[[ -n "$dead_tsv8" ]] && n_dead8=$(printf '%s\n' "$dead_tsv8" | grep -c .)
assert_eq "null-area dead orch: not counted" "1" "$n_dead8"

test_summary
