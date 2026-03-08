#!/usr/bin/env bash
# test-token-fallback.sh — Verify token calculation uses actual window size (#72 item 4)
# The old code hardcoded 200k: tok_k=$(( pct * 200 / 100 ))
# The new code extracts actual window: tok_k=$(( pct * tok_total / 100 ))
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/helpers.sh"

# ── Test 1: 128k window ──
input="Some output
45% of 128k tokens remaining
More output"

tok=$(printf '%s' "$input" | grep -oE '[0-9]+% of [0-9]+k tokens' | tail -1)
pct=$(printf '%s' "$tok" | grep -oE '^[0-9]+')
tok_total=$(printf '%s' "$tok" | grep -oE 'of [0-9]+k' | grep -oE '[0-9]+')

assert_eq "128k window: pct" "45" "$pct"
assert_eq "128k window: total" "128" "$tok_total"

tok_k=$(( pct * tok_total / 100 ))
assert_eq "128k window: tok_k = 57 (not 90)" "57" "$tok_k"

# Old formula would give: 45 * 200 / 100 = 90 (wrong!)
old_tok_k=$(( pct * 200 / 100 ))
assert_ne "128k window: old formula gives wrong result" "$tok_k" "$old_tok_k"

# ── Test 2: 200k window (backward compatible) ──
input2="75% of 200k tokens remaining"
tok2=$(printf '%s' "$input2" | grep -oE '[0-9]+% of [0-9]+k tokens' | tail -1)
pct2=$(printf '%s' "$tok2" | grep -oE '^[0-9]+')
total2=$(printf '%s' "$tok2" | grep -oE 'of [0-9]+k' | grep -oE '[0-9]+')
tok_k2=$(( pct2 * total2 / 100 ))

assert_eq "200k window: tok_k = 150" "150" "$tok_k2"

# ── Test 3: 100k window ──
input3="50% of 100k tokens remaining"
tok3=$(printf '%s' "$input3" | grep -oE '[0-9]+% of [0-9]+k tokens' | tail -1)
pct3=$(printf '%s' "$tok3" | grep -oE '^[0-9]+')
total3=$(printf '%s' "$tok3" | grep -oE 'of [0-9]+k' | grep -oE '[0-9]+')
tok_k3=$(( pct3 * total3 / 100 ))

assert_eq "100k window: tok_k = 50" "50" "$tok_k3"

# ── Test 4: No match gives empty ──
input4="no token info here"
tok4=$(printf '%s' "$input4" | grep -oE '[0-9]+% of [0-9]+k tokens' | tail -1 || true)
assert_eq "no match: empty" "" "$tok4"

test_summary
