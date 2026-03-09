---
name: dev-pipeline
description: Orchestrate /dev-build -> /dev-review -> resolve (direct) -> merge for a monorepo with area-scoped worktrees. Headless review sessions start from monorepo root so skills resolve correctly; resolve runs directly in the pipeline session. Activates on "/dev-pipeline", "run pipeline", "automated review", etc.
---

# Dev-Pipeline

## Non-negotiable invariants

1. **Claude headless review cwd is always monorepo root** (`$MONOREPO_ROOT`). Never start `claude -p` from a worktree.
2. **Feature-branch file edits and feature-branch git sync happen only in the issue worktree**.
3. **gh commands use explicit repo selection** (`-R owner/name`) or an explicit repo dir.
4. **Merge lock is held inside one helper call** (`pipeline_merge_pr`), not across multiple Bash tool calls.
5. **All transient files are area-scoped** (`state`, `logs`, `messages`, `worktrees`).
6. **Resolve runs directly in the pipeline session**, not as a headless sub-agent.

> Source helpers: `source .agents/skills/dev-pipeline/scripts/pipeline-helpers.sh`
> Canonical worktree path: `.workspace/worktrees/{area}/issue-{N}`
> Canonical state path: `.workspace/pipeline/{area}/issue-{N}.state.json`

## Required runtime shape

For any long-running `pipeline_run_review` Bash call, the Bash tool invocation itself must use **background mode**. The helper remains synchronous, but the outer tool call must not be foreground-blocked because the Bash-tool timeout can be shorter than Claude's internal timeout.

## Workflow

### 0. Initialize / resume

Run:

```bash
source .agents/skills/dev-pipeline/scripts/pipeline-helpers.sh
pipeline_init "$AREA"
STATE_FILE=$(pipeline_state_path "$ISSUE" "$AREA")
```

If state exists, read it and resume from `.step`. Do not recompute paths ad hoc; use helper functions. If the state has no `.version` field or `.version < 2`, discard it and start fresh (v1 schema is incompatible).

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
  "reviewResolveRound": 0,
  "maxReviewResolveRounds": 5,
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
REVIEW_RC=$?
[ $REVIEW_RC -eq 2 ] && { echo "[pipeline] gh API error checking reviews after headless run - abort"; return 1; }
```

Rules:
- This Bash call itself must run in background mode.
- Never pass the worktree path as Claude's process cwd.
- Always treat GitHub API as source of truth after exit.

Outcome (combine `RC` from headless run and `REVIEW_RC` from API check):

```bash
if [ -n "$REVIEW_ID" ]; then
  # Review found -> Step 3
elif [ $RC -ne 0 ]; then
  # Headless failed + no review -> pipeline_stage_retry, then retry Step 2
else
  # Headless succeeded but no review posted -> pipeline_format_escalation, report to user
fi
```

### 3. Process review (`step: review`)

Fetch review:

```bash
REVIEW_JSON=$(pipeline_fetch_review "$AREA" "$PR" "$REVIEW_ID")
```

Update:
- `.lastReviewId = REVIEW_ID`
- `.stageRetries.review = 0`

Parse the review summary table to extract severity counts (`CRITICAL`, `WARNING`, `SUGGESTION`).

Then decide:

```
if Pending or dismissed:
  stop and report

if Critical > 0 or Warning > 0:
  if reviewResolveRound >= maxReviewResolveRounds (5):
    ask user: continue / merge as-is / abort
  else:
    update .step = "resolve", .reviewResolveRound += 1
    go to Step 4 (auto)

if Suggestion > 0 (but Critical = 0 and Warning = 0):
  AI decides:
    a) suggestions are trivial or debatable -> auto-merge (Step 6)
    b) suggestions are valid and worth fixing -> resolve then re-review (Step 4, set skipReview = false)
    c) suggestions are valid but no re-review needed -> resolve then merge (Step 4, set skipReview = true)

if all counts = 0 (clean review):
  auto-merge -> update .step = "merge", go to Step 6
