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
7. **Review dispatch always goes through `pipeline_run_review`**. Never run `codex exec review` or `claude -p` for review directly in the pipeline session.

> Source helpers: `source .agents/skills/dev-pipeline/scripts/pipeline-helpers.sh`
> Canonical worktree path: `.workspace/worktrees/{area}/issue-{N}`
> Canonical state path: `.workspace/pipeline/{area}/issue-{N}.state.json`

## State machine

| From step | To step | Trigger | Turn break? |
|---|---|---|---|
| `build` | `review_dispatch` | /dev-build + PR created | No |
| `review_dispatch` | `review_wait` | Background review dispatched | **Yes** - end turn |
| `review_wait` | `review_process` | Task-notification + review found on GitHub | No |
| `review_wait` | `review_dispatch` | Task-notification + review not found + job failed | No |
| `review_process` | `resolve` | Critical > 0 or Warning > 0 | No |
| `review_process` | `merge` | Critical = 0 and Warning = 0 | No |
| `resolve` | `review_dispatch` | skipReview=false, fixes applied | No |
| `resolve` | `merge` | skipReview=true | No |
| `merge` | `log` | PR merged | No |
| `log` | (done) | Cleanup complete | No |

Only `review_dispatch -> review_wait` requires a turn break.
All other transitions must happen within the same turn.

## Required runtime shape

For any long-running `pipeline_run_review` Bash call, the Bash tool invocation itself must use **background mode**. The helper remains synchronous, but the outer tool call must not be foreground-blocked because the Bash-tool timeout can be shorter than Claude's internal timeout.

After launching the background Bash call for review (step `review_dispatch`), **end your turn immediately and wait for the task-notification**. Do not sleep, poll, or output intermediate status. Resume processing only after you receive the completion notification. This is the only pipeline step where ending the turn between steps is correct - it is required to avoid forbidden sleep/poll behaviour while waiting for a long-running background process.

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

Before calling `/dev-build`, write a minimal state file to establish a recovery entry point:

```bash
WORKTREE_PATH=$(pipeline_worktree_path "$ISSUE" "$AREA")
cat > "$STATE_FILE" <<EOF
{"version":2,"issue":$ISSUE,"area":"$AREA","pr":0,"branch":"","paths":{"skillCwd":"$MONOREPO_ROOT","repoDir":"$REPO_DIR","worktreeDir":"$WORKTREE_PATH"},"step":"build","lastReviewId":0,"lastCommitSha":"","skipReview":false,"reviewResolveRound":0,"maxReviewResolveRounds":5,"stageRetries":{"build":0,"review_dispatch":0,"review_wait":0,"review_process":0,"resolve":0,"merge":0},"maxStageRetries":3,"reviewJob":{"runId":"","status":"idle","startedAt":null,"finishedAt":null,"tool":"","model":""},"transitionLog":[]}
EOF
```

Then run `/dev-build` as usual.

After `/dev-build` returns, immediately (without ending your turn) read the PR number and branch, then update state to `step: "review_dispatch"`:

```bash
WORKTREE_PATH=$(pipeline_worktree_path "$ISSUE" "$AREA")
BRANCH=$(git -C "$WORKTREE_PATH" rev-parse --abbrev-ref HEAD)
PR=$(gh pr list -R "$REPO" --head "$BRANCH" --json number --jq '.[0].number')
LAST_COMMIT_SHA=$(git -C "$WORKTREE_PATH" rev-parse HEAD)
```

