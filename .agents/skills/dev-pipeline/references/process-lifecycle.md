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

## Step subcommands

High-level CLI interface that replaces inline Bash in SKILL.md (v3).

### Invocation

`python3 -m dev_pipeline step <name> --issue N --area A [--phase setup|finalize] [--review-id N] [--tool T] [--decision D]`

### Output contract

stdout emits 2 lines:
- `action:<action_name>` - SKILL.md routing key
- `data:<json>` - structured payload

stderr emits human-readable log messages.

### Two patterns

1. **Single call** (fully automated): `review-dispatch`, `review-wait`, `review-process`, `suggestion-decide`, `merge`
   - Python handles the entire logic, returns action for next step routing
2. **Two-phase** (AI skill invocation required): `build`, `resolve`, `log`
   - `--phase setup`: preparation before AI skill (fetch, state init, review fetch)
   - AI performs `/dev-build`, code fixes, or `/dev-log`
   - `--phase finalize`: cleanup after AI skill (state update, commit, push)

## State schema

See [python-migration-spec.md](python-migration-spec.md) for the canonical v2 schema.