```

### 4. Resolve (`step: resolve`) - direct

Resolve worktree path first (needed by all sub-steps including recovery):

```bash
WORKTREE_PATH=$(pipeline_resolve_worktree_path "$ISSUE" "$AREA")
RC=$?
[ $RC -eq 3 ] && { echo "[pipeline] worktree not found - escalate"; pipeline_format_escalation "$ISSUE" "$AREA" "resolve"; return 1; }
```

Recovery entry - check local worktree first, then GitHub API:

```bash
LOCAL_HEAD=$(git -C "$WORKTREE_PATH" rev-parse HEAD 2>/dev/null || true)
```

If `LOCAL_HEAD` is empty, the worktree is corrupt - escalate and abort.

If `LOCAL_HEAD` differs from `$LAST_COMMIT_SHA` and the working tree is clean (`git -C "$WORKTREE_PATH" diff --quiet && git -C "$WORKTREE_PATH" diff --cached --quiet`), a local commit exists (possibly unpushed). Push it and skip to 4d:

```bash
pipeline_push_branch_safely "$WORKTREE_PATH"
```

If `LOCAL_HEAD` differs but the working tree is dirty, report to the user for manual resolution (uncommitted changes from a previous session may exist).

Otherwise (LOCAL_HEAD matches LAST_COMMIT_SHA), check for dirty/staged state first. If `git -C "$WORKTREE_PATH" diff --quiet && git -C "$WORKTREE_PATH" diff --cached --quiet` fails, report to the user (partial resolve from a previous session may exist). Then check the remote:

```bash
NEW_SHA=$(pipeline_check_new_commits "$AREA" "$PR" "$LAST_COMMIT_SHA")
RC=$?
[ $RC -eq 2 ] && { echo "[pipeline] gh API error checking commits - abort"; return 1; }
```

If found (`RC=0`), use `NEW_SHA` from stdout directly, update `.lastCommitSha`, show diff, and ask user (skip 4a-4c since context is lost).

Otherwise resolve directly in this pipeline session:

#### 4a. Read review and inline comments

```bash
REVIEW_JSON=$(pipeline_fetch_review "$AREA" "$PR" "$REVIEW_ID")
COMMENTS_JSON=$(pipeline_fetch_review_comments "$AREA" "$PR" "$REVIEW_ID")
```

Parse the review body for severity labels (`[CRITICAL]`, `[WARNING]`, `[SUGGESTION]`) and inline comments for file-level feedback.

#### 4b. Fix code in the worktree

Rules:
- All source-file edits must happen in `WORKTREE_PATH`. Use Read/Edit/Write tools with absolute worktree paths.
- `[CRITICAL]` and `[WARNING]` items must be fixed.
- `[SUGGESTION]` items should be fixed if valid, otherwise skip with a reason.
- Do not change code unrelated to the review feedback.

After applying fixes, commit and push (skip if no changes):

```bash
git -C "$WORKTREE_PATH" add -A
if ! git -C "$WORKTREE_PATH" diff --cached --quiet; then
  git -C "$WORKTREE_PATH" commit -m "fix: address review comments (#${ISSUE})"
  pipeline_push_branch_safely "$WORKTREE_PATH"
fi
```

If no changes were staged (all items skipped or already fixed), skip directly to 4d without pushing.

#### 4c. Post response comment

Write and post a response comment summarizing fixed and skipped items:

```bash
MSG_FILE=$(pipeline_message_path "$AREA" "$PR" response)
# Write response body to MSG_FILE (Fixed table | Skipped table)
gh pr comment "$PR" -R "$(pipeline_repo_name "$AREA")" --body-file "$MSG_FILE"
rm -f "$MSG_FILE"
```

#### 4d. Update state and decide next step

Get the new commit SHA. Use local git as the primary source (avoids GitHub API propagation delay after push):

```bash
NEW_SHA=$(git -C "$WORKTREE_PATH" rev-parse HEAD)
```

Update:
- `.lastCommitSha = NEW_SHA`
- `.stageRetries.resolve = 0`

Then:
- `skipReview: true` -> update `.step = "merge"`, go to Step 6
- `skipReview: false` -> update `.step = "review"`, go to Step 2 (auto re-review)

### 5. Round limit reached (`reviewResolveRound >= maxReviewResolveRounds`)

This step is entered from Step 3 when the review-resolve loop has exhausted its rounds but Critical/Warning items remain.

Show the latest review summary and the round count, then ask the user:
- Continue -> reset `.reviewResolveRound = 0`, update `.step = "resolve"`, go to Step 4
- Merge as-is -> update `.step = "merge"`, go to Step 6
- Abort -> stop and report

### 6. Merge (`step: merge`)

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
pipeline_cleanup "$ISSUE" "$AREA" "$BRANCH" "$PR"
```

On failure:
- `pipeline_stage_retry`
- `pipeline_recovery_log`
- retry up to max
- then `pipeline_format_escalation`

### 7. Log + cleanup (`step: log`)

Run `/dev-log`, then delete the state file only after `/dev-log` succeeds.

## Constraints

- **Auto-merge** is allowed when: (1) review has Critical=0 AND Warning=0, or (2) user explicitly approves in Step 5
- **User approval required** when: review-resolve loop reaches `maxReviewResolveRounds` with Critical/Warning still present (Step 5)
- Source edits in the pipeline session are allowed only during the resolve step (Step 4b), and only in the issue worktree
- Build-phase source edits happen only in `/dev-build`
- Git metadata operations required for merge are allowed
- On unrecoverable error: save state, then report with `pipeline_format_escalation`
