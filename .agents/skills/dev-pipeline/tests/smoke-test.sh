#!/usr/bin/env bash
# Smoke tests for pipeline-helpers.sh
# Run from monorepo root: bash .agents/skills/dev-pipeline/tests/smoke-test.sh
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd -P)"
source "$ROOT/.agents/skills/dev-pipeline/scripts/pipeline-helpers.sh"

PASS=0
FAIL=0
_ok() { PASS=$((PASS+1)); printf '  PASS: %s\n' "$1"; }
_fail() { FAIL=$((FAIL+1)); printf '  FAIL: %s\n' "$1"; }

echo "=== pipeline smoke tests ==="

# --- 1. State write/read/update ---
echo "--- 1. state write/read/update ---"
_TEST_AREA="smoke-$$"
_TEST_ISSUE="999"
pipeline_init "$_TEST_AREA"
_STATE_FILE="$(pipeline_state_path "$_TEST_ISSUE" "$_TEST_AREA")"

_INITIAL='{"version":2,"issue":999,"area":"smoke","step":"build","pr":0,"branch":"","reviewJob":{"runId":"","status":"idle","startedAt":null,"finishedAt":null,"tool":"","model":""},"transitionLog":[],"lastReviewId":0,"lastCommitSha":"","skipReview":false,"reviewResolveRound":0,"maxReviewResolveRounds":5,"stageRetries":{"build":0,"review_dispatch":0,"review_wait":0,"review_process":0,"resolve":0,"merge":0},"maxStageRetries":3}'
pipeline_state_write "$_TEST_ISSUE" "$_TEST_AREA" "$_INITIAL"
_READ=$(pipeline_state_read "$_TEST_ISSUE" "$_TEST_AREA")
[ "$(printf '%s' "$_READ" | jq -r '.step')" = "build" ] && _ok "state write+read" || _fail "state write+read"

pipeline_state_update "$_TEST_ISSUE" "$_TEST_AREA" '.step = "review_dispatch"'
_STEP=$(pipeline_state_read "$_TEST_ISSUE" "$_TEST_AREA" | jq -r '.step')
[ "$_STEP" = "review_dispatch" ] && _ok "state update step" || _fail "state update step"

# --- 2. pipeline_log_transition ---
echo "--- 2. pipeline_log_transition ---"
pipeline_log_transition "$_TEST_ISSUE" "$_TEST_AREA" "build" "review_dispatch" "test"
_TLOG=$(pipeline_state_read "$_TEST_ISSUE" "$_TEST_AREA" | jq -r '.transitionLog | length')
[ "$_TLOG" -ge 1 ] && _ok "log_transition appends" || _fail "log_transition appends"

# --- 3. pipeline_parse_review_body - valid ---
echo "--- 3. pipeline_parse_review_body ---"
_REVIEW_BODY="## Review Summary
**Verdict**: Request changes

### Critical
1. **Bad function** \`foo.sh\`
   description

### Warning
1. Minor issue

### Suggestions
None"
_COUNTS=$(pipeline_parse_review_body "$_REVIEW_BODY")
[ "$(printf '%s' "$_COUNTS" | jq -r '.critical')" = "1" ] && _ok "parse: critical=1" || _fail "parse: critical=1"
[ "$(printf '%s' "$_COUNTS" | jq -r '.warning')" = "1" ] && _ok "parse: warning=1" || _fail "parse: warning=1"
[ "$(printf '%s' "$_COUNTS" | jq -r '.suggestion')" = "0" ] && _ok "parse: suggestion=0" || _fail "parse: suggestion=0"

# --- 4. pipeline_parse_review_body - bad format ---
echo "--- 4. parse_review_body bad format ---"
if pipeline_parse_review_body "no header here" 2>/dev/null; then
  _fail "parse bad format should return 1"
else
  _ok "parse bad format returns non-zero"
fi

# --- 5. Cleanup ---
echo "--- 5. cleanup ---"
pipeline_state_delete "$_TEST_ISSUE" "$_TEST_AREA"
[ ! -f "$_STATE_FILE" ] && _ok "state delete" || _fail "state delete"
rmdir "$(pipeline_state_dir "$_TEST_AREA")" 2>/dev/null || true
rmdir "$(pipeline_log_dir "$_TEST_AREA")" 2>/dev/null || true

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
[ "$FAIL" -eq 0 ]
