#!/usr/bin/env bash
# test-claude-parse.sh — Verify Claude sidecar parsing (#72 items 3, 5, 6)
# Tests the jq extraction + @tsv protocol used in lib/collect.sh
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/helpers.sh"

TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

# The jq expression used in _collect_claude_pane (lib/collect.sh)
JQ_EXPR='[
  (.model // "Claude"),
  (.status // "idle"),
  (.tokens.pct // 0 | tostring),
  ((.tokens.used // 0) / 1000 | floor | tostring),
  ((.task // "-") | gsub("[\\n\\t\\r]"; " ") | gsub("  +"; " ")),
  ((.activity // "") | gsub("[\\n\\t\\r]"; " ") | gsub("  +"; " ")),
  (.updated_at // 0 | tostring)
] | @tsv'

# ── Test 1: Normal sidecar ──
cat > "$TMPDIR/normal.json" << 'EOF'
{
  "model": "Sonnet 4.6",
  "status": "working",
  "tokens": {"pct": 45, "used": 90000},
  "task": "Fix the parser bug",
  "activity": "Edit: file.ts",
  "updated_at": 9999999999
}
EOF

raw=$(jq -r "$JQ_EXPR" "$TMPDIR/normal.json")
IFS=$'\t' read -r model status pct tok_k task activity updated_at <<< "$raw"
assert_eq "normal: model" "Sonnet 4.6" "$model"
assert_eq "normal: status" "working" "$status"
assert_eq "normal: pct" "45" "$pct"
assert_eq "normal: tok_k" "90" "$tok_k"
assert_eq "normal: task" "Fix the parser bug" "$task"
assert_eq "normal: activity" "Edit: file.ts" "$activity"

# ── Test 2: Multiline task/activity (#72 item 3) ──
cat > "$TMPDIR/multiline.json" << 'EOF'
{
  "model": "Claude",
  "status": "working",
  "tokens": {"pct": 20, "used": 40000},
  "task": "Line one\nLine two\nLine three",
  "activity": "Bash: echo \"hello\nworld\"",
  "updated_at": 9999999999
}
EOF

raw=$(jq -r "$JQ_EXPR" "$TMPDIR/multiline.json")
IFS=$'\t' read -r model status pct tok_k task activity updated_at <<< "$raw"
assert_eq "multiline: task normalized to single line" "Line one Line two Line three" "$task"
assert_eq "multiline: activity normalized" 'Bash: echo "hello world"' "$activity"
assert_eq "multiline: model preserved" "Claude" "$model"
assert_eq "multiline: status preserved" "working" "$status"

# ── Test 3: Task with tabs ──
cat > "$TMPDIR/tabs.json" << 'EOF'
{
  "model": "Claude",
  "status": "working",
  "tokens": {"pct": 10, "used": 20000},
  "task": "col1\tcol2\tcol3",
  "activity": "",
  "updated_at": 9999999999
}
EOF

raw=$(jq -r "$JQ_EXPR" "$TMPDIR/tabs.json")
IFS=$'\t' read -r model status pct tok_k task activity updated_at <<< "$raw"
assert_eq "tabs: task tabs replaced with spaces" "col1 col2 col3" "$task"

# ── Test 4: Stale sidecar detection ──
cat > "$TMPDIR/stale.json" << 'EOF'
{
  "model": "Claude",
  "status": "working",
  "tokens": {"pct": 30, "used": 60000},
  "task": "Old task",
  "activity": "Old activity",
  "updated_at": 1000000000
}
EOF

raw=$(jq -r "$JQ_EXPR" "$TMPDIR/stale.json")
IFS=$'\t' read -r model status pct tok_k task activity updated_at <<< "$raw"
# jq returns raw status; stale detection is done in bash
assert_eq "stale: jq returns raw status" "working" "$status"
# Simulate stale check
now_epoch=$(date +%s)
age=$(( now_epoch - ${updated_at%.*} ))
if (( age > 30 )); then
  status="idle"
  activity=""
fi
assert_eq "stale: status reset to idle" "idle" "$status"
assert_eq "stale: activity cleared" "" "$activity"

# ── Test 5: Empty/missing fields ──
cat > "$TMPDIR/minimal.json" << 'EOF'
{}
EOF

raw=$(jq -r "$JQ_EXPR" "$TMPDIR/minimal.json")
IFS=$'\t' read -r model status pct tok_k task activity updated_at <<< "$raw"
assert_eq "minimal: model defaults to Claude" "Claude" "$model"
assert_eq "minimal: status defaults to idle" "idle" "$status"
assert_eq "minimal: pct defaults to 0" "0" "$pct"
assert_eq "minimal: tok_k defaults to 0" "0" "$tok_k"
assert_eq "minimal: task defaults to dash" "-" "$task"

# ── Test 6: jq failure on invalid JSON produces unknown status ──
echo "not json" > "$TMPDIR/invalid.json"
raw=$(jq -r "$JQ_EXPR" "$TMPDIR/invalid.json" 2>/dev/null) || true
if [[ -z "$raw" ]]; then
  status="unknown"
fi
assert_eq "invalid json: status becomes unknown" "unknown" "$status"

test_summary
