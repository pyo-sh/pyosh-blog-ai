#!/usr/bin/env bash
# tools/agent-tracker/tests/helpers.sh
# Test assertion utilities for fixture-based regression tests.

_TESTS_RUN=0
_TESTS_FAILED=0

assert_eq() {
  local desc=$1 expected=$2 actual=$3
  _TESTS_RUN=$(( _TESTS_RUN + 1 ))
  if [[ "$expected" == "$actual" ]]; then
    printf '  \033[38;5;71m✓\033[0m %s\n' "$desc"
  else
    printf '  \033[38;5;132m✗\033[0m %s\n' "$desc"
    printf '    expected: %s\n' "$expected"
    printf '    actual:   %s\n' "$actual"
    _TESTS_FAILED=$(( _TESTS_FAILED + 1 ))
  fi
}

assert_ne() {
  local desc=$1 not_expected=$2 actual=$3
  _TESTS_RUN=$(( _TESTS_RUN + 1 ))
  if [[ "$not_expected" != "$actual" ]]; then
    printf '  \033[38;5;71m✓\033[0m %s\n' "$desc"
  else
    printf '  \033[38;5;132m✗\033[0m %s\n' "$desc"
    printf '    should not be: %s\n' "$not_expected"
    _TESTS_FAILED=$(( _TESTS_FAILED + 1 ))
  fi
}

assert_contains() {
  local desc=$1 needle=$2 haystack=$3
  _TESTS_RUN=$(( _TESTS_RUN + 1 ))
  if [[ "$haystack" == *"$needle"* ]]; then
    printf '  \033[38;5;71m✓\033[0m %s\n' "$desc"
  else
    printf '  \033[38;5;132m✗\033[0m %s\n' "$desc"
    printf '    expected to contain: %s\n' "$needle"
    printf '    actual: %s\n' "$haystack"
    _TESTS_FAILED=$(( _TESTS_FAILED + 1 ))
  fi
}

assert_json_field() {
  local desc=$1 json=$2 field=$3 expected=$4
  local actual
  actual=$(printf '%s' "$json" | jq -r "$field" 2>/dev/null)
  assert_eq "$desc" "$expected" "$actual"
}

test_summary() {
  local passed=$(( _TESTS_RUN - _TESTS_FAILED ))
  if (( _TESTS_FAILED == 0 )); then
    printf '  \033[38;5;71m%d/%d tests passed\033[0m\n' "$passed" "$_TESTS_RUN"
  else
    printf '  \033[38;5;132m%d/%d tests passed (%d failed)\033[0m\n' "$passed" "$_TESTS_RUN" "$_TESTS_FAILED"
  fi
  return "$_TESTS_FAILED"
}