Then write the full state:

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
  "step": "review_dispatch",
  "lastReviewId": 0,
  "lastCommitSha": "<sha>",
  "skipReview": false,
  "reviewResolveRound": 0,
  "maxReviewResolveRounds": 5,
  "stageRetries": { "build": 0, "review_dispatch": 0, "review_wait": 0, "review_process": 0, "resolve": 0, "merge": 0 },
  "maxStageRetries": 3,
  "reviewJob": { "runId": "", "status": "idle", "startedAt": null, "finishedAt": null, "tool": "", "model": "" },
  "transitionLog": []
}
```

After writing state, immediately proceed to Step 2a (review dispatch). Do not output a progress message to the user and do not end your turn between pipeline steps.

### 2a. Review dispatch (`step: review_dispatch`)

Check GitHub for an existing review first:

```bash
REVIEW_ID=$(pipeline_check_review_exists "$AREA" "$PR" "$LAST_REVIEW_ID")
RC=$?
[ $RC -eq 2 ] && { echo "[pipeline] gh API error checking reviews - abort"; return 1; }
```

If found (`RC=0`), skip directly to Step 3 (`review_process`).

Otherwise write job metadata and dispatch the background review:

```bash
pipeline_state_update "$ISSUE" "$AREA" '.step = "review_wait"'
LOG=$(pipeline_run_review "$ISSUE" "$AREA" "$PR" "$TOOL" "$MODEL")
```

Tool defaults to `claude`. When `TOOL=codex`, review runs via `codex exec review --base origin/main` from the worktree, and the helper posts the output to GitHub automatically. Note: codex writes all output (progress + final review) to stderr; stdout is always empty. The helper redirects stderr to the log file and discards stdout.

Rules:
- This Bash call itself must run in background mode.
- For `claude`: never pass the worktree path as the process cwd.
- For `codex`: the helper runs from the worktree (needed for `--base origin/main` diff).
- Always treat GitHub API as source of truth after exit.
- **End turn immediately after dispatching.** Do not sleep, poll, or output intermediate status.

### 2b. Review wait (`step: review_wait`)

Entered on resume after task-notification. Check GitHub and job metadata:

```bash
REVIEW_ID=$(pipeline_check_review_exists "$AREA" "$PR" "$LAST_REVIEW_ID")
RC=$?
[ $RC -eq 2 ] && { echo "[pipeline] gh API error checking reviews - abort"; return 1; }
```

Outcome:

```bash
if [ -n "$REVIEW_ID" ]; then
  # Review found -> Step 3 (review_process)
else
  JOB_STATUS=$(pipeline_state_read "$ISSUE" "$AREA" | jq -r '.reviewJob.status')
  if [ "$JOB_STATUS" = "failed" ]; then
    # Job failed + no review -> pipeline_stage_retry, set step=review_dispatch, re-enter 2a
  else
    # Headless succeeded but no review posted -> pipeline_format_escalation, report to user
  fi
fi
```

### 3. Process review (`step: review_process`)

Fetch review:

```bash
REVIEW_JSON=$(pipeline_fetch_review "$AREA" "$PR" "$REVIEW_ID")
```

Update:
- `.lastReviewId = REVIEW_ID`
- `.stageRetries.review_dispatch = 0`
- `.stageRetries.review_wait = 0`
- `.stageRetries.review_process = 0`

Parse using the helper:

```bash
REVIEW_BODY=$(printf '%s' "$REVIEW_JSON" | jq -r '.body')
COUNTS=$(pipeline_parse_review_body "$REVIEW_BODY")
RC=$?
[ $RC -ne 0 ] && { pipeline_format_escalation "$ISSUE" "$AREA" "review_process"; return 1; }
CRITICAL=$(printf '%s' "$COUNTS" | jq -r '.critical')
WARNING=$(printf '%s' "$COUNTS" | jq -r '.warning')
SUGGESTION=$(printf '%s' "$COUNTS" | jq -r '.suggestion')
```

If `pipeline_parse_review_body` fails, escalate immediately - do not attempt to continue with zero counts.

Then decide:

```
if Pending or dismissed:
  stop and report

if Critical > 0 or Warning > 0:
  if reviewResolveRound >= maxReviewResolveRounds (5):
    if headless (non-interactive): auto-abort, pipeline_format_escalation, exit
    else: ask user: continue / merge as-is / abort
  else:
    update .step = "resolve", .reviewResolveRound += 1
    go to Step 4 (auto)

if Suggestion > 0 (but Critical = 0 and Warning = 0):
  if reviewResolveRound >= maxReviewResolveRounds (5):
    if headless (non-interactive): update .step = "merge", auto-merge (suggestions are non-blocking)
    else: ask user: merge as-is / fix suggestions / abort
  else:
    AI decides:
      a) suggestions are trivial or debatable -> update .step = "merge", auto-merge (Step 6)
      b) suggestions are valid and worth fixing -> update .reviewResolveRound += 1, resolve then re-review (Step 4, set skipReview = false)
      c) suggestions are valid but no re-review needed -> update .reviewResolveRound += 1, resolve then merge (Step 4, set skipReview = true)

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

