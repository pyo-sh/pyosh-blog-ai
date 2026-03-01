# State Detection

How the orchestrator determines whether a dispatched issue's pipeline has completed,
failed, or stalled.

## Completion Detection

`orch_check_completion <issue> <area_dir>` checks in priority order:

### 1. Signal File (fastest)

```
.workspace/orchestrate/{area}/issue-{N}.exit
```

Content `ok` → `completed`. Any other content → `failed`.

The signal file is written by the pipeline AI at the end of `/dev-pipeline` (Step 7 log):

```bash
echo "ok" > "$ORCH_BASE/$AREA/issue-${ISSUE}.exit"
```

If the pipeline AI does not write the signal file (older version), fall back to method 2.

### 2. Pipeline State + PR Status

If no signal file and `.workspace/pipeline/issue-{N}.state.json` is absent:

```bash
# Check for merged PR
gh pr list --search "Closes #${issue}" --state merged --json number --jq 'length'
```

- Count > 0 → `completed`
- Count = 0 and no open PR → `failed`
- Count = 0 but open PR exists → still `running` (pipeline cleaning up)

### 3. Still Running

Pipeline state file exists → `running`. Poll again next cycle.

## Pane Health

Each dispatched issue's pane ID is stored in `batch.state.json` under `dispatched.{N}.pane`.

Pane check (informational only — not used for completion):

```bash
tmux list-panes -a -F '#{pane_id}' | grep -qx "$PANE_ID"
```

If the pane is dead but the issue is still `dispatched` (not completed/failed):
- Check completion via signal file / PR status first
- If completion signal found → normal finish (pane closed after done)
- If no completion signal → likely crash; retry or report

## Stall Detection

`orch_detect_stall <area> <issue> <area_dir>` checks if the last activity timestamp
for a dispatched issue exceeds 10 minutes with no new commits on the PR.

### Activity tracking

`lastActivity` is set to current time when:
- Issue is first dispatched (`orch_record_dispatch`)
- A new commit is detected on the PR (`orch_update_last_activity`)

### Stall threshold

```
stall_seconds = 600  # 10 minutes
```

If `now - lastActivity > stall_seconds`:
1. Fetch latest commit SHA on the PR
2. Compare with `lastCommitSha` in state
3. Different → update `lastActivity` + `lastCommitSha`, return "not stalled"
4. Same → return "stalled"

### On stall detected

Orchestrator reports to user:

```
[orchestrator] STALL: Issue #N — no activity for 10+ minutes
  Pane: %3
  Last commit: abc1234 (10:05:00 UTC)
Options: [retry] [skip] [inspect]
```

User chooses:
- **retry** → kill pane, re-dispatch to same or different pane
- **skip** → mark issue `failed`, unblock any dependents
- **inspect** → user manually resolves, orchestrator resumes polling

## Status State Machine

```
pending
  └─(dispatch)──► dispatched
                    ├─(completion: ok)──► completed
                    ├─(completion: fail)─► failed
                    └─(stall + skip)──────► failed

blocked
  └─(all deps completed OR failed)──► pending

completed ──(triggers orch_unblock)
failed    ──(triggers orch_unblock — dependency was attempted, downstream unblocked)
```

## Polling Interval

Default: 30 seconds per cycle.

`orch_poll_cycle` processes ALL dispatched issues per cycle, so the effective
per-issue latency is still 30s regardless of batch size.
