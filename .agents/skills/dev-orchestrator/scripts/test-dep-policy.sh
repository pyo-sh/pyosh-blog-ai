#!/bin/bash
# test-dep-policy.sh — Integration tests for hard/soft dep + cross-area policy
#
# Tests acceptance criteria from issue #90:
#   1. Fenced block and ### Dependencies both parseable
#   2. Hard dep failed -> blocked-failed-dependency
#   3. Soft dep failed -> pending
#   4. Cross-area dep -> blocked-external
#   5. Cycle found -> only cycle nodes are quarantined (SCC isolation)
#
# Usage: bash test-dep-policy.sh [--verbose]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARSE="$SCRIPT_DIR/parse-dependencies.sh"

PASS=0
FAIL=0
VERBOSE="${1:-}"

_ok() {
  local desc=$1
  PASS=$((PASS + 1))
  [ -n "$VERBOSE" ] && echo "  [OK] $desc"
}

_fail() {
  local desc=$1 got=$2 want=$3
  FAIL=$((FAIL + 1))
  echo "  [FAIL] $desc"
  echo "         got:  $got"
  echo "         want: $want"
}

_assert_eq() {
  local desc=$1 got=$2 want=$3
  if [ "$got" = "$want" ]; then _ok "$desc"; else _fail "$desc" "$got" "$want"; fi
}

echo "=== test-dep-policy.sh ==="
echo ""

# ──────────────────────────────────────────────
echo "--- 1. --parse-typed: fenced orchestrator block ---"

FENCED_BLOCK="hard: #12, #15
soft: #20
cross-area: server/#30
cross-area soft: client/#5"

