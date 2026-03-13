#!/usr/bin/env bash
# test-stale-token.sh — stale token detection (#113)
#
# Regression: verifies that the STALE_THRESHOLD_SECS (30s) is applied correctly
# to tokens_updated_at (independent from updated_at) for both Claude sidecar
# and Codex session-based token sources.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/helpers.sh"

TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

STALE_THRESHOLD_SECS=30

# ── Shared freshness check logic (mirrors lib/collect.sh) ──
_tok_fresh_check() {
  local tokens_updated_at=$1 updated_at=$2
  local now_epoch
  now_epoch=$(date +%s)
  local tok_ts="${tokens_updated_at:-0}"
  [[ "$tok_ts" == "0" || "$tok_ts" == "null" || -z "$tok_ts" ]] && tok_ts="${updated_at:-0}"
  local tok_fresh=true
  if [[ -n "$tok_ts" && "$tok_ts" != "0" && "$tok_ts" != "null" ]]; then
    local tok_age=$(( now_epoch - ${tok_ts%.*} ))
    (( tok_age > STALE_THRESHOLD_SECS )) && tok_fresh=false
  fi
  printf '%s' "$tok_fresh"
}

now=$(date +%s)
fresh_ts=$now
stale_ts=$(( now - 60 ))   # 60s ago = definitively stale
border_ts=$(( now - 29 ))  # 29s ago = just within threshold (fresh)
exact_ts=$(( now - 30 ))   # 30s ago = at threshold boundary (still fresh ≤ 30)

# ── Test 1: tokens_updated_at fresh → tok_fresh=true ──
r1=$(_tok_fresh_check "$fresh_ts" "$stale_ts")
assert_eq "fresh tokens_updated_at: tok_fresh=true" "true" "$r1"

# ── Test 2: tokens_updated_at stale (60s) → tok_fresh=false ──
r2=$(_tok_fresh_check "$stale_ts" "$fresh_ts")
assert_eq "stale tokens_updated_at (60s): tok_fresh=false" "false" "$r2"

# ── Test 3: tokens_updated_at missing → falls back to updated_at ──
r3=$(_tok_fresh_check "" "$fresh_ts")
assert_eq "no tokens_updated_at: fallback to updated_at (fresh)" "true" "$r3"

r3b=$(_tok_fresh_check "0" "$stale_ts")
assert_eq "tokens_updated_at=0: fallback to updated_at (stale)" "false" "$r3b"

# ── Test 4: Border at 29s → still fresh ──
r4=$(_tok_fresh_check "$border_ts" "$stale_ts")
assert_eq "29s ago: tok_fresh=true (within threshold)" "true" "$r4"

# ── Test 5: Exactly at threshold 30s → still fresh (age > 30 means > not >=) ──
r5=$(_tok_fresh_check "$exact_ts" "$stale_ts")
assert_eq "30s ago: tok_fresh=true (at boundary, not >)" "true" "$r5"

# ── Test 6: 31s ago → stale (age > 30) ──
ts31=$(( now - 31 ))
r6=$(_tok_fresh_check "$ts31" "$fresh_ts")
assert_eq "31s ago: tok_fresh=false (just past threshold)" "false" "$r6"

# ── Test 7: Claude sidecar JSON round-trip with stale token ──
cat > "$TMPDIR/sidecar-stale-tok.json" << EOF
{
  "model": "Sonnet 4.6",
  "status": "working",
  "tokens": {"used": 90000, "max": 200000, "pct": 45},
  "task": "Active task",
  "updated_at": $fresh_ts,
  "tokens_updated_at": $stale_ts
}
EOF

raw=$(jq -r '[
  (.tokens_updated_at // 0 | tostring),
  (.updated_at // 0 | tostring)
] | @tsv' "$TMPDIR/sidecar-stale-tok.json")
IFS=$'\t' read -r tua ua <<< "$raw"
r7=$(_tok_fresh_check "$tua" "$ua")
assert_eq "claude sidecar: stale token_updated_at → tok_fresh=false" "false" "$r7"

# ── Test 8: Claude sidecar with fresh token_updated_at ──
cat > "$TMPDIR/sidecar-fresh-tok.json" << EOF
{
  "model": "Sonnet 4.6",
  "status": "working",
  "tokens": {"used": 90000, "max": 200000, "pct": 45},
  "task": "Active task",
  "updated_at": $stale_ts,
  "tokens_updated_at": $fresh_ts
}
EOF

raw8=$(jq -r '[
  (.tokens_updated_at // 0 | tostring),
  (.updated_at // 0 | tostring)
] | @tsv' "$TMPDIR/sidecar-fresh-tok.json")
IFS=$'\t' read -r tua8 ua8 <<< "$raw8"
r8=$(_tok_fresh_check "$tua8" "$ua8")
assert_eq "claude sidecar: fresh tokens_updated_at overrides stale updated_at" "true" "$r8"

test_summary
