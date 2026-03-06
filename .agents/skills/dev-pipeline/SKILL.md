---
name: dev-pipeline
description: Orchestrate the full dev cycle - code, review, resolve - with headless subprocess execution and self-healing. Runs /dev-build, then triggers /dev-review and /dev-resolve as synchronous headless subprocesses. Activates on "/dev-pipeline", "run pipeline", "automated review", etc.
---

# Dev-Pipeline

Orchestrate: `/dev-build` -> `/dev-review` -> `/dev-resolve` -> merge. Review/resolve run as **headless `claude -p` subprocesses**. Self-healing with auto-retry on known failures.

> Area definitions, directory/repo mappings, worktree paths: [monorepo-layout.md](../../references/monorepo-layout.md)
> Source helpers: `source scripts/pipeline-helpers.sh`
> State schema and headless execution details: [process-lifecycle.md](references/process-lifecycle.md)
> Recovery strategy: [recovery.md](references/recovery.md)

## Workflow

### 0. Check existing state

Check `.workspace/pipeline/{area}/issue-{N}.state.json`. If exists -> show `step` and `pr`, ask **"Resume?"** or **"Start fresh?"**. If resume -> jump to current `step`. Each step self-validates on entry.

### 1. Run /dev-build

**`cd {area}` first.** Sync before starting:

```bash
cd {area}
git fetch origin
git rebase origin/main || git merge origin/main
```

**Recovery entry**: If `step: "build"`, check PR via `gh pr list --head {branch} --json number,state --jq '.[0]'`. PR open -> Step 2. PR merged -> Step 7. No PR -> re-run `/dev-build`.

After PR creation, capture initial commit SHA and write state. -> [process-lifecycle.md](references/process-lifecycle.md) for state schema.

### 2. Run review (headless)

**Recovery entry**: `pipeline_check_review_exists` first. Found -> skip to Step 3.

Run headless review and check API after exit. -> [process-lifecycle.md#headless-pattern](references/process-lifecycle.md) for the run-then-check pattern.

```bash
LOG=$(pipeline_run_headless "$MONOREPO_ROOT" \
  "/dev-review for PR #{PR#} in {area} repo ({owner}/{repo}). After review, exit." \
  "$ISSUE" "$AREA" "review")
RC=$?
REVIEW_ID=$(pipeline_check_review_exists "{area_dir}" {PR#} {lastReviewId})
```

- Review found -> Step 3 (success regardless of exit code)
- Not found + `RC!=0` -> self-heal with `pipeline_stage_retry` / `pipeline_recovery_log`, retry or escalate
- Not found + `RC=0` -> unexpected, report to user

### 3. Process review

Fetch review with `pipeline_fetch_review`. Count severities (`[CRITICAL]`, `[WARNING]`, `[SUGGESTION]`). Update `lastReviewId`, reset `stageRetries.review`.

- `CHANGES_REQUESTED` or `CRITICAL > 0` -> Step 4
- `CRITICAL = 0` or `APPROVED` -> Step 5
- `PENDING` / `DISMISSED` -> report to user, stop

### 4. Run resolve (headless)

**Recovery entry**: `pipeline_check_new_commits` first. Found -> skip to Step 4b.

Same headless pattern as Step 2 but with `"resolve"` stage and worktree path:

```bash
WORKTREE_PATH=$(pipeline_resolve_worktree_path "$ISSUE" "$AREA")
LOG=$(pipeline_run_headless "$WORKTREE_PATH" \
  "/dev-resolve for PR #{PR#} in {area} repo ({owner}/{repo}). Worktree: ${WORKTREE_PATH}. After done, exit." \
  "$ISSUE" "$AREA" "resolve")
```

After exit -> `pipeline_check_new_commits`. Found -> Step 4b. Not found -> self-heal.

### 4b. Process resolve result

Update `lastCommitSha`, reset `stageRetries.resolve`. Show diff (`gh pr diff {PR#}`).

- `skipReview: true` -> Step 6
- `skipReview: false` -> ask user: **"Re-review"** (-> Step 2) | **"Merge as-is"** (-> Step 6) | **"Manual edit"** (user edits, then Step 2)

### 5. No critical - user decision

Show review summary. Ask user: **"Merge"** -> Step 6 | **"Fix & Re-review"** -> Step 4 | **"Fix & Merge"** -> Step 4 with `skipReview: true`.

### 6. Merge + cleanup

**Recovery entry**: Check `gh pr view {PR#} --json state -q .state`. `MERGED` -> skip to cleanup. `OPEN` -> ask user for merge approval.

```bash
cd {area}
gh pr merge {PR#} --squash --delete-branch
```

If merge fails -> self-heal: `git fetch origin && git rebase origin/main || git merge origin/main && git push`, retry. Max 3 retries, then escalate with `pipeline_format_escalation`.

After merge, validate state is `MERGED`, then:

```bash
git fetch --prune
pipeline_cleanup "$ISSUE" "$AREA" "{branch}"
```

State -> `"step": "log"`.

### 7. Record + clean up

Run `/dev-log`, then delete state file.

## Constraints

- **Never merge without user approval**
- **Never modify code in this session** - code changes happen only in /dev-build or headless /dev-resolve
- On unrecoverable error: save state, report to user with `pipeline_format_escalation`