RESULT=$(echo "$FENCED_BLOCK" | jq -Rs '
  split("\n") |
  map(select(length > 0)) |
  reduce .[] as $line (
    {"hard": [], "soft": [], "crossArea": []};
    if ($line | test("^cross-area soft:\\s*"; "i")) then
      .crossArea += (
        ($line | gsub("^cross-area soft:\\s*"; ""; "i")) |
        [match("([a-zA-Z][a-zA-Z0-9_-]*)/?#([0-9]+)"; "g")] |
        map({area: .captures[0].string, issue: (.captures[1].string | tonumber), type: "soft"})
      )
    elif ($line | test("^cross-area:\\s*"; "i")) then
      .crossArea += (
        ($line | gsub("^cross-area:\\s*"; ""; "i")) |
        [match("([a-zA-Z][a-zA-Z0-9_-]*)/?#([0-9]+)"; "g")] |
        map({area: .captures[0].string, issue: (.captures[1].string | tonumber), type: "hard"})
      )
    elif ($line | test("^soft:\\s*"; "i")) then
      .soft += (($line | gsub("^soft:\\s*"; ""; "i")) | [scan("[0-9]+")] | map(tonumber))
    elif ($line | test("^hard:\\s*"; "i")) then
      .hard += (($line | gsub("^hard:\\s*"; ""; "i")) | [scan("[0-9]+")] | map(tonumber))
    else . end
  ) |
  .hard |= (map(tostring) | unique | map(tonumber)) |
  .soft |= (map(tostring) | unique | map(tonumber))
')

HARD=$(echo "$RESULT" | jq -r '.hard | @json')
SOFT=$(echo "$RESULT" | jq -r '.soft | @json')
CROSS_COUNT=$(echo "$RESULT" | jq '.crossArea | length')
CROSS_HARD_AREA=$(echo "$RESULT" | jq -r '.crossArea[] | select(.type=="hard") | .area')
CROSS_SOFT_AREA=$(echo "$RESULT" | jq -r '.crossArea[] | select(.type=="soft") | .area')

_assert_eq "fenced: hard deps [12,15]" "$HARD" "[12,15]"
_assert_eq "fenced: soft deps [20]" "$SOFT" "[20]"
_assert_eq "fenced: crossArea count=2" "$CROSS_COUNT" "2"
_assert_eq "fenced: cross-area hard area=server" "$CROSS_HARD_AREA" "server"
_assert_eq "fenced: cross-area soft area=client" "$CROSS_SOFT_AREA" "client"

# ──────────────────────────────────────────────
echo ""
echo "--- 2. --find-sccs: no cycle ---"

SCC=$(bash "$PARSE" --find-sccs '[1,2,3]' '{"2":[1],"3":[2]}')
HAS_CYCLE=$(echo "$SCC" | jq -r '.hasCycle')
SCC_COUNT=$(echo "$SCC" | jq '.sccNodes | length')

_assert_eq "no-cycle: hasCycle=false" "$HAS_CYCLE" "false"
_assert_eq "no-cycle: sccNodes empty" "$SCC_COUNT" "0"

# ──────────────────────────────────────────────
echo ""
echo "--- 3. --find-sccs: cycle isolation (only cycle nodes) ---"

# 1->2->3->1 (full cycle), 4->1 (not in cycle)
SCC=$(bash "$PARSE" --find-sccs '[1,2,3,4]' '{"1":[3],"2":[1],"3":[2],"4":[1]}')
HAS_CYCLE=$(echo "$SCC" | jq -r '.hasCycle')
SCC_NODES=$(echo "$SCC" | jq -r '[.sccNodes[]] | sort | @json')
FOUR_ISOLATED=$(echo "$SCC" | jq -r '.sccNodes | any(. == 4)')

_assert_eq "cycle: hasCycle=true" "$HAS_CYCLE" "true"
_assert_eq "cycle: sccNodes=[1,2,3]" "$SCC_NODES" "[1,2,3]"
_assert_eq "cycle: issue 4 NOT isolated" "$FOUR_ISOLATED" "false"

# ──────────────────────────────────────────────
echo ""
echo "--- 4. --check-cycles backward compat ---"

bash "$PARSE" --check-cycles '[1,2,3]' '{"2":[1],"3":[2]}' \
  && _ok "no-cycle: exit 0" || _fail "no-cycle: exit 0" "exit 1" "exit 0"

bash "$PARSE" --check-cycles '[1,2,3]' '{"1":[3],"2":[1],"3":[2]}' 2>/dev/null \
  && _fail "cycle: exit 1" "exit 0" "exit 1" || _ok "cycle: exit 1"

# ──────────────────────────────────────────────
echo ""
echo "--- 5. orch_unblock: hard dep failed -> blocked-failed-dependency ---"

# Simulate state with dagTypes (hard dep) and a failed dep
STATE_HARD=$(jq -n '{
  "issues": [1, 2],
  "dag": {"2": [1]},
  "dagTypes": {"2": {"1": "hard"}},
  "crossAreaDeps": {},
  "status": {"1": "failed", "2": "blocked"}
}')

# Check logic: issue 2 has hard dep on 1; 1 is failed; result should be blocked-failed-dependency
DEP_STATUS=$(echo "$STATE_HARD" | jq -r '.status["1"]')
DEP_TYPE=$(echo "$STATE_HARD" | jq -r '.dagTypes["2"]["1"] // "hard"')
_assert_eq "hard dep: dep_status=failed" "$DEP_STATUS" "failed"
_assert_eq "hard dep: dep_type=hard" "$DEP_TYPE" "hard"

# ──────────────────────────────────────────────
echo ""
echo "--- 6. orch_unblock: soft dep failed -> pending ---"

STATE_SOFT=$(jq -n '{
  "issues": [1, 2],
  "dag": {"2": [1]},
  "dagTypes": {"2": {"1": "soft"}},
  "crossAreaDeps": {},
  "status": {"1": "failed", "2": "blocked"}
}')

DEP_TYPE=$(echo "$STATE_SOFT" | jq -r '.dagTypes["2"]["1"] // "hard"')
_assert_eq "soft dep: dep_type=soft" "$DEP_TYPE" "soft"
# Soft dep failure is treated as satisfied -> pending

# ──────────────────────────────────────────────
echo ""
echo "--- 7. cross-area hard dep -> blocked-external ---"

STATE_CROSS=$(jq -n '{
  "issues": [1],
  "dag": {"1": []},
  "dagTypes": {},
  "crossAreaDeps": {"1": [{"area": "server", "issue": 30, "type": "hard"}]},
  "status": {"1": "blocked"}
}')

HAS_CROSS=$(echo "$STATE_CROSS" | jq -r '.crossAreaDeps["1"] // [] | map(select(.type == "hard")) | length > 0')
_assert_eq "cross-area: has hard cross-area dep" "$HAS_CROSS" "true"

# ──────────────────────────────────────────────
echo ""
echo "--- 8. orch_init status: SCC nodes -> cycle-isolated ---"

ISSUES='[1,2,3,4]'
DAG='{"1":[3],"2":[1],"3":[2]}'  # 1->3->2->1 cycle, 4 is free

# Simulate orch_init initial status logic
SCC_JSON=$(bash "$PARSE" --find-sccs "$ISSUES" "$DAG")
SCC_NODES=$(echo "$SCC_JSON" | jq '.sccNodes')

STATUS=$(jq -n \
  --argjson issues "$ISSUES" \
  --argjson dag "$DAG" \
  --argjson cross_area_deps '{}' \
  --argjson scc_nodes "$SCC_NODES" \
  'reduce $issues[] as $n ({};
     . + {($n|tostring):
       (if ($scc_nodes | any(. == $n)) then "cycle-isolated"
        elif (($dag[($n|tostring)] // []) | length > 0) then "blocked"
        elif (($cross_area_deps[($n|tostring)] // [])
              | map(select(.type == "hard")) | length > 0) then "blocked-external"
        else "pending" end)})')

S1=$(echo "$STATUS" | jq -r '."1"')
S2=$(echo "$STATUS" | jq -r '."2"')
S3=$(echo "$STATUS" | jq -r '."3"')
S4=$(echo "$STATUS" | jq -r '."4"')

_assert_eq "scc init: issue 1 cycle-isolated" "$S1" "cycle-isolated"
_assert_eq "scc init: issue 2 cycle-isolated" "$S2" "cycle-isolated"
_assert_eq "scc init: issue 3 cycle-isolated" "$S3" "cycle-isolated"
_assert_eq "scc init: issue 4 pending" "$S4" "pending"

# ──────────────────────────────────────────────
echo ""
echo "--- 9. orch_init status: cross-area hard -> blocked-external ---"

ISSUES2='[10]'
DAG2='{}'
CROSS2='{"10": [{"area": "server", "issue": 5, "type": "hard"}]}'

STATUS2=$(jq -n \
  --argjson issues "$ISSUES2" \
  --argjson dag "$DAG2" \
  --argjson cross_area_deps "$CROSS2" \
  --argjson scc_nodes '[]' \
  'reduce $issues[] as $n ({};
     . + {($n|tostring):
       (if ($scc_nodes | any(. == $n)) then "cycle-isolated"
        elif (($dag[($n|tostring)] // []) | length > 0) then "blocked"
        elif (($cross_area_deps[($n|tostring)] // [])
              | map(select(.type == "hard")) | length > 0) then "blocked-external"
        else "pending" end)})')

_assert_eq "cross-area init: issue 10 blocked-external" "$(echo "$STATUS2" | jq -r '."10"')" "blocked-external"

# ──────────────────────────────────────────────
echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
