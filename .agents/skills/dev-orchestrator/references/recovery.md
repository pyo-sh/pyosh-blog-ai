# Orchestrator recovery

Resume from `batch.state.json` when the orchestrator crashes or is restarted.

## Entry

Check for existing state file:

```bash
STATE_FILE=".workspace/orchestrate/{area}/batch.state.json"
[ -f "$STATE_FILE" ] && echo "EXISTS" || echo "NOT EXISTS"
```

If found, read state and resume based on current issue statuses.

## Recovery steps

### 1. Read state + re-register identity

```bash
source scripts/orchestrate-helpers.sh
STATE=$(orch_state_read "$AREA")
AGENT=$(echo "$STATE" | jq -r '.agent')

# Update orchestrator identity (PID, pane) for liveness detection.
orch_register_self "$AREA"
```

### 2. Check provider health

```bash
GH_HEALTH=$(orch_provider_health_get "$AREA")
if [ "$GH_HEALTH" = "hard_fault" ]; then
  echo "[recovery] GitHub hard fault - fix auth before resuming"
  exit 1
fi
```

### 3. Reconcile dispatched issues

For each issue with status `dispatched`, check completion using the priority chain
(exit file JSON + attemptId match, then process group alive, then PR status):

```bash
DISPATCHED=$(echo "$STATE" | jq -r '.dispatched | keys[]')
for ISSUE in $DISPATCHED; do
  RESULT=$(orch_check_completion "$ISSUE" "$AREA_DIR")

  case "$RESULT" in
    completed|failed)
      orch_status_set "$AREA" "$ISSUE" "$RESULT"
      orch_state_update "$AREA" "del(.dispatched[\"$ISSUE\"])"
      orch_unblock "$AREA" "$ISSUE"
      ;;
    abnormal_exit)
      RETRY=$(echo "$STATE" | jq -r ".dispatched[\"$ISSUE\"].retryCount // 0")
      if [ "$RETRY" -lt 1 ]; then
        echo "[recovery] Abnormal exit for #$ISSUE - re-dispatching"
        orch_state_update "$AREA" "del(.dispatched[\"$ISSUE\"])"
        orch_dispatch "$ISSUE" "$AREA_DIR" "$AGENT" "$((RETRY + 1))"
      else
        echo "[recovery] #$ISSUE abnormal exit, retry exhausted - marking failed"
        orch_status_set "$AREA" "$ISSUE" "failed"
        orch_state_update "$AREA" "del(.dispatched[\"$ISSUE\"])"
        orch_unblock "$AREA" "$ISSUE"
      fi
      ;;
    running)
      # Process group still alive - no action needed
      ;;
  esac
done
```

### 4. Resume poll cycle

After reconciliation, resume the normal poll loop:

```bash
while true; do
  orch_poll_cycle "$AREA" "$AREA_DIR" "$AGENT"

  REMAINING=$(orch_state_read "$AREA" | jq \
    '[.status | to_entries[]
     | select(.value == "pending" or .value == "dispatched" or .value == "blocked")
     ] | length')
  [ "$REMAINING" -eq 0 ] && break

  sleep 30
done
```

### 5. Stale state

If the batch is already complete (all issues terminal) but state file remains:

```bash
orch_print_summary "$AREA"
rm -rf ".workspace/orchestrate/$AREA/"
echo "[recovery] Stale state cleaned up."
```

## Per-status recovery

| Status | Action |
|--------|--------|
| `pending` | No action - dispatched in next poll cycle |
| `blocked` | No action - waiting for deps to resolve |
| `dispatched` | Check via `orch_check_completion`; reconcile based on result |
| `completed` | Re-run `orch_unblock` (idempotent) |
| `failed` | Re-run `orch_unblock` (failed deps still unblock, may produce `skipped_dep_failed`) |
| `skipped_dep_failed` | Terminal - re-run `orch_unblock` for downstream (idempotent) |

## DAG integrity

After crash, re-validate DAG (no new cycles introduced):

```bash
ISSUES_JSON=$(orch_state_read "$AREA" | jq '.issues')
DAG_JSON=$(orch_state_read "$AREA" | jq '.dag')
bash scripts/parse-dependencies.sh --check-cycles "$ISSUES_JSON" "$DAG_JSON"
```

If cycle found (shouldn't happen unless state was corrupted), abort and ask user.

## Auto-retry policy

Maximum 1 automatic re-dispatch per issue. Track in state:

```json
"dispatched": {
  "5": {
    "pid": 12345,
    "pgid": 12345,
    "attemptId": "batch-20260308-issue5-attempt1",
    "retryCount": 1
  }
}
```

If `retryCount >= 1` and process dies again, mark `failed` and report to user.
Do not retry a third time automatically.
