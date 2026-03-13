#!/usr/bin/env bash
# test-sidecar-partial-write.sh — sidecar partial write defense (#113)
#
# Regression: a partially written sidecar (truncated JSON) must not crash the
# collector and must produce status="fault" so the pane is visibly flagged rather
# than silently disappearing from the dashboard.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/helpers.sh"

TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

# The jq expression used in _collect_claude_pane (lib/collect.sh)
JQ_EXPR='[
  (.model // "unknown"),
  (.status // "idle"),
  (.tokens.pct // 0 | tostring),
  (.tokens.used // 0 | tostring),
  (.tokens.max // 0 | tostring),
  ((.task // "-") | gsub("[\\n\\r]"; " ") | gsub("  +"; " ") | @base64),
  ((.activity // "") | gsub("[\\n\\r]"; " ") | gsub("  +"; " ") | @base64),
  (.updated_at // 0 | tostring),
  (.tokens_updated_at // 0 | tostring)
] | join("\u001e")'

# ── Test 1: Truncated JSON (partial write mid-object) ──
# Simulates a write that was interrupted, leaving an incomplete JSON object.
printf '{"status":"working","model":"Sonnet 4.6","task":"Fix bu' \
  > "$TMPDIR/partial.json"

raw=$(jq -r "$JQ_EXPR" "$TMPDIR/partial.json" 2>/dev/null) || true
if [[ -z "$raw" ]]; then
  status="fault"
fi
assert_eq "partial write: jq fails cleanly" "fault" "$status"

# ── Test 2: Empty file (zero-byte write, then rename) ──
printf '' > "$TMPDIR/zero.json"
raw2=$(jq -r "$JQ_EXPR" "$TMPDIR/zero.json" 2>/dev/null) || true
if [[ -z "$raw2" ]]; then
  status2="fault"
fi
assert_eq "zero-byte file: jq fails cleanly" "fault" "$status2"

# ── Test 3: Binary garbage (filesystem corruption) ──
printf '\x00\x01\xff\xfe{"bad' > "$TMPDIR/garbage.json"
raw3=$(jq -r "$JQ_EXPR" "$TMPDIR/garbage.json" 2>/dev/null) || true
if [[ -z "$raw3" ]]; then
  status3="fault"
fi
assert_eq "binary garbage: jq fails cleanly" "fault" "$status3"

# ── Test 4: Valid sidecar round-trips correctly ──
now=$(date +%s)
cat > "$TMPDIR/valid.json" << EOF
{
  "model": "Opus 4.6",
  "status": "working",
  "tokens": {"used": 80000, "max": 200000, "pct": 40},
  "task": "Fix the parser",
  "activity": "Edit: main.py",
  "updated_at": $now,
  "tokens_updated_at": $now
}
EOF

raw4=$(jq -r "$JQ_EXPR" "$TMPDIR/valid.json" 2>/dev/null)
if [[ -n "$raw4" ]]; then
  IFS=$'\x1e' read -r model4 status4 pct4 used4 total4 task_b64 act_b64 ua4 tua4 <<< "$raw4"
  task4=$(printf '%s' "$task_b64" | base64 -d 2>/dev/null)
fi

assert_eq "valid sidecar: no fault" "working" "$status4"
assert_eq "valid sidecar: model" "Opus 4.6" "$model4"
assert_eq "valid sidecar: task decoded" "Fix the parser" "$task4"
assert_eq "valid sidecar: tok_used" "80000" "$used4"

test_summary
