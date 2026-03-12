#!/bin/bash
# test-dep-policy.sh — Integration tests for hard/soft dep + cross-area policy
#
# Tests acceptance criteria from issue #90:
#   1. Fenced block and ### Dependencies both parseable via --parse-typed
#   2. Hard dep failed -> blocked-failed-dependency (via orch_unblock)
#   3. Soft dep failed -> pending (via orch_unblock)
#   4. Cross-area dep -> blocked-external (via orch_unblock)
#   5. Cycle found -> only cycle nodes are cycle-isolated (SCC isolation)
#
# Usage: bash test-dep-policy.sh [--verbose]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARSE="$SCRIPT_DIR/parse-dependencies.sh"
HELPERS="$SCRIPT_DIR/orchestrate-helpers.sh"

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

# ──────────────────────────────────────────────
# Mock gh setup
# A temp bin dir with a mock 'gh' binary that outputs the given body.
# ──────────────────────────────────────────────

MOCK_BIN=$(mktemp -d)
trap 'rm -rf "$MOCK_BIN"' EXIT

_setup_mock_gh() {
  # Usage: _setup_mock_gh <body_text>
  # Creates/overwrites the mock gh binary to output body_text for issue view calls.
  local body=$1
  printf '#!/bin/bash\ncat << '"'"'__MOCK_BODY__\n'"'"'\n%s\n'"'"'__MOCK_BODY__\n'"'"'\n' "$body" > "$MOCK_BIN/gh"
  chmod +x "$MOCK_BIN/gh"
}

echo "=== test-dep-policy.sh ==="
echo ""

# ──────────────────────────────────────────────
echo "--- 1. --parse-typed: fenced orchestrator block (via actual script) ---"

FENCED_BODY='## Test issue

```orchestrator
hard: #12, #15
soft: #20
cross-area: server/#30
cross-area soft: client/#5
```'

_setup_mock_gh "$FENCED_BODY"
RESULT=$(PATH="$MOCK_BIN:$PATH" bash "$PARSE" --parse-typed 999 .)

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
echo "--- 2. --parse-typed: ### Dependencies fallback (via actual script) ---"

LEGACY_BODY='## Test issue

### Dependencies

- #42
- #15 (some note)
Closes #7'

_setup_mock_gh "$LEGACY_BODY"
RESULT=$(PATH="$MOCK_BIN:$PATH" bash "$PARSE" --parse-typed 999 .)

HARD=$(echo "$RESULT" | jq -r '.hard | sort | @json')
SOFT=$(echo "$RESULT" | jq -r '.soft | @json')
CROSS_COUNT=$(echo "$RESULT" | jq '.crossArea | length')

_assert_eq "legacy: hard deps [7,15,42]" "$HARD" "[7,15,42]"
_assert_eq "legacy: soft empty" "$SOFT" "[]"
_assert_eq "legacy: crossArea empty" "$CROSS_COUNT" "0"

# ──────────────────────────────────────────────
echo ""
echo "--- 3. --find-sccs: no cycle ---"

SCC=$(bash "$PARSE" --find-sccs '[1,2,3]' '{"2":[1],"3":[2]}')
HAS_CYCLE=$(echo "$SCC" | jq -r '.hasCycle')
SCC_COUNT=$(echo "$SCC" | jq '.sccNodes | length')

_assert_eq "no-cycle: hasCycle=false" "$HAS_CYCLE" "false"
_assert_eq "no-cycle: sccNodes empty" "$SCC_COUNT" "0"

# ──────────────────────────────────────────────
echo ""
echo "--- 4. --find-sccs: cycle isolation (only cycle nodes, not dependents) ---"

# 1->2->3->1 (full cycle), 4 depends on 1 (not in cycle)
SCC=$(bash "$PARSE" --find-sccs '[1,2,3,4]' '{"1":[3],"2":[1],"3":[2],"4":[1]}')
HAS_CYCLE=$(echo "$SCC" | jq -r '.hasCycle')
SCC_NODES=$(echo "$SCC" | jq -r '[.sccNodes[]] | sort | @json')
FOUR_ISOLATED=$(echo "$SCC" | jq -r '.sccNodes | any(. == 4)')

_assert_eq "cycle: hasCycle=true" "$HAS_CYCLE" "true"
_assert_eq "cycle: sccNodes=[1,2,3]" "$SCC_NODES" "[1,2,3]"
_assert_eq "cycle: issue 4 NOT isolated" "$FOUR_ISOLATED" "false"

# ──────────────────────────────────────────────
echo ""
echo "--- 5. --check-cycles backward compat ---"

bash "$PARSE" --check-cycles '[1,2,3]' '{"2":[1],"3":[2]}' \
  && _ok "no-cycle: exit 0" || _fail "no-cycle: exit 0" "exit 1" "exit 0"

bash "$PARSE" --check-cycles '[1,2,3]' '{"1":[3],"2":[1],"3":[2]}' 2>/dev/null \
  && _fail "cycle: exit 1" "exit 0" "exit 1" || _ok "cycle: exit 1"

# ──────────────────────────────────────────────
# orch_unblock integration tests
# Source helpers and use a temp ORCH_BASE to avoid touching real state.
# ──────────────────────────────────────────────

