---
name: dev-pipeline
description: Orchestrate the full dev cycle - code, review, resolve - with headless subprocess execution and self-healing. Runs /dev-build, then triggers /dev-review and /dev-resolve as synchronous headless subprocesses. Activates on "/dev-pipeline", "run pipeline", "automated review", etc.
---

# Dev-Pipeline

Orchestrate: `/dev-build` -> `/dev-review` -> `/dev-resolve` -> merge. Review/resolve run as **headless `claude -p` subprocesses**. State tracked per-issue for crash recovery. Self-healing with auto-retry on known failures.

> Area definitions, directory/repo mappings, worktree paths: [monorepo-layout.md](../../references/monorepo-layout.md)
> Source helpers: `source scripts/pipeline-helpers.sh`

## Workflow

### 0. Check existing state

Check for existing pipeline:

```bash
STATE_FILE=".workspace/pipeline/{area}/issue-{N}.state.json"
```

If state file exists -> show the current `step` and `pr` to the user, then ask: **"Resume from step X?"** or **"Start fresh?"**. If "Start fresh" -> delete state file, proceed to Step 1. If "Resume" -> jump directly to the current `step`. Each step self-validates on entry.

Not exists -> Step 1.

### 1. Run /dev-build

**`cd {area}` first.** Sync with remote before starting:

```bash
cd {area}
git fetch origin
git rebase origin/main || git merge origin/main
```

**Recovery entry**: If state says `step: "build"`, check PR status first:

```bash
cd {area} && gh pr list --head {branch} --json number,state --jq '.[0]'
```

- PR open -> update state to `step: "review"`, jump to Step 2
- PR merged -> update state to `step: "log"`, jump to Step 7
- No PR -> re-run `/dev-build` from `.workspace/worktrees/issue-{N}`

After PR creation, capture the initial commit SHA and write state:

```bash
LAST_COMMIT_SHA=$(cd {area_dir} && gh api "repos/{owner}/{repo}/pulls/{PR#}/commits" --jq '.[-1].sha')
if [ -z "$LAST_COMMIT_SHA" ] || [ "$LAST_COMMIT_SHA" = "null" ]; then
  echo "ERROR: Failed to capture initial commit SHA for PR #{PR#}. Aborting."
  exit 1
fi
```

```json
{
  "issue": 42, "area": "client", "pr": 99,
  "branch": "feat/issue-42-add-auth",
  "worktree": ".workspace/worktrees/issue-42",
  "agent": "claude",
  "step": "review", "reviewRound": 1, "lastReviewId": 0,
  "lastCommitSha": "{LAST_COMMIT_SHA}",
  "skipReview": false,
  "reviewLog": ".workspace/pipeline/logs/issue-42-review.log",
  "resolveLog": ".workspace/pipeline/logs/issue-42-resolve.log",
  "stageRetries": { "build": 0, "review": 0, "resolve": 0, "merge": 0 },
  "maxStageRetries": 3,
  "recoveryLog": [],
  "createdAt": "2026-01-01T00:00:00Z", "updatedAt": "2026-01-01T00:00:00Z"
}
```

### 2. Run review (headless)

**Recovery entry**: Check if a review already exists:

```bash
REVIEW_ID=$(pipeline_check_review_exists "{area_dir}" {PR#} {lastReviewId})
```

If found -> skip to Step 3 (process review).

If not found, run review as a synchronous headless subprocess:

```bash
LOG=$(pipeline_run_headless "$MONOREPO_ROOT" \
  "/dev-review for PR #{PR#} in {area} repo ({owner}/{repo}). After review, exit." \
  "$ISSUE" "$AREA" "review")
RC=$?
```

- `RC=0` -> check API for review, continue to Step 3
- `RC=124` (timeout) -> log, attempt self-healing (Step 2a)
- `RC!=0` -> log, attempt self-healing (Step 2a)

After subprocess exits (any exit code), always check API first:

```bash
REVIEW_ID=$(pipeline_check_review_exists "{area_dir}" {PR#} {lastReviewId})
```

If review found -> success regardless of exit code, continue to Step 3.
If not found and `RC=0` -> unexpected, report to user.
If not found and `RC!=0` -> Step 2a.

### 2a. Review self-healing

```bash
if pipeline_stage_retry "$ISSUE" "$AREA" "review"; then
  pipeline_recovery_log "$ISSUE" "$AREA" "review" "exit code $RC" "re-run headless" "retrying"
  # -> retry Step 2
else
  pipeline_format_escalation "$ISSUE" "$AREA" "review"
  # -> report to user, stop
fi
```

