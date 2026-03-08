#!/usr/bin/env bash
# test-codex-parse.sh — Verify Codex session JSONL parsing (#72, #74)
# Tests multiline message safety, @tsv extraction, and coherent token snapshot.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/helpers.sh"

TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

# The jq expression used in _collect_codex_pane (lib/collect.sh)
# Coherent snapshot: used+total extracted from same .payload.info event (#74)
JQ_EXPR='
  def last_ne(f): [.[] | f | select(. != null and . != "")] | if length == 0 then null else last end;
  (
    [.[] | select(.payload.info | type == "object") |
      { used: .payload.info.total_token_usage.total_tokens,
        total: .payload.info.model_context_window } |
      select(.used != null and .total != null)
    ] | if length == 0 then null else last end
  ) as $tok_pair |
  {
    model: last_ne(select(.type == "turn_context") | .payload.model),
    tok_used:  ($tok_pair.used // 0),
    tok_total: ($tok_pair.total // 0),
    msg:   (last_ne(select(.payload.type == "user_message") | .payload.message)
           // last_ne(select(.type == "response_item" and .payload.role == "user") | .payload.content // .payload.message))
  } | [
    (.model // ""),
    (.tok_used | tostring),
    (.tok_total | tostring),
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
IFS=$'\t' read -r model tok_used tok_total msg <<< "$raw"
assert_eq "normal: model" "codex-mini-latest" "$model"
assert_eq "normal: tok_used" "50000" "$tok_used"
assert_eq "normal: tok_total" "128000" "$tok_total"
assert_eq "normal: msg" "Fix the login bug" "$msg"

# Verify token calculation uses actual window, not 200k
pct=$(( tok_used * 100 / tok_total ))
tok_k=$(( tok_used / 1000 ))
assert_eq "normal: pct uses 128k window" "39" "$pct"
assert_eq "normal: tok_k" "50" "$tok_k"

# ── Test 2: Multiline user message (#72 item 3) ──
cat > "$TMPDIR/multiline.jsonl" << 'EOF'
{"type":"turn_context","payload":{"model":"codex-mini-latest"}}
{"payload":{"type":"user_message","message":"Line one\nLine two\nLine three"}}
{"payload":{"info":{"total_token_usage":{"total_tokens":10000},"model_context_window":200000}}}
EOF

raw2=$(jq -rs "$JQ_EXPR" "$TMPDIR/multiline.jsonl")
IFS=$'\t' read -r model2 tok_used2 tok_total2 msg2 <<< "$raw2"
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
IFS=$'\t' read -r model4 tok_used4 tok_total4 msg4 <<< "$raw4"
assert_eq "tabs: msg tabs replaced" "col1 col2 col3" "$msg4"

# ── Test 5: Coherent snapshot — used/total from same event (#74) ──
# Multiple info events with different windows. Only the last COMPLETE pair should be used.
cat > "$TMPDIR/coherent.jsonl" << 'EOF'
{"type":"turn_context","payload":{"model":"codex-mini-latest"}}
{"payload":{"info":{"total_token_usage":{"total_tokens":30000},"model_context_window":200000}}}
{"payload":{"info":{"total_token_usage":{"total_tokens":60000},"model_context_window":128000}}}
{"payload":{"type":"user_message","message":"second turn"}}
EOF

raw5=$(jq -rs "$JQ_EXPR" "$TMPDIR/coherent.jsonl")
IFS=$'\t' read -r model5 tok_used5 tok_total5 msg5 <<< "$raw5"
assert_eq "coherent: tok_used from last event" "60000" "$tok_used5"
assert_eq "coherent: tok_total from same event" "128000" "$tok_total5"
# Verify pct is calculated from coherent pair
pct5=$(( tok_used5 * 100 / tok_total5 ))
assert_eq "coherent: pct = 46 (not 30)" "46" "$pct5"

# ── Test 6: Incomplete pair — used without total (#74) ──
# Event has total_tokens but no model_context_window → should be filtered out
cat > "$TMPDIR/incomplete-pair.jsonl" << 'EOF'
{"type":"turn_context","payload":{"model":"codex-mini-latest"}}
{"payload":{"info":{"total_token_usage":{"total_tokens":40000}}}}
{"payload":{"type":"user_message","message":"test"}}
EOF

raw6=$(jq -rs "$JQ_EXPR" "$TMPDIR/incomplete-pair.jsonl")
IFS=$'\t' read -r model6 tok_used6 tok_total6 msg6 <<< "$raw6"
assert_eq "incomplete pair: tok_used defaults to 0" "0" "$tok_used6"
assert_eq "incomplete pair: tok_total defaults to 0" "0" "$tok_total6"

# ── Test 7: Mixed — some events have pair, some don't (#74) ──
cat > "$TMPDIR/mixed.jsonl" << 'EOF'
{"type":"turn_context","payload":{"model":"codex-mini-latest"}}
{"payload":{"info":{"total_token_usage":{"total_tokens":20000},"model_context_window":200000}}}
{"payload":{"info":{"total_token_usage":{"total_tokens":50000}}}}
{"payload":{"type":"user_message","message":"test"}}
EOF

raw7=$(jq -rs "$JQ_EXPR" "$TMPDIR/mixed.jsonl")
IFS=$'\t' read -r model7 tok_used7 tok_total7 msg7 <<< "$raw7"
# The last complete pair is the first event (20000/200000), second event is incomplete
assert_eq "mixed: tok_used from last complete pair" "20000" "$tok_used7"
assert_eq "mixed: tok_total from last complete pair" "200000" "$tok_total7"

test_summary
