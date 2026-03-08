# Orchestrator recovery

Resume from `batch.state.json` when the orchestrator crashes or is restarted.

## Entry

```bash
ls .workspace/orchestrate/{area}/batch.state.json 2>/dev/null
```

If found -> read state, resume based on current issue statuses.

## Recovery steps

### 1. Read state + re-register identity

```bash
source scripts/orchestrate-helpers.sh
STATE=$(orch_state_read "$AREA")
AGENT=$(echo "$STATE" | jq -r '.agent')

# Update orchestrator pane/startedAt so agent-tracker can detect liveness.
orch_register_self "$AREA"
```

### 2. Reconcile dispatched issues

For each issue with status `dispatched`, check if the background process is still alive:

```bash
DISPATCHED=$(echo "$STATE" | jq -r '.dispatched | keys[]')
for ISSUE in $DISPATCHED; do
  PID=$(echo "$STATE" | jq -r ".dispatched[\"$ISSUE\"].pid")

  RESULT=$(orch_check_completion "$ISSUE" "$AREA_DIR")
  if [ "$RESULT" = "completed" ] || [ "$RESULT" = "failed" ]; then
    orch_status_set "$AREA" "$ISSUE" "$RESULT"
    orch_state_update "$AREA" "del(.dispatched[\"$ISSUE\"])"
    orch_unblock "$AREA" "$ISSUE"
  elif ! orch_process_alive "$PID"; then
    # Process died but pipeline may still be running (orphaned sub-processes)
    # Re-dispatch with bounded retry
    RETRY=$(echo "$STATE" | jq -r ".dispatched[\"$ISSUE\"].retryCount // 0")
    if [ "$RETRY" -lt 1 ]; then
      echo "[recovery] Process $PID for #$ISSUE is dead; re-dispatching"
      NEW_PID=$(orch_dispatch "$ISSUE" "$AREA_DIR" "$AGENT")
      if [ -n "$NEW_PID" ]; then
        RETRY_NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)
        orch_state_update "$AREA" \
          ".dispatched[\"$ISSUE\"].pid = $NEW_PID | .dispatched[\"$ISSUE\"].retryCount = $((RETRY + 1)) | .dispatched[\"$ISSUE\"].dispatchedAt = \"$RETRY_NOW\" | .dispatched[\"$ISSUE\"].lastActivity = \"$RETRY_NOW\" | .dispatched[\"$ISSUE\"].pipelineStarted = false"
      fi
    else
      echo "[recovery] Process for #$ISSUE dead, retry exhausted - marking failed"
      orch_status_set "$AREA" "$ISSUE" "failed"
      orch_state_update "$AREA" "del(.dispatched[\"$ISSUE\"])"
      orch_unblock "$AREA" "$ISSUE"
    fi
  fi
  # else: process alive, still running - no action needed
done
```

### 3. Resume poll cycle

After reconciliation, resume the normal poll loop:

```bash
while true; do
  orch_poll_cycle "$AREA" "$AREA_DIR" "$AGENT"

  # Check batch completion
  REMAINING=$(orch_state_read "$AREA" | jq \
    '[.status | to_entries[] | select(.value == "pending" or .value == "dispatched" or .value == "blocked")] | length')
  [ "$REMAINING" -eq 0 ] && break

  sleep 30
done
```

### 4. Stale state

If the batch is already complete (all issues `completed` or `failed`) but state file remains:

```bash
orch_print_summary "$AREA"
rm -rf ".workspace/orchestrate/$AREA/"
echo "[recovery] Stale state cleaned up."
```

## Per-status recovery

| Status | Action |
|--------|--------|
| `pending` | No action - will be dispatched in next poll cycle |
| `blocked` | No action - waiting for deps to complete |
| `dispatched` | Check PID alive; if dead, re-dispatch (max 1 retry) or fail |
| `completed` | Re-run `orch_unblock` (idempotent) |
| `failed` | Re-run `orch_unblock` (failed issues still unblock dependents) |

## DAG integrity

After crash, re-validate DAG (no new cycles introduced):

```bash
ISSUES_JSON=$(orch_state_read "$AREA" | jq '.issues')
DAG_JSON=$(orch_state_read "$AREA" | jq '.dag')
bash scripts/parse-dependencies.sh --check-cycles "$ISSUES_JSON" "$DAG_JSON"
```

If cycle found (shouldn't happen unless state was corrupted) -> abort and ask user.

## Auto-retry policy

Maximum 1 automatic re-dispatch per issue. Track retry count in state:

```json
"dispatched": {
  "5": {"pid": 12345, "retryCount": 1, ...}
}
```

If `retryCount >= 1` and process dies again -> mark `failed`, report to user. Do not
retry a third time automatically.
