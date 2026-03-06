# Process lifecycle

## Headless pattern

Review and resolve run as synchronous `claude -p` subprocesses via `pipeline_run_headless()`. The pipeline blocks until exit, then checks GitHub API for results.

```
pipeline_run_headless(workdir, prompt, issue, area, stage)
  -> timeout $SEC claude -p --dangerously-skip-permissions ... "$prompt" > $LOG
  -> returns exit code: 0=success, 124=timeout, other=error
  -> ALWAYS check API after exit (result may exist even on non-zero exit)
```

| Stage | Tools | Max turns | Timeout |
|-------|-------|-----------|---------|
| review | `Bash,Read,Skill` | 15 | 900s |
| resolve | `Bash,Read,Edit,Write,Grep,Glob,Skill` | 25 | 900s |

## Self-healing

Per-stage retry via `pipeline_stage_retry()` (max 3). Log actions with `pipeline_recovery_log()`. On max retries -> `pipeline_format_escalation()` reports to user.

## State schema

```json
{
  "issue": 42, "area": "client", "pr": 99,
  "branch": "feat/issue-42-add-auth",
  "worktree": ".workspace/worktrees/issue-42",
  "agent": "claude",
  "step": "review", "reviewRound": 1, "lastReviewId": 0,
  "lastCommitSha": "{SHA}", "skipReview": false,
  "reviewLog": ".workspace/pipeline/logs/issue-42-review.log",
  "resolveLog": ".workspace/pipeline/logs/issue-42-resolve.log",
  "stageRetries": { "build": 0, "review": 0, "resolve": 0, "merge": 0 },
  "maxStageRetries": 3,
  "recoveryLog": [],
  "createdAt": "...", "updatedAt": "..."
}
```
