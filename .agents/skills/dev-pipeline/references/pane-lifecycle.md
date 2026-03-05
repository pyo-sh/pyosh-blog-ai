# Pane lifecycle

## Return codes

| Code | stdout | Meaning |
|------|--------|---------|
| 0 | result | Success |
| 1 | `TIMEOUT` | Polling expired |
| 2 | `PANE_DEAD` | Pane process died |
| 3 | `PATH_INVALID` | Working directory not found |
| 5 | `MAX_RETRIES` | State-based retry limit reached |

## Key behaviors

- `pipeline_open_pane_verified()`: validates dir, opens pane, 3s startup check. Single attempt only (no internal retry). On failure, captures dead pane output via `remain-on-exit` for diagnosis, then cleans up.
- `pipeline_open_pane_with_retry()`: state-based retry wrapper. Reads `{field}Retries` from state, checks against `maxPaneRetries`, increments before attempting. Kills previous pane for the same field before opening new one.
- `pipeline_pane_alive_verified()`: checks pane existence AND verifies the running command matches expected (claude/codex). Prevents false positives after tmux server restart.
- `pipeline_poll_review()` / `pipeline_poll_commits()`: checks API first (catches normal exit), then pane health.

## Orchestrator protocol for opening panes

Follow this 3-layer protocol to prevent orphan pane proliferation.

### Layer 1: Pre-defense (before open)

```bash
# Kill previous pane recorded in state
pipeline_kill_state_pane "$ISSUE" "$AREA" "reviewPane"

# Snapshot current panes for orphan detection
pipeline_pane_snapshot > /tmp/panes_before_${ISSUE}.txt
```

### Layer 2: Execution (single call, file-based capture)

```bash
# Always redirect to file - never rely on bash variable capture alone
PANE_OUT="/tmp/pipeline-pane-${ISSUE}-${AREA}.txt"
pipeline_open_pane_with_retry "$ISSUE" "$AREA" "reviewPane" \
  "$MONOREPO_ROOT" "$PROMPT" "$AGENT" "$ORCHESTRATOR_PANE" \
  > "$PANE_OUT" 2>/tmp/pipeline-pane-err.txt
RC=$?
PANE_ID=$(cat "$PANE_OUT")

# NEVER call this again with different bash syntax. One call only.
```

### Layer 3: Post-diagnosis (on failure only)

```bash
if [ $RC -ne 0 ]; then
  # Clean up orphans created during the failed attempt
  pipeline_pane_snapshot > /tmp/panes_after_${ISSUE}.txt
  pipeline_pane_orphan_cleanup /tmp/panes_before_${ISSUE}.txt /tmp/panes_after_${ISSUE}.txt

  # stderr from the function contains dead pane output for diagnosis
  # Escalate to user - do not auto-retry at orchestrator level
fi
```

## State schema for retry tracking

```json
{
  "reviewPaneRetries": 0,
  "resolvePaneRetries": 0,
  "maxPaneRetries": 2
}
```

Retry counters persist across sessions. Reset to 0 when step transitions (e.g., review -> resolve).
