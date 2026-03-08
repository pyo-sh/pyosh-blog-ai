#!/usr/bin/env bash
# test-exit-code.sh — Verify exit code preservation (#72 item 1)
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/helpers.sh"

TRACKER="$SCRIPT_DIR/../agent-tracker.sh"

# Test: invalid interval (zero) returns non-zero exit code
ec_zero=0
bash "$TRACKER" -i 0 >/dev/null 2>/dev/null || ec_zero=$?
assert_ne "invalid interval (0): exit code not 0" "0" "$ec_zero"

# Test: unknown option returns non-zero
ec_unknown=0
bash "$TRACKER" -z 2>/dev/null || ec_unknown=$?
assert_ne "unknown option (-z): exit code not 0" "0" "$ec_unknown"

# Test: help flag returns 0 (intentional)
ec_help=0
bash "$TRACKER" -h >/dev/null 2>/dev/null || ec_help=$?
assert_eq "help flag (-h): exit code 0" "0" "$ec_help"

test_summary