### 3. Process review

Fetch and read review:

```bash
pipeline_fetch_review "{area_dir}" {PR#} "$REVIEW_ID"
```

Read `state` and severity counts (`[CRITICAL]`, `[WARNING]`, `[SUGGESTION]`). Update state:

```bash
pipeline_state_update "$ISSUE" "$AREA" \
  ".lastReviewId = ${REVIEW_ID} | .stageRetries.review = 0"
```

Decision:
- `CHANGES_REQUESTED` or `COMMENTED` + `CRITICAL > 0` -> Step 4
- `COMMENTED` + `CRITICAL = 0` -> Step 5
- `APPROVED` -> Step 5 (treat as no critical)
- `PENDING` or `DISMISSED` -> report unexpected state to user, stop

### 4. Run resolve (headless)

**Recovery entry**: Check if new commits already exist:

```bash
NEW_SHA=$(pipeline_check_new_commits "{area_dir}" {PR#} "{lastCommitSha}")
```

If found -> skip to Step 4b (process commits).

If not found, run resolve as a synchronous headless subprocess:

```bash
WORKTREE_PATH=$(pipeline_resolve_worktree_path "$ISSUE" "$AREA")
LOG=$(pipeline_run_headless "$WORKTREE_PATH" \
  "/dev-resolve for PR #{PR#} in {area} repo ({owner}/{repo}). Worktree: ${WORKTREE_PATH}. After done, exit." \
  "$ISSUE" "$AREA" "resolve")
RC=$?
```

After subprocess exits, check API:

```bash
NEW_SHA=$(pipeline_check_new_commits "{area_dir}" {PR#} "{lastCommitSha}")
```

If found -> Step 4b. If not found -> self-healing (same pattern as Step 2a but for "resolve" stage).

### 4b. Process resolve result

Update state:

```bash
pipeline_state_update "$ISSUE" "$AREA" \
  ".lastCommitSha = \"${NEW_SHA}\" | .stageRetries.resolve = 0"
```

Show diff (`gh pr diff {PR#}`).

- `skipReview: true` -> Step 6
- `skipReview: false` -> ask user: **"Re-review"** (reset `stageRetries.review` to 0 -> Step 2) | **"Merge as-is"** (-> Step 6) | **"Manual edit"** (user edits, then Step 2)

### 5. No critical - user decision

Show review summary.

Ask user: **"Merge"** -> Step 6 | **"Fix & Re-review"** -> Step 4 | **"Fix & Merge"** -> Step 4 with `skipReview: true`.

### 6. Merge + cleanup

**Recovery entry**: Check PR state first:

```bash
PR_STATE=$(cd {area} && gh pr view {PR#} --json state -q .state)
```

- `MERGED` -> skip merge, proceed to cleanup
- `OPEN` -> ask user for merge approval, then merge

Merge with self-healing:

```bash
cd {area}
gh pr merge {PR#} --squash --delete-branch
```

If merge fails:

```bash
# Self-healing: sync and retry
if pipeline_stage_retry "$ISSUE" "$AREA" "merge"; then
  git fetch origin
  git rebase origin/main || git merge origin/main
  git push
  pipeline_recovery_log "$ISSUE" "$AREA" "merge" "merge failed" "fetch+rebase+push" "retrying"
  # retry gh pr merge
else
  pipeline_format_escalation "$ISSUE" "$AREA" "merge"
  # -> report to user, stop
fi
```

After successful merge, validate:

```bash
PR_STATE=$(gh pr view {PR#} --json state -q .state)
if [ "$PR_STATE" != "MERGED" ]; then
  echo "ERROR: PR #{PR#} state is '$PR_STATE', expected 'MERGED'."
  pipeline_state_update "$ISSUE" "$AREA" '.step = "merge-failed"'
  exit 1
fi
```

Cleanup (run inside `{area}` dir):

```bash
git fetch --prune
pipeline_cleanup "$ISSUE" "$AREA" "{branch}"
```

State -> `"step": "log"`.

### 7. Record + clean up

Run `/dev-log`, then `rm .workspace/pipeline/{area}/issue-{N}.state.json`.

## Constraints

- **Never merge without user approval**
- **Never modify code in this session** - code changes happen only in /dev-build or headless /dev-resolve
- On unrecoverable error: save state, report to user with `pipeline_format_escalation`

## References

- [Recovery strategy](references/recovery.md)
- [Process lifecycle](references/process-lifecycle.md)
- [Pipeline helpers](scripts/pipeline-helpers.sh)
