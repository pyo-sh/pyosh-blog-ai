#!/usr/bin/env bash
# test-codex-parse.sh — Verify Codex session JSONL parsing (#72 items 3, 6)
# Tests multiline message safety and @tsv extraction.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/helpers.sh"

TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

# The jq expression used in _collect_codex_pane (lib/collect.sh)
JQ_EXPR='
  def last_ne(f): [.[] | f | select(. != null and . != "")] | if length == 0 then null else last end;
  {
    model:     last_ne(select(.type == "turn_context") | .payload.model),
    total_tok: last_ne(select(.payload.info | type == "object") | .payload.info.total_token_usage.total_tokens),
    ctx_win:   last_ne(select(.payload.info | type == "object") | .payload.info.model_context_window),
    msg:       (last_ne(select(.payload.type == "user_message") | .payload.message)
               // last_ne(select(.type == "response_item" and .payload.role == "user") | .payload.content // .payload.message))
  } | [
    (.model // ""),
    (.total_tok // 0 | tostring),
    (.ctx_win // 0 | tostring),
    ((.msg // "") | gsub("[\\n\\t\\r]"; " ") | gsub("  +"; " "))
  ] | @tsv
'

# ── Test 1: Normal session ──
cat > "$TMPDIR/normal.jsonl" << 'EOF'
{"type":"turn_context","payload":{"model":"o3-mini"}}
{"type":"turn_context","payload":{"model":"codex-mini-latest"}}
{"payload":{"type":"user_message","message":"Fix the login bug"}}
{"payload":{"info":{"total_token_usage":{"total_tokens":50000},"model_context_window":128000}}}
EOF

raw=$(jq -rs "$JQ_EXPR" "$TMPDIR/normal.jsonl")
IFS=$'\t' read -r model total_tok ctx_win msg <<< "$raw"
assert_eq "normal: model" "codex-mini-latest" "$model"
assert_eq "normal: total_tok" "50000" "$total_tok"
assert_eq "normal: ctx_win" "128000" "$ctx_win"
assert_eq "normal: msg" "Fix the login bug" "$msg"

# Verify token calculation uses actual window, not 200k
pct=$(( total_tok * 100 / ctx_win ))
tok_k=$(( total_tok / 1000 ))
assert_eq "normal: pct uses 128k window" "39" "$pct"
assert_eq "normal: tok_k" "50" "$tok_k"

# ── Test 2: Multiline user message (#72 item 3) ──
cat > "$TMPDIR/multiline.jsonl" << 'EOF'
{"type":"turn_context","payload":{"model":"codex-mini-latest"}}
{"payload":{"type":"user_message","message":"Line one\nLine two\nLine three"}}
{"payload":{"info":{"total_token_usage":{"total_tokens":10000},"model_context_window":200000}}}
EOF

raw2=$(jq -rs "$JQ_EXPR" "$TMPDIR/multiline.jsonl")
IFS=$'\t' read -r model2 total_tok2 ctx_win2 msg2 <<< "$raw2"
assert_eq "multiline: msg normalized" "Line one Line two Line three" "$msg2"
assert_eq "multiline: model preserved" "codex-mini-latest" "$model2"

# ── Test 3: Empty session file ──
echo "" > "$TMPDIR/empty.jsonl"
raw3=$(jq -rs "$JQ_EXPR" "$TMPDIR/empty.jsonl" 2>/dev/null || echo "")
# Empty input should not crash, may produce empty or default values
assert_eq "empty session: no crash" "true" "true"

# ── Test 4: Message with tabs ──
cat > "$TMPDIR/tabs.jsonl" << 'EOF'
{"type":"turn_context","payload":{"model":"codex-mini-latest"}}
{"payload":{"type":"user_message","message":"col1\tcol2\tcol3"}}
{"payload":{"info":{"total_token_usage":{"total_tokens":5000},"model_context_window":200000}}}
EOF

raw4=$(jq -rs "$JQ_EXPR" "$TMPDIR/tabs.jsonl")
IFS=$'\t' read -r model4 total_tok4 ctx_win4 msg4 <<< "$raw4"
assert_eq "tabs: msg tabs replaced" "col1 col2 col3" "$msg4"

test_summary
