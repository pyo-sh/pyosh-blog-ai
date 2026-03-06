# State detection

How the orchestrator determines whether a dispatched issue's pipeline has completed,
failed, or stalled.

## Completion detection

`orch_check_completion <issue> <area_dir>` checks in priority order (see `orchestrate-helpers.sh`):

### 1. Signal file (highest priority)

```
.workspace/orchestrate/{area}/issue-{N}.exit
```

Content `ok` -> `completed`. Any other content -> `failed`.

The signal file is optional. If present, it takes highest priority.
It is not written automatically - the pipeline AI or an external hook must produce it.
In practice, the primary detection path is method 2 (process exit + state file absence).

If no signal file exists, fall back to method 2.

### 2. Process alive check (PID)

Check whether the background `claude -p` process is still running:

```bash
kill -0 "$pid" 2>/dev/null
```

| Process | State file | pipelineStarted | Result |
|---------|-----------|-----------------|--------|
| alive | exists | * | `running` (marks `pipelineStarted: true`) |
| alive | absent | true | `completed` (Step 7 deleted it) |
| alive | absent | false | `running` (not created yet) |
| dead | * | * | fall through to method 3 |

The `pipelineStarted` flag in `batch.state.json` tracks whether the pipeline state file
was ever observed. This prevents false `completed` judgments when the state file hasn't
been created yet (dispatch just happened, pipeline still in Step 1).

### 3. Pipeline state file (process exited)

When the headless process has exited:

| State file | pipelineStarted | Result |
|-----------|-----------------|--------|
| absent | true | `completed` |
| absent | false | fall through (early crash, never started) |
| exists | * | fall through (pipeline didn't finish) |

### 4. PR status (fallback)

After methods 2-3 are inconclusive:

```bash
gh pr list -R "$REPO" \
  --search "Closes #${issue}" --state merged \
  --json number --jq 'length'
```

- Merged PR exists -> `completed`
- Open PR exists -> `running` (pipeline may still be cleaning up)
- No PR at all -> `failed`

Always use `-R <owner/repo>` for explicit repo targeting. Avoid deprecated fields
like `projectCards` - use `number,title,state,body,url` only.

## Stall detection

`orch_detect_stall <area> <issue>` checks if the last activity timestamp
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
1. Fetch latest commit SHA on the PR via `gh api repos/{repo}/pulls/{pr}/commits`
2. Compare with `lastCommitSha` in state
3. Different -> update `lastActivity` + `lastCommitSha`, return "active"
4. Same -> return "stalled"

Extended threshold (2x normal) for pre-PR phase when no open PR exists yet.

### On stall detected

Orchestrator reports to user:

```
[orchestrator] STALL: Issue #N - no activity for 10+ minutes
  Process PID 12345 still alive. Consider: stop, retry, or skip
```

Automatic handling:
- Process dead + retry available -> auto re-dispatch (max 1 retry per issue)
- Process dead + retry exhausted -> mark `failed`, unblock dependents
- Process alive + stalled -> report only, user decides

## Status state machine

```
pending
  └─(dispatch)──► dispatched
                    ├─(completion: ok)──► completed
                    ├─(completion: fail)─► failed
                    └─(stall + skip)──────► failed

blocked
  └─(all deps completed OR failed)──► pending

completed ──(triggers orch_unblock)
failed    ──(triggers orch_unblock - dependency was attempted, downstream unblocked)
```

## Polling interval

Default: 30 seconds per cycle.

`orch_poll_cycle` processes ALL dispatched issues per cycle, so the effective
per-issue latency is still 30s regardless of batch size.