ORCH_BASE=$(mktemp -d)
trap 'rm -rf "$MOCK_BIN" "$ORCH_BASE"' EXIT
TEST_AREA="test-area-$$"
mkdir -p "$ORCH_BASE/$TEST_AREA"

# Source the helpers (sets MONOREPO_ROOT, ORCH_BASE, etc.)
# Override ORCH_BASE immediately after sourcing so tests use the temp dir.
# shellcheck source=/dev/null
source "$HELPERS"
ORCH_BASE_ORIG="$ORCH_BASE"  # already our temp dir (sourcing sets it to $MONOREPO_ROOT/.workspace/orchestrate)
# Re-override ORCH_BASE to point to our temp dir
ORCH_BASE="$ORCH_BASE_ORIG"

_write_state() {
  # Usage: _write_state <json>
  # Writes fake batch state to ORCH_BASE/TEST_AREA/batch.state.json
  mkdir -p "$ORCH_BASE/$TEST_AREA"
  echo "$1" > "$ORCH_BASE/$TEST_AREA/batch.state.json"
}

_read_status() {
  # Usage: _read_status <issue>
  jq -r ".status[\"$1\"]" "$ORCH_BASE/$TEST_AREA/batch.state.json"
}

# ──────────────────────────────────────────────
echo ""
echo "--- 6. orch_unblock: hard dep failed -> blocked-failed-dependency ---"

# Issue 2 depends (hard) on issue 1; issue 1 is failed
_write_state "$(jq -n '{
  "issues": [1, 2],
  "dag": {"2": [1]},
  "dagTypes": {"2": {"1": "hard"}},
  "crossAreaDeps": {},
  "status": {"1": "failed", "2": "blocked"}
}')"

orch_unblock "$TEST_AREA" 1 > /dev/null
STATUS2=$(_read_status 2)
_assert_eq "hard dep failed: issue 2 -> blocked-failed-dependency" "$STATUS2" "blocked-failed-dependency"

# ──────────────────────────────────────────────
echo ""
echo "--- 7. orch_unblock: soft dep failed -> pending ---"

_write_state "$(jq -n '{
  "issues": [1, 2],
  "dag": {"2": [1]},
  "dagTypes": {"2": {"1": "soft"}},
  "crossAreaDeps": {},
  "status": {"1": "failed", "2": "blocked"}
}')"

orch_unblock "$TEST_AREA" 1 > /dev/null
STATUS2=$(_read_status 2)
_assert_eq "soft dep failed: issue 2 -> pending" "$STATUS2" "pending"

# ──────────────────────────────────────────────
echo ""
echo "--- 8. orch_unblock: soft dep completed -> pending ---"

_write_state "$(jq -n '{
  "issues": [1, 2],
  "dag": {"2": [1]},
  "dagTypes": {"2": {"1": "soft"}},
  "crossAreaDeps": {},
  "status": {"1": "completed", "2": "blocked"}
}')"

orch_unblock "$TEST_AREA" 1 > /dev/null
STATUS2=$(_read_status 2)
_assert_eq "soft dep completed: issue 2 -> pending" "$STATUS2" "pending"

# ──────────────────────────────────────────────
echo ""
echo "--- 9. orch_unblock: cross-area hard dep -> blocked-external ---"

_write_state "$(jq -n '{
  "issues": [1, 2],
  "dag": {"2": [1]},
  "dagTypes": {"2": {"1": "soft"}},
  "crossAreaDeps": {"2": [{"area": "server", "issue": 30, "type": "hard"}]},
  "status": {"1": "completed", "2": "blocked"}
}')"

orch_unblock "$TEST_AREA" 1 > /dev/null
STATUS2=$(_read_status 2)
_assert_eq "cross-area hard dep: issue 2 -> blocked-external" "$STATUS2" "blocked-external"

# ──────────────────────────────────────────────
echo ""
echo "--- 10. orch_unblock: soft cross-area dep only -> pending ---"

_write_state "$(jq -n '{
  "issues": [1, 2],
  "dag": {"2": [1]},
  "dagTypes": {},
  "crossAreaDeps": {"2": [{"area": "server", "issue": 30, "type": "soft"}]},
  "status": {"1": "completed", "2": "blocked"}
}')"

orch_unblock "$TEST_AREA" 1 > /dev/null
STATUS2=$(_read_status 2)
_assert_eq "soft cross-area dep: issue 2 -> pending" "$STATUS2" "pending"

# ──────────────────────────────────────────────
echo ""
echo "--- 11. orch_init status: SCC nodes -> cycle-isolated ---"

ISSUES='[1,2,3,4]'
DAG='{"1":[3],"2":[1],"3":[2]}'  # 1->3->2->1 cycle, 4 is free

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

_assert_eq "scc init: issue 1 cycle-isolated" "$(echo "$STATUS" | jq -r '."1"')" "cycle-isolated"
_assert_eq "scc init: issue 2 cycle-isolated" "$(echo "$STATUS" | jq -r '."2"')" "cycle-isolated"
_assert_eq "scc init: issue 3 cycle-isolated" "$(echo "$STATUS" | jq -r '."3"')" "cycle-isolated"
_assert_eq "scc init: issue 4 pending" "$(echo "$STATUS" | jq -r '."4"')" "pending"

# ──────────────────────────────────────────────
echo ""
echo "--- 12. orch_init status: cross-area hard -> blocked-external ---"

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
