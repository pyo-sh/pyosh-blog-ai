#!/usr/bin/env bash
# test-token-snapshot.sh — Verify token snapshot schema and freshness (#74)
# Tests token sub-object, freshness separation, stale detection, and fallback policy.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/helpers.sh"

TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

# ── Claude sidecar jq expression (from collect.sh) ──
CLAUDE_JQ='[
  (.model // "Claude"),
  (.status // "idle"),
  (.tokens.pct // 0 | tostring),
  (.tokens.used // 0 | tostring),
  (.tokens.max // 0 | tostring),
  ((.task // "-") | gsub("[\\n\\t\\r]"; " ") | gsub("  +"; " ")),
  ((.activity // "") | gsub("[\\n\\t\\r]"; " ") | gsub("  +"; " ")),
  (.updated_at // 0 | tostring),
  (.tokens_updated_at // 0 | tostring)
] | @tsv'

now_epoch=$(date +%s)

# ── Test 1: tokens_updated_at present and fresh ──
recent=$((now_epoch - 5))
cat > "$TMPDIR/fresh.json" << EOF
{
  "model": "Opus 4.6",
  "status": "working",
  "tokens": {"pct": 45, "used": 90000, "max": 200000},
  "task": "Test task",
  "activity": "Edit: foo.ts",
  "updated_at": ${recent}.123,
  "tokens_updated_at": ${recent}.456
}
EOF

raw=$(jq -r "$CLAUDE_JQ" "$TMPDIR/fresh.json")
IFS=$'\t' read -r model status pct tok_used tok_total task activity updated_at tokens_updated_at <<< "$raw"

tok_fresh=true
tok_ts="${tokens_updated_at:-0}"
[[ "$tok_ts" == "0" || "$tok_ts" == "null" || -z "$tok_ts" ]] && tok_ts="${updated_at:-0}"
if [[ -n "$tok_ts" && "$tok_ts" != "0" && "$tok_ts" != "null" ]]; then
  tok_age=$(( now_epoch - ${tok_ts%.*} ))
  (( tok_age > 30 )) && tok_fresh=false
fi

assert_eq "fresh tokens: pct" "45" "$pct"
assert_eq "fresh tokens: used" "90000" "$tok_used"
assert_eq "fresh tokens: total" "200000" "$tok_total"
assert_eq "fresh tokens: fresh=true" "true" "$tok_fresh"

# ── Test 2: tokens_updated_at stale (>30s) but status still recent ──
old_tok=$((now_epoch - 60))
cat > "$TMPDIR/split.json" << EOF
{
  "model": "Opus 4.6",
  "status": "working",
  "tokens": {"pct": 30, "used": 60000, "max": 200000},
  "task": "Active task",
  "activity": "Bash: running",
  "updated_at": ${recent}.0,
  "tokens_updated_at": ${old_tok}.0
}
EOF

raw2=$(jq -r "$CLAUDE_JQ" "$TMPDIR/split.json")
IFS=$'\t' read -r m2 s2 p2 tu2 tt2 ta2 ac2 ua2 tua2 <<< "$raw2"

tok_fresh2=true
tok_ts2="${tua2:-0}"
[[ "$tok_ts2" == "0" || "$tok_ts2" == "null" || -z "$tok_ts2" ]] && tok_ts2="${ua2:-0}"
if [[ -n "$tok_ts2" && "$tok_ts2" != "0" && "$tok_ts2" != "null" ]]; then
  tok_age2=$(( now_epoch - ${tok_ts2%.*} ))
  (( tok_age2 > 30 )) && tok_fresh2=false
fi

assert_eq "split state: status is working (recent updated_at)" "working" "$s2"
assert_eq "split state: tok_fresh=false (tokens_updated_at stale)" "false" "$tok_fresh2"
# Values preserved, not reset to 0
assert_eq "split state: tok_used preserved" "60000" "$tu2"
assert_eq "split state: tok_total preserved" "200000" "$tt2"

# ── Test 3: No tokens_updated_at (backward compat) — fall back to updated_at ──
cat > "$TMPDIR/no-tua.json" << EOF
{
  "model": "Claude",
  "status": "working",
  "tokens": {"pct": 20, "used": 40000, "max": 200000},
  "task": "Old sidecar format",
  "updated_at": ${recent}.0
}
EOF

raw3=$(jq -r "$CLAUDE_JQ" "$TMPDIR/no-tua.json")
IFS=$'\t' read -r m3 s3 p3 tu3 tt3 ta3 ac3 ua3 tua3 <<< "$raw3"

tok_fresh3=true
tok_ts3="${tua3:-0}"
[[ "$tok_ts3" == "0" || "$tok_ts3" == "null" || -z "$tok_ts3" ]] && tok_ts3="${ua3:-0}"
if [[ -n "$tok_ts3" && "$tok_ts3" != "0" && "$tok_ts3" != "null" ]]; then
  tok_age3=$(( now_epoch - ${tok_ts3%.*} ))
  (( tok_age3 > 30 )) && tok_fresh3=false
fi

# tokens_updated_at missing → jq outputs "0" via (// 0), but @tsv trailing field may be empty
# In collect.sh, this triggers fallback to updated_at for freshness
assert_eq "backward compat: fresh=true (falls back to recent updated_at)" "true" "$tok_fresh3"

# ── Test 4: on-status.sh preserves tokens and tokens_updated_at ──
# Simulate: on-status.sh does `. + {status: "idle", ...}` which uses jq object merge.
# tokens and tokens_updated_at must survive.
cat > "$TMPDIR/pre-status.json" << EOF
{
  "model": "Claude",
  "status": "working",
  "tokens": {"pct": 50, "used": 100000, "max": 200000},
  "task": "Some task",
  "activity": "Edit: foo.ts",
  "updated_at": ${recent}.0,
  "tokens_updated_at": ${recent}.0
}
EOF

# Simulate on-status.sh Stop event: `. + {status: "idle", activity: null, updated_at: now}`
post_status=$(jq --arg pane_id "%0" \
  '. + {status: "idle", activity: null, pane_id: $pane_id, updated_at: now} |
   if (.task != null and .task != "—" and (.task | startswith("(Done) ") | not))
   then .task = "(Done) " + .task
   else . end' "$TMPDIR/pre-status.json")

# Verify tokens survived the merge
assert_json_field "on-status preserves tokens.used" "$post_status" ".tokens.used" "100000"
assert_json_field "on-status preserves tokens.max" "$post_status" ".tokens.max" "200000"
assert_json_field "on-status preserves tokens.pct" "$post_status" ".tokens.pct" "50"
# tokens_updated_at should NOT change (on-status.sh doesn't set it)
assert_json_field "on-status preserves tokens_updated_at" "$post_status" \
  ".tokens_updated_at" "${recent}.0"
# But updated_at DOES change
tok_updated=$(printf '%s' "$post_status" | jq -r '.updated_at')
assert_ne "on-status updates updated_at" "${recent}.0" "$tok_updated"

# ── Test 5: on-statusline.sh sets tokens_updated_at ──
# Simulate the on-statusline.sh jq merge expression with tokens_updated_at
cat > "$TMPDIR/statusline-input.json" << 'EOF'
{
  "model": {"display_name": "Opus 4.6"},
  "context_window": {
    "context_window_size": 200000,
    "used_percentage": 45,
    "current_usage": {"input_tokens": 90000, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0}
  }
}
EOF

existing='{}'
statusline_result=$(jq -n --argjson existing "$existing" \
  --argjson input "$(cat "$TMPDIR/statusline-input.json")" \
  --arg pane_id "%0" --argjson precomputed 0 '
  ($input.model.display_name // $input.model.id // "Claude") as $model |
  ($input.context_window.context_window_size // 200000) as $max_tokens |
  (($input.context_window.used_percentage // 0) | floor) as $pct |
  (
    if $precomputed > 0 then $precomputed
    elif $input.context_window.current_usage != null then
      (($input.context_window.current_usage.input_tokens // 0) +
       ($input.context_window.current_usage.cache_creation_input_tokens // 0) +
       ($input.context_window.current_usage.cache_read_input_tokens // 0))
    elif $pct > 0 then
      ($max_tokens * $pct / 100 | floor)
    else 0 end
  ) as $used_tokens |
  $existing * {
    pane_id: $pane_id,
    model: $model,
    tokens: { used: $used_tokens, max: $max_tokens, pct: (if $pct > 100 then 100 else $pct end) },
    updated_at: now,
    tokens_updated_at: now
  }
')

assert_json_field "statusline sets tokens.used" "$statusline_result" ".tokens.used" "90000"
assert_json_field "statusline sets tokens.max" "$statusline_result" ".tokens.max" "200000"
assert_json_field "statusline sets tokens.pct" "$statusline_result" ".tokens.pct" "45"
# tokens_updated_at should be set (non-zero)
tua_val=$(printf '%s' "$statusline_result" | jq -r '.tokens_updated_at')
assert_ne "statusline sets tokens_updated_at" "0" "$tua_val"
assert_ne "statusline tokens_updated_at not null" "null" "$tua_val"

# ── Test 6: Claude fallback — total unknown, tok_k not computed ──
# Simulate scraping fallback with no regex match: source=unknown, values=0
# In collect.sh, when no scraping match: tok_source="unknown", tok_used=0, tok_total=0
# Renderer should show "?" not "0k"
tok_source="unknown"
tok_used=0
tok_total=0
tok_pct=0

# Simulate renderer logic
if [[ "$tok_source" == "unknown" ]]; then
  tok_display="   ?"
else
  tok_display="  0k"
fi
assert_eq "unknown source: display is ?" "   ?" "$tok_display"

# ── Test 7: Claude fallback — total known, tok_k computed correctly ──
# Simulate scraping match: "45% of 128k tokens"
input_text="45% of 128k tokens remaining"
tok_match=$(printf '%s' "$input_text" | grep -oE '[0-9]+% of [0-9]+k tokens' | tail -1)
if [[ -n "$tok_match" ]]; then
  fb_pct=$(printf '%s' "$tok_match" | grep -oE '^[0-9]+')
  fb_total_k=$(printf '%s' "$tok_match" | grep -oE 'of [0-9]+k' | grep -oE '[0-9]+')
  fb_total=$(( fb_total_k * 1000 ))
  fb_used=$(( fb_pct * fb_total / 100 ))
  fb_source="scraping"
fi
assert_eq "scraping fallback: total" "128000" "$fb_total"
assert_eq "scraping fallback: used" "57600" "$fb_used"
assert_eq "scraping fallback: source" "scraping" "$fb_source"

# ── Test 8: Parse failure shows stale, not 0 ──
# When jq fails and we have cached data, fresh=false, values preserved
cached_model="codex-mini-latest"
cached_tok_used="50000"
cached_tok_total="128000"
cached_task="cached task"

# Simulate parse failure with cache available
raw_jq=""  # Empty = parse failed
if [[ -z "$raw_jq" ]]; then
  # Use cache
  model="$cached_model"
  tok_used="$cached_tok_used"
  tok_total="$cached_tok_total"
  task="$cached_task"
  tok_fresh=false
fi
assert_eq "parse failure: model from cache" "codex-mini-latest" "$model"
assert_eq "parse failure: tok_used from cache" "50000" "$tok_used"
assert_eq "parse failure: tok_total from cache" "128000" "$tok_total"
assert_eq "parse failure: fresh=false" "false" "$tok_fresh"
assert_ne "parse failure: tok_used not 0" "0" "$tok_used"

# ── Test 9: Renderer stale display — "?" suffix instead of "k" ──
tok_fresh=false
tok_k=50
if [[ "$tok_fresh" == "false" ]]; then
  printf -v tok_str "%3d?" "$tok_k"
else
  printf -v tok_str "%3dk" "$tok_k"
fi
assert_eq "stale display: suffix is ?" " 50?" "$tok_str"

# ── Test 10: Renderer fresh display — "k" suffix ──
tok_fresh=true
tok_k=90
if [[ "$tok_fresh" == "false" ]]; then
  printf -v tok_str "%3d?" "$tok_k"
else
  printf -v tok_str "%3dk" "$tok_k"
fi
assert_eq "fresh display: suffix is k" " 90k" "$tok_str"

test_summary
