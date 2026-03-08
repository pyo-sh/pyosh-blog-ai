# State detection

How the orchestrator determines whether a dispatched issue's pipeline has completed,
failed, or stalled.

## Completion detection

`orch_check_completion <issue> <area_dir>` checks in priority order:

### 1. Exit file JSON (highest priority)

```
.workspace/orchestrate/{area}/issue-{N}.exit
```

JSON format with attemptId for stale file safety:

```json
{
  "attemptId": "batch-20260308-issue29-attempt0",
  "status": "completed",
  "rc": 0,
  "endedAt": "2026-03-08T12:34:56Z"
}
```

**attemptId matching**: Only trust the exit file if its `attemptId` matches the
current dispatch's `attemptId` in state. Mismatched files are ignored (stale from
previous batch or retry).

The exit file is written by `orch-dispatch-wrapper.sh` via `trap EXIT`, covering
normal exit and SIGTERM. Only SIGKILL prevents writing (trap cannot catch it).

### 2. Process group alive (PGID)

Check whether the process group is still running:

```bash
orch_pgid_alive "$pgid"
```

| Process group | Exit file | Result |
|---------------|-----------|--------|
| alive | absent | `running` |
| alive | present + match | `completed` or `failed` (per exit file) |
| dead | present + match | `completed` or `failed` (per exit file) |
| dead | absent | fall through to method 3 |
| dead | present + mismatch | fall through (stale file) |

The `pipelineStarted` flag tracks whether the pipeline state file was ever observed.
Prevents false `completed` when the state file hasn't been created yet.

### 3. Grace period (process dead, no exit file)

60-second grace period after process death. The exit handler may be writing the file,
or there's a race between termination and file system flush.

After grace period: fall through to PR status check.

### 4. PR status (fallback, provider-health-aware)

Before checking PR status, verify GitHub provider health:

| Provider | Action |
|----------|--------|
| `healthy` | Proceed with PR check |
| `degraded` | Return `running` (don't make PR-based judgments) |
| `hard_fault` | Return `running` (poll cycle should halt) |

PR check uses `orch_gh` (provider health wrapper):
- Merged PR exists -> `completed`
- Open PR exists, process dead -> `abnormal_exit`
- gh command failed -> `running` (don't judge on error)
- No PR at all -> `failed`

Always use `-R <owner/repo>` for explicit repo targeting. Avoid deprecated fields
like `projectCards` - use `number,title,state,body,url` only.

## Stall detection

`orch_detect_stall <area> <issue>` uses a multi-signal approach.

### Detection priority

1. **Heartbeat** (strongest): `.workspace/orchestrate/{area}/issue-{N}.heartbeat`
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
                   |-(exit file: ok)--------> completed
                   |-(exit file: fail)-------> failed
                   |-(abnormal exit, retry)--> dispatched (re-dispatch)
                   |-(abnormal exit, no retry)-> failed
                   +-(stall + dead + retry)--> dispatched (re-dispatch)
                   +-(stall + dead + exhausted)-> failed

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
