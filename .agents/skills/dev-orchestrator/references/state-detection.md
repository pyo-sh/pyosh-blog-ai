# State detection

How the orchestrator determines whether a dispatched issue's pipeline has completed,
failed, or stalled.

## Terminal result contract

`terminal.json` is the **sole basis** for a `completed` or `failed` result.
No path reaches `completed` without a valid terminal file.

Written by `orch-dispatch-wrapper.sh` via `trap EXIT`, covering normal exit and
SIGTERM. Only SIGKILL prevents writing (trap cannot catch it). In that edge case
the orchestrator receives `abnormal_exit` (see completion detection below).

### Schema (schemaVersion 1)

```
.workspace/orchestrate/{area}/issues/{N}/attempts/{attemptId}/terminal.json
```

`attemptId` format: `issue-{N}-a{M}` (e.g., `issue-78-a0` for first attempt).

```json
{
  "schemaVersion": 1,
  "attemptId": "issue-78-a0",
  "issue": 78,
  "status": "completed",
  "prNumber": 123,
  "merged": true,
  "headSha": "abc1234def5678",
  "finishedAt": "2026-03-08T12:34:56Z",
  "reason": "pipeline completed at step=log"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `schemaVersion` | integer | Always `1` for this revision |
| `attemptId` | string | Matches the dispatch attempt ID in batch state |
| `issue` | integer | GitHub issue number |
| `status` | `"completed"` \| `"failed"` | Pipeline exit status |
| `prNumber` | integer \| null | PR number if pipeline created one |
| `merged` | boolean | `true` if pipeline reached `log`/`done` step |
| `headSha` | string \| null | Last commit SHA on the PR branch if known |
| `finishedAt` | ISO-8601 UTC | When the wrapper exit trap ran |
| `reason` | string | Human-readable exit summary |

**Attempt isolation**: Each attempt writes to its own directory (`issues/{N}/attempts/{attemptId}/`). Previous attempt artifacts are preserved. The `attemptId` field in terminal.json is still validated as a safety net, but stale file collision is structurally prevented by directory separation.

## Completion detection

`orch_check_completion <issue> <area_dir>` checks in priority order:

### 1. terminal.json (sole source of `completed` / `failed`)

If the terminal file exists and the `attemptId` matches:

| `status` field | Result |
|----------------|--------|
| `"completed"` | `completed` |
| anything else | `failed` |

### 2. Process group alive (PGID)

No terminal file yet; check whether the process group is still running:

```bash
orch_pgid_alive "$pgid"
```

| Process group | Terminal file | Result |
|---------------|---------------|--------|
| alive | absent | `running` |
| alive | present + match | `completed` or `failed` (per terminal file) |
| dead | present + match | `completed` or `failed` (per terminal file) |
| dead | absent | fall through to method 3 |
| dead | present + mismatch | fall through (stale file) |

The `pipelineStarted` flag tracks whether the pipeline state file was ever observed
(observability only - no effect on completion logic).

### 3. Grace period (process dead, no terminal file)

60-second grace period after process death. The exit handler may still be writing
the file, or there is a race between termination and filesystem flush.

After grace period: fall through to PR status check.

### 4. PR status (supplementary only - never produces `completed`)

Process is dead and terminal.json was not written (SIGKILL or trap failure).
PR evidence helps distinguish `abnormal_exit` from `failed` but cannot confirm
a successful completion.

Before checking PR status, verify GitHub provider health:

| Provider | Action |
|----------|--------|
| `healthy` | Proceed with PR check |
| `degraded` | Return `running` (don't make PR-based judgments) |
| `hard_fault` | Return `running` (poll cycle should halt) |

PR check uses `orch_gh` (provider health wrapper):

| PR state | Result | Note |
|----------|--------|------|
| Merged PR exists | `abnormal_exit` | Process killed before trap wrote terminal file |
| Open PR exists | `abnormal_exit` | Process died mid-pipeline |
| gh command failed | `running` | Don't judge on API error |
| No PR at all | `failed` | No sign of progress |

`abnormal_exit` triggers the retry path in `orch_poll_cycle`.

Always use `-R <owner/repo>` for explicit repo targeting. Avoid deprecated fields
like `projectCards` - use `number,title,state,body,url` only.

## Stall detection

`orch_detect_stall <area> <issue>` uses a multi-signal approach.

### Detection priority

1. **Heartbeat** (strongest): `{attemptDir}/heartbeat`
   - Written every 60s by `orch-dispatch-wrapper.sh`
   - If last heartbeat < 120s ago -> `active`

2. **Elapsed time**: `lastActivity` timestamp vs threshold
   - Post-PR threshold: 10 minutes (600s)
   - Pre-PR threshold: 20 minutes (1200s)
   - If elapsed < threshold -> `active`

3. **Composite signals** (when threshold exceeded, any positive = active):
   - Log file mtime change (output is being written)
   - CPU jiffies change (`/proc/{pid}/stat` fields 14+15)
   - PR commit SHA change (new commits pushed)

4. **No positive signals**: `stalled`
   - Records `stallReason` in state for debugging

### Stall reason tracking

```json
"dispatched": {
  "29": {
    "stallReason": "no heartbeat, process group alive but no log/cpu/commit activity for 620s"
  }
}
```

### On stall detected

| Process group | Retry | Action |
|---------------|-------|--------|
| dead | available (< 1) | Auto re-dispatch |
| dead | exhausted (>= 1) | Mark `failed`, unblock dependents |
| alive | any | Report to user, no auto-action |

## Status state machine

```
pending
  +-(dispatch)-> dispatched
                   |-(terminal.json: completed)---> completed
                   |-(terminal.json: failed)-------> failed
                   |-(abnormal exit, retry)---------> dispatched (re-dispatch)
                   |-(abnormal exit, no retry)-------> failed
                   +-(stall + dead + retry)---------> dispatched (re-dispatch)
                   +-(stall + dead + exhausted)-----> failed

blocked
  +-(all deps completed)--------------------> pending
  +-(all deps resolved, >= 1 failed)--------> skipped_dep_failed

completed  --(triggers orch_unblock)
failed     --(triggers orch_unblock, may produce skipped_dep_failed)
skipped_dep_failed --(triggers orch_unblock for downstream)
```

Terminal states: `completed`, `failed`, `skipped_dep_failed`.

## Provider health

GitHub API circuit breaker tracked in `batch.state.json`:

```json
"providers": {
  "github": {
    "status": "healthy",
    "consecutiveFailures": 0,
    "lastError": null,
    "lastCheckedAt": "2026-03-08T12:00:00Z"
  }
}
```

| Transition | Trigger |
|------------|---------|
| healthy -> degraded | 3 consecutive gh failures |
| degraded -> healthy | 1 successful gh call |
| any -> hard_fault | gh exit code 4 (auth failure) |

During `degraded`: completion checks return `running` instead of PR-based judgments.
During `hard_fault`: all `orch_gh` calls blocked, poll cycle halts.

## Polling interval

Default: 30 seconds per cycle. `orch_poll_cycle` processes ALL dispatched issues
per cycle, so the effective per-issue latency is still 30s regardless of batch size.
