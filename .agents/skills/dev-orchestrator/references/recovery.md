# Orchestrator Recovery

Resume from `batch.state.json` when the orchestrator crashes or is restarted.

## Entry

```bash
ls .workspace/orchestrate/{area}/batch.state.json 2>/dev/null
```

If found → read state, resume based on current issue statuses.

## Recovery Steps

### 1. Read State

```bash
source scripts/orchestrate-helpers.sh
STATE=$(orch_state_read "$AREA")
AGENT=$(echo "$STATE" | jq -r '.agent')
ORCH_PANE=$(tmux display-message -p '#{pane_id}')  # current pane
```

Update `orchestratorPane` to the new pane (session may have changed):

```bash
orch_state_update "$AREA" ".orchestratorPane = \"$ORCH_PANE\""
```

### 2. Reconcile Dispatched Issues

For each issue with status `dispatched`:

```bash
DISPATCHED=$(echo "$STATE" | jq -r '.dispatched | keys[]')
for ISSUE in $DISPATCHED; do
  RESULT=$(orch_check_completion "$ISSUE" "$AREA_DIR")
  if [ "$RESULT" = "completed" ] || [ "$RESULT" = "failed" ]; then
    orch_status_set "$AREA" "$ISSUE" "$RESULT"
    [ "$RESULT" = "completed" ] && orch_unblock "$AREA" "$ISSUE"
  else
    # Still running — check pane
    PANE=$(echo "$STATE" | jq -r ".dispatched[\"$ISSUE\"].pane")
    if ! orch_pane_alive "$PANE"; then
      # Pane died but pipeline still running — re-dispatch
      echo "[recovery] Pane $PANE for #$ISSUE is dead; re-dispatching"
      IDLE=$(orch_find_idle_panes "$ORCH_PANE")
      for P in $IDLE; do
        orch_dispatch "$ISSUE" "$P" "$AREA_DIR" "$AGENT" && \
          orch_record_dispatch "$AREA" "$ISSUE" "$P" && break
      done
    fi
  fi
done
```

### 3. Resume Poll Cycle

After reconciliation, resume the normal poll loop:

```bash
while true; do
  orch_poll_cycle "$AREA" "$AREA_DIR" "$AGENT" "$ORCH_PANE"

  # Check batch completion
  ALL_DONE=$(orch_state_read "$AREA" | jq -r '
    .issues | map(tostring) | .[] as $n |
    .status[$n] // "pending" | select(. == "pending" or . == "dispatched" or . == "blocked")
  ' | wc -l)
  [ "$ALL_DONE" -eq 0 ] && break

  sleep 30
done
```

### 4. Stale State

If the batch is already complete (all issues `completed` or `failed`) but state file remains:

```bash
orch_print_summary "$AREA" "$AREA_DIR"
rm -rf ".workspace/orchestrate/$AREA/"
echo "[recovery] Stale state cleaned up."
```

## Per-Status Recovery

| Status | Action |
|--------|--------|
| `pending` | No action — will be dispatched when idle pane available |
| `blocked` | No action — waiting for deps to complete |
| `dispatched` | Check completion; if pane dead, re-dispatch |
| `completed` | Re-run `orch_unblock` (idempotent) |
| `failed` | Re-run `orch_unblock` (failed issues still unblock dependents) |

## DAG Integrity

After crash, re-validate DAG (no new cycles introduced):

```bash
ISSUES_JSON=$(orch_state_read "$AREA" | jq '.issues')
DAG_JSON=$(orch_state_read "$AREA" | jq '.dag')
bash scripts/parse-dependencies.sh --check-cycles "$ISSUES_JSON" "$DAG_JSON"
```

If cycle found (shouldn't happen unless state was corrupted) → abort and ask user.

## Auto-Retry Policy

Maximum 1 automatic re-dispatch per issue. Track retry count in state:

```json
"dispatched": {
  "5": {"pane": "%3", "retryCount": 1, ...}
}
```

If `retryCount >= 1` and pane dies again → mark `failed`, report to user. Do not
retry a third time automatically.

```bash
orch_state_update "$AREA" ".dispatched[\"$ISSUE\"].retryCount = ((.dispatched[\"$ISSUE\"].retryCount // 0) + 1)"
```
