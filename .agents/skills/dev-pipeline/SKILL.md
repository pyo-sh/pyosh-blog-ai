---
name: dev-pipeline
description: Orchestrate /dev-build -> /dev-review -> /dev-resolve -> merge for a monorepo with area-scoped worktrees. Headless Claude sessions always start from monorepo root so skills resolve correctly; code edits always happen in the issue worktree. Activates on "/dev-pipeline", "run pipeline", "automated review", etc.
---

# Dev-Pipeline

## Non-negotiable invariants

1. **Claude headless cwd is always monorepo root** (`$MONOREPO_ROOT`). Never start `claude -p` from a worktree.
2. **Feature-branch file edits and feature-branch git sync happen only in the issue worktree**.
3. **gh commands use explicit repo selection** (`-R owner/name`) or an explicit repo dir.
4. **Merge lock is held inside one helper call** (`pipeline_merge_pr`), not across multiple Bash tool calls.
5. **All transient files are area-scoped** (`state`, `logs`, `messages`, `worktrees`).

> Source helpers: `source .agents/skills/dev-pipeline/scripts/pipeline-helpers.sh`
> Canonical worktree path: `.workspace/worktrees/{area}/issue-{N}`
> Canonical state path: `.workspace/pipeline/{area}/issue-{N}.state.json`

## Required runtime shape

For any long-running `pipeline_run_review` or `pipeline_run_resolve` Bash call, the Bash tool invocation itself must use **background mode**. The helper remains synchronous, but the outer tool call must not be foreground-blocked because the Bash-tool timeout can be shorter than Claude's internal timeout.

## Workflow

### 0. Initialize / resume

Run:

```bash
source .agents/skills/dev-pipeline/scripts/pipeline-helpers.sh
pipeline_init "$AREA"
STATE_FILE=$(pipeline_state_path "$ISSUE" "$AREA")
```

If state exists, read it and resume from `.step`. Do not recompute paths ad hoc; use helper functions.

### 1. Build (`step: build`)

Use the canonical repo dir:

```bash
REPO_DIR=$(pipeline_repo_dir "$AREA")
REPO=$(pipeline_repo_name "$AREA")

git -C "$REPO_DIR" fetch origin
git -C "$REPO_DIR" rebase origin/main || git -C "$REPO_DIR" merge origin/main
```

Then run `/dev-build` as usual. After PR creation, write state with at least:

```json
{
  "version": 2,
  "issue": 42,
  "area": "client",
  "pr": 129,
  "branch": "feat/issue-42-add-auth",
  "paths": {
    "skillCwd": "/workspace",
    "repoDir": "/workspace/client",
    "worktreeDir": "/workspace/.workspace/worktrees/client/issue-42"
  },
  "step": "review",
  "lastReviewId": 0,
  "lastCommitSha": "<sha>",
  "skipReview": false,
  "stageRetries": { "build": 0, "review": 0, "resolve": 0, "merge": 0 },
  "maxStageRetries": 3
}
```

### 2. Review (`step: review`)

Recovery entry:

```bash
REVIEW_ID=$(pipeline_check_review_exists "$AREA" "$PR" "$LAST_REVIEW_ID")
RC=$?
[ $RC -eq 2 ] && { echo "[pipeline] gh API error checking reviews - abort"; return 1; }
```

If found (`RC=0`), skip to Step 3.

Otherwise start headless review **from monorepo root** using the stage-specific wrapper:

```bash
LOG=$(pipeline_run_review "$ISSUE" "$AREA" "$PR" "$MODEL")
RC=$?
REVIEW_ID=$(pipeline_check_review_exists "$AREA" "$PR" "$LAST_REVIEW_ID")
```

Rules:
- This Bash call itself must run in background mode.
- Never pass the worktree path as Claude's process cwd.
- Always treat GitHub API as source of truth after exit.

Outcome:
- Review found -> Step 3
- No review + non-zero exit -> retry / recovery
- No review + zero exit -> unexpected failure; escalate

### 3. Process review (`step: review`)

Fetch review:

```bash
REVIEW_JSON=$(pipeline_fetch_review "$AREA" "$PR" "$REVIEW_ID")
```

Update:
- `.lastReviewId = REVIEW_ID`
- `.stageRetries.review = 0`

Then decide:
- `CHANGES_REQUESTED` or 1+ Critical -> Step 4
- Approved / zero Critical -> Step 5
- Pending / dismissed -> stop and report

### 4. Resolve (`step: resolve`)

Recovery entry:

```bash
NEW_SHA=$(pipeline_check_new_commits "$AREA" "$PR" "$LAST_COMMIT_SHA")
RC=$?
[ $RC -eq 2 ] && { echo "[pipeline] gh API error checking commits - abort"; return 1; }
```

If found (`RC=0`), skip to Step 4b.

Otherwise run the resolve wrapper:

```bash
WORKTREE_PATH=$(pipeline_resolve_worktree_path "$ISSUE" "$AREA")
LOG=$(pipeline_run_resolve "$ISSUE" "$AREA" "$PR" "$MODEL")
RC=$?
NEW_SHA=$(pipeline_check_new_commits "$AREA" "$PR" "$LAST_COMMIT_SHA")
```

Rules:
- The Claude process still starts from `$MONOREPO_ROOT`.
- The prompt and exported env vars tell `/dev-resolve` which repo dir and worktree dir to use.
- All file edits must happen in `WORKTREE_PATH`.
- This Bash call itself must run in background mode.

### 4b. Process resolve result (`step: resolve`)

Update:
- `.lastCommitSha = NEW_SHA`
- `.stageRetries.resolve = 0`

Show PR diff:

```bash
gh pr diff "$PR" -R "$(pipeline_repo_name "$AREA")"
```

Then:
- `skipReview: true` -> Step 6
- otherwise ask the user: Re-review / Merge as-is / Manual edit

### 5. No critical issues

Show review summary and ask:
- Merge -> Step 6
- Fix & Re-review -> Step 4
- Fix & Merge -> set `skipReview=true`, then Step 4

### 6. Merge (`step: merge`)

Never merge without user approval.

Recovery entry:

```bash
gh pr view "$PR" -R "$(pipeline_repo_name "$AREA")" --json state --jq '.state'
```

If already `MERGED`, go to Step 7.

Otherwise merge with the **single helper**:

```bash
pipeline_merge_pr "$ISSUE" "$AREA" "$PR" "$BRANCH"
```

Important:
- Do **not** acquire the merge lock in one Bash call and release it in another.
- Do **not** run `gh pr merge` from the issue worktree.
- Feature-branch sync/rebase/push happens in the worktree.
- `gh pr merge` runs from the canonical repo dir.
- The helper will use `git push --force-with-lease` automatically only when history diverged.

On success:

```bash
git -C "$(pipeline_repo_dir "$AREA")" fetch --prune
pipeline_cleanup "$ISSUE" "$AREA" "$BRANCH"
```

On failure:
- `pipeline_stage_retry`
- `pipeline_recovery_log`
- retry up to max
- then `pipeline_format_escalation`

### 7. Log + cleanup (`step: log`)

Run `/dev-log`, then delete the state file only after `/dev-log` succeeds.

## Constraints

- Never merge without user approval
- Never edit source files in the pipeline session itself; source edits happen only in `/dev-build` or headless `/dev-resolve`
- Git metadata operations required for merge are allowed
- On unrecoverable error: save state, then report with `pipeline_format_escalation`
