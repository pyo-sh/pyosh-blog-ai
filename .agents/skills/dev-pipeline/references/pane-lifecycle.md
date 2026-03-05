# Pane lifecycle

## Return codes

| Code | stdout | Meaning |
|------|--------|---------|
| 0 | result | Success |
| 1 | `TIMEOUT` | Polling expired |
| 2 | `PANE_DEAD` | Pane process died |
| 3 | `PATH_INVALID` | Working directory not found |

## Key behaviors

- `pipeline_open_pane_verified()`: validates dir → opens pane → 3s startup check. Single attempt only (no internal retry). On failure, captures dead pane output via `remain-on-exit` for diagnosis, then cleans up.
- `pipeline_poll_review()` / `pipeline_poll_commits()`: checks API first (catches normal exit), then pane health. Prevents false PANE_DEAD when task completed normally.
- No auto-retry at the helper level. Orchestrator decides whether to retry, report, or escalate.

## Orchestrator protocol for opening panes

The orchestrator must follow this 3-layer protocol to prevent orphan pane proliferation:

### Layer 1: Pre-defense (before calling `pipeline_open_pane_verified`)

```bash
# Kill any previous pane recorded in state
pipeline_kill_state_pane "$ISSUE" "$AREA" "reviewPane"

# Snapshot current panes for orphan detection
pipeline_pane_snapshot > /tmp/panes_before_${ISSUE}.txt
```

### Layer 2: Execution (single call, file-based capture)

```bash
# Always redirect to file - never rely on bash variable capture
PANE_OUT="/tmp/pipeline-pane-${ISSUE}-${AREA}.txt"
pipeline_open_pane_verified "$WORKDIR" "$PROMPT" "$AGENT" \
  "$ORCHESTRATOR_PANE" "$ISSUE" "$AREA" > "$PANE_OUT" 2>/tmp/pipeline-pane-err.txt
RC=$?
PANE_ID=$(cat "$PANE_OUT")

# NEVER retry with different bash syntax. One call only.
```

### Layer 3: Post-diagnosis (on failure only)

```bash
if [ $RC -ne 0 ]; then
  # Clean up orphans created during the failed attempt
  pipeline_pane_snapshot > /tmp/panes_after_${ISSUE}.txt
  pipeline_pane_orphan_cleanup /tmp/panes_before_${ISSUE}.txt /tmp/panes_after_${ISSUE}.txt

  # Report diagnosis (stderr from the function contains dead pane output)
  # Escalate to user - do not auto-retry
fi
```