Decision table based on `LOCAL_HEAD` vs `LAST_COMMIT_SHA` and working tree state:

| LOCAL_HEAD vs LAST_COMMIT_SHA | Working tree | Action |
|---|---|---|
| mismatch (LOCAL_HEAD != SHA) | clean | Push LOCAL_HEAD, skip to 4d |
| mismatch (LOCAL_HEAD != SHA) | dirty | STOP - report uncommitted changes, do not push |
| match | dirty/staged | STOP - report partial resolve from previous session |
| match | clean | Continue with remote check -> 4a |

Check the remote:

```bash
NEW_SHA=$(pipeline_check_new_commits "$AREA" "$PR" "$LAST_COMMIT_SHA")
RC=$?
[ $RC -eq 2 ] && { echo "[pipeline] gh API error checking commits - abort"; return 1; }
```

If found (`RC=0`), use `NEW_SHA` from stdout directly, update `.lastCommitSha` and `.stageRetries.resolve = 0`, show diff, and ask user (skip 4a-4c since context is lost).

Otherwise resolve directly in this pipeline session:

#### 4a. Read review and inline comments

```bash
REVIEW_JSON=$(pipeline_fetch_review "$AREA" "$PR" "$REVIEW_ID")
[ -z "$REVIEW_JSON" ] && { echo "[pipeline] failed to fetch review - abort resolve"; return 1; }
COMMENTS_JSON=$(pipeline_fetch_review_comments "$AREA" "$PR" "$REVIEW_ID")
```

If `pipeline_fetch_review` fails, abort the resolve step (`pipeline_stage_retry`, then retry). `pipeline_fetch_review_comments` failure is non-fatal (inline comments are supplementary; the review body contains severity labels).

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
- `skipReview: false` -> update `.step = "review_dispatch"`, go to Step 2a (auto re-review)

### 5. Round limit reached (`reviewResolveRound >= maxReviewResolveRounds`)

This step is entered from Step 3 when the review-resolve loop has exhausted its rounds but Critical/Warning items remain.

If headless (non-interactive): `pipeline_format_escalation`, exit (do not auto-merge with unresolved Critical/Warning).

Otherwise show the latest review summary and the round count, then ask the user:
- Continue -> reset `.reviewResolveRound = 0`, `.stageRetries.review = 0`, `.stageRetries.resolve = 0`, update `.step = "resolve"`, go to Step 4
- Merge as-is -> update `.step = "merge"`, go to Step 6
- Abort -> stop and report

### 6. Merge (`step: merge`)

Recovery entry:

```bash
gh pr view "$PR" -R "$(pipeline_repo_name "$AREA")" --json state --jq '.state'
```

If already `MERGED`, go to Step 7. If `CLOSED`, stop and report (PR was closed without merging).

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
```

Update `.step = "log"` immediately after successful merge (before cleanup). This ensures recovery can resume from Step 7 if a crash occurs.

On failure:
- `pipeline_stage_retry`
- `pipeline_recovery_log`
- retry up to max
- then `pipeline_format_escalation`

### 7. Log + cleanup (`step: log`)

Run `/dev-log` first, then clean up:

```bash
pipeline_cleanup "$ISSUE" "$AREA" "$BRANCH" "$PR"
```

`pipeline_cleanup` deletes the state file as its last action. Only call it after `/dev-log` succeeds.

## Constraints

- **Do not end your turn between pipeline steps.** After each step completes, immediately proceed to the next step without outputting a progress summary to the user. Only report at major milestones (build complete with PR link, final merge success) or on error. **Exception: Step 2a (`review_dispatch`).** After launching the background Bash call for `pipeline_run_review`, end your turn and wait for the task-notification. Do not sleep or poll. Resume from the task-notification by reading state, then continue with the outcome check in Step 2b (`review_wait`) and Step 3 (`review_process`).
- **Auto-merge** is allowed when: (1) review has Critical=0 AND Warning=0, or (2) user explicitly approves in Step 5
- **User approval required** when: review-resolve loop reaches `maxReviewResolveRounds` with Critical/Warning still present (Step 5)
- Source edits in the pipeline session are allowed only during the resolve step (Step 4b), and only in the issue worktree
- Build-phase source edits happen only in `/dev-build`
- Git metadata operations required for merge are allowed
- On unrecoverable error: save state, then report with `pipeline_format_escalation`
