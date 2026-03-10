# Process lifecycle

## Headless pattern (review only)

Review runs as a synchronous `claude -p` subprocess via `review_runner.dispatch_review()`. The pipeline blocks until exit, then checks GitHub API for results.

```
review_runner.dispatch_review(skill_cwd, prompt, issue, area, stage, repo_dir, worktree_dir, pr [, model])
  -> timeout $SEC claude -p [--model $MODEL] --dangerously-skip-permissions ... "$prompt" > $LOG
  -> returns exit code: 0=success, 124=timeout, other=error
  -> ALWAYS check API after exit (result may exist even on non-zero exit)
  -> model: optional. Pass to ensure review uses the same model as the pipeline.
```

| Stage | Tools | Max turns | Timeout |
|-------|-------|-----------|---------|
| review | `Bash,Read,Skill` | 15 | 900s |

## Direct resolve

Resolve runs directly in the pipeline session. The pipeline reads the review via `github_client.fetch_review()` and `github_client.fetch_review_comments()`, then applies fixes using Read/Edit/Write tools in the issue worktree. After committing and pushing, it posts a response comment to the PR.

## Merge queue

When multiple pipelines run in parallel (via orchestrator), only one can merge at a time per area. Prevents rebase conflicts from simultaneous merges.

```
merge_lock.MergeLock.acquire(area, issue)
  -> mkdir .workspace/pipeline/{area}/merge.lock  (atomic)
  -> writes issue, timestamp to lock dir
  -> if held: polls every 10s, max 300s
  -> stale lock (TTL 1800s elapsed): auto-reclaims
  -> returns: 0=acquired, 1=timeout

merge_lock.MergeLock.release(area)
  -> rm -rf .workspace/pipeline/{area}/merge.lock
```

**Always release the lock** - both on success and failure. If a process holds the lock and does not release it within the TTL (1800s), the next acquirer auto-reclaims it.

## Self-healing

Per-stage retry via `state_store.stage_retry()` (max 3). Log actions with `state_store.recovery_log_append()`. On max retries -> `controller.format_escalation()` reports to user.

## State schema

```json
{
  "version": 2,
  "issue": 42, "area": "client", "pr": 99,
  "branch": "feat/issue-42-add-auth",
  "paths": {
    "skillCwd": "/workspace",
    "repoDir": "/workspace/client",
    "worktreeDir": "/workspace/.workspace/worktrees/client/issue-42"
  },
  "step": "review", "lastReviewId": 0,
  "lastCommitSha": "{SHA}", "skipReview": false,
  "reviewResolveRound": 0, "maxReviewResolveRounds": 5,
  "stageRetries": { "build": 0, "review": 0, "resolve": 0, "merge": 0 },
  "maxStageRetries": 3,
  "recoveryLog": [],
  "createdAt": "...", "updatedAt": "..."
}
```
