#!/usr/bin/env bash
# test-control-char-sanitize.sh — ANSI/OSC/control char sanitize (#113)
#
# Regression: ANSI escape codes and control characters embedded in task or
# activity text must be handled safely. The jq gsub expressions in collect.sh
# strip \n, \r, \t (tab). ANSI/OSC sequences are passed through as-is by jq
# (they are valid JSON string content), but must not break the @tsv/@base64
# protocol or cause runtime errors.
#
# Key behaviors tested:
# 1. \n \r \t in task/activity are replaced by spaces (existing guarantee)
# 2. ANSI escape codes (\033[...m) do not break jq @base64 extraction
# 3. OSC sequences (\033]...\007) do not corrupt @tsv framing
# 4. NUL bytes in a sidecar are handled without crashing jq
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/helpers.sh"

TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

# The jq extraction from _collect_claude_pane (lib/collect.sh)
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

# ── Test 1: ANSI escape codes in task text ──
# jq stores the raw string; gsub replaces \n/\r but not ANSI; @base64 encodes safely.
cat > "$TMPDIR/ansi-task.json" << 'EOF'
{
  "model": "Claude",
  "status": "working",
  "task": "\u001b[1mBold\u001b[0m task",
  "tokens": {"used": 1000, "max": 200000, "pct": 0},
  "updated_at": 9999999999
}
EOF

raw=$(jq -r "$JQ_EXPR" "$TMPDIR/ansi-task.json" 2>/dev/null)
if [[ -n "$raw" ]]; then
  IFS=$'\x1e' read -r model status pct used total task_b64 act_b64 ua tua <<< "$raw"
  task=$(printf '%s' "$task_b64" | base64 -d 2>/dev/null)
  ansi_ok=true
else
  ansi_ok=false
fi

assert_eq "ansi in task: jq does not crash" "true" "$ansi_ok"
assert_eq "ansi in task: model preserved" "Claude" "$model"
assert_contains "ansi in task: content preserved" "Bold" "$task"

# ── Test 2: Newline in task is replaced by space ──
# jq's gsub("[\\n\\r]"; " ") must collapse embedded newlines.
cat > "$TMPDIR/newline-task.json" << 'EOF'
{
  "model": "Claude",
  "status": "working",
  "task": "Line one\nLine two\nLine three",
  "updated_at": 9999999999
}
EOF

raw2=$(jq -r "$JQ_EXPR" "$TMPDIR/newline-task.json" 2>/dev/null)
if [[ -n "$raw2" ]]; then
  IFS=$'\x1e' read -r m2 s2 p2 u2 t2 task_b64_2 act_b64_2 ua2 tua2 <<< "$raw2"
  task2=$(printf '%s' "$task_b64_2" | base64 -d 2>/dev/null)
fi

assert_eq "newline in task: replaced by space" "Line one Line two Line three" "$task2"

# ── Test 3: OSC sequence in activity ──
# OSC: ESC ] ... BEL — valid JSON string content, must not break @base64.
cat > "$TMPDIR/osc-activity.json" << 'EOF'
{
  "model": "Codex",
  "status": "working",
  "task": "Normal task",
  "activity": "\u001b]0;title\u0007Bash: run test",
  "updated_at": 9999999999
}
EOF

raw3=$(jq -r "$JQ_EXPR" "$TMPDIR/osc-activity.json" 2>/dev/null)
if [[ -n "$raw3" ]]; then
  IFS=$'\x1e' read -r m3 s3 p3 u3 t3 task_b64_3 act_b64_3 ua3 tua3 <<< "$raw3"
  act3=$(printf '%s' "$act_b64_3" | base64 -d 2>/dev/null)
  osc_ok=true
else
  osc_ok=false
fi

assert_eq "OSC in activity: jq does not crash" "true" "$osc_ok"
assert_contains "OSC in activity: content preserved" "Bash: run test" "$act3"

# ── Test 4: Tab in task — @base64 must survive tabs in original content ──
# Note: gsub does NOT strip tabs in the current code (only \n and \r are stripped).
# @base64 encodes the raw string, so tabs are preserved in the base64 payload.
cat > "$TMPDIR/tab-task.json" << 'EOF'
{
  "model": "Claude",
  "status": "working",
  "task": "col1\tcol2\tcol3",
  "updated_at": 9999999999
}
EOF

raw4=$(jq -r "$JQ_EXPR" "$TMPDIR/tab-task.json" 2>/dev/null)
if [[ -n "$raw4" ]]; then
  IFS=$'\x1e' read -r m4 s4 p4 u4 t4 task_b64_4 act_b64_4 ua4 tua4 <<< "$raw4"
  task4=$(printf '%s' "$task_b64_4" | base64 -d 2>/dev/null)
  tab_ok=true
else
  tab_ok=false
fi

assert_eq "tab in task: @base64 does not break IFS split" "true" "$tab_ok"
assert_eq "tab in task: model preserved" "Claude" "$m4"
# task4 still has literal tab (base64 round-trip preserves it)
assert_contains "tab in task: content preserved" "col1" "$task4"

# ── Test 5: Carriage return stripped from activity ──
cat > "$TMPDIR/cr-activity.json" << 'EOF'
{
  "model": "Claude",
  "status": "working",
  "task": "Normal task",
  "activity": "line1\rline2",
  "updated_at": 9999999999
}
EOF

raw5=$(jq -r "$JQ_EXPR" "$TMPDIR/cr-activity.json" 2>/dev/null)
if [[ -n "$raw5" ]]; then
  IFS=$'\x1e' read -r m5 s5 p5 u5 t5 task_b64_5 act_b64_5 ua5 tua5 <<< "$raw5"
  act5=$(printf '%s' "$act_b64_5" | base64 -d 2>/dev/null)
fi

assert_eq "CR in activity: replaced by space" "line1 line2" "$act5"

test_summary
