#!/usr/bin/env bash
# tools/agent-tracker/tests/run-tests.sh
# Fixture-based regression test runner for agent-tracker.
#
# Usage: bash tools/agent-tracker/tests/run-tests.sh

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

printf '\n══ agent-tracker regression tests ══\n'

failures=0

for test_file in "$SCRIPT_DIR"/test-*.sh; do
  [[ -f "$test_file" ]] || continue
  printf '\n── %s ──\n' "$(basename "$test_file")"
  if bash "$test_file"; then
    :
  else
    (( failures += $? ))
  fi
done

printf '\n══ Done: '
if (( failures == 0 )); then
  printf '\033[38;5;71mall tests passed\033[0m ══\n'
else
  printf '\033[38;5;132m%d test(s) failed\033[0m ══\n' "$failures"
fi
exit "$failures"
