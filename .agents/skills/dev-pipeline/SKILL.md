---
name: dev-pipeline
description: Orchestrate /dev-build -> /dev-review -> resolve (direct) -> merge for a monorepo with area-scoped worktrees. Headless review sessions start from monorepo root so skills resolve correctly; resolve runs directly in the pipeline session. Activates on "/dev-pipeline", "run pipeline", "automated review", etc.
---

# Dev-Pipeline

## Non-negotiable invariants

1. **Claude headless review cwd is always monorepo root** (`$MONOREPO_ROOT`). Never start `claude -p` from a worktree.
2. **Feature-branch file edits and feature-branch git sync happen only in the issue worktree**.
3. **gh commands use explicit repo selection** (`-R owner/name`) or an explicit repo dir.
4. **Merge lock is held inside one CLI call** (`python -m dev_pipeline merge`), not across multiple Bash tool calls.
5. **All transient files are area-scoped** (`state`, `logs`, `messages`, `worktrees`).
6. **Resolve runs directly in the pipeline session**, not as a headless sub-agent.
7. **Review dispatch always goes through `python -m dev_pipeline run`**. Never run `codex exec review` or `claude -p` for review directly in the pipeline session.

> Python CLI: `cd .agents/skills/dev-pipeline/scripts && python -m dev_pipeline <cmd>`
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

## Workflow

### 0. Initialize / resume

Run:

```bash
cd .agents/skills/dev-pipeline/scripts
python -m dev_pipeline init --area "$AREA"
STATE_FILE="/workspace/.workspace/pipeline/${AREA}/issue-${ISSUE}.state.json"
```

If state exists, read it and resume from `.step`. Do not recompute paths ad hoc; derive them from the area and issue number using the canonical patterns.

### 1. Build (`step: build`)

Resolve the canonical repo dir and repo name inline:

```bash
case "$AREA" in
  client)    REPO_DIR=/workspace/client  REPO=pyo-sh/pyosh-blog-fe ;;
  server)    REPO_DIR=/workspace/server  REPO=pyo-sh/pyosh-blog-be ;;
  workspace) REPO_DIR=/workspace         REPO=pyo-sh/pyosh-blog-ai ;;
esac
WORKTREE_PATH="/workspace/.workspace/worktrees/${AREA}/issue-${ISSUE}"

git -C "$REPO_DIR" fetch origin
git -C "$REPO_DIR" rebase origin/main || git -C "$REPO_DIR" merge origin/main
```

Before calling `/dev-build`, write a minimal state file to establish a recovery entry point:

```bash
cat > "$STATE_FILE" <<EOF
{"version":2,"issue":$ISSUE,"area":"$AREA","pr":0,"branch":"","paths":{"skillCwd":"$MONOREPO_ROOT","repoDir":"$REPO_DIR","worktreeDir":"$WORKTREE_PATH"},"step":"build","lastReviewId":0,"lastCommitSha":"","skipReview":false,"reviewResolveRound":0,"maxReviewResolveRounds":5,"stageRetries":{"build":0,"review_dispatch":0,"review_wait":0,"review_process":0,"resolve":0,"merge":0},"maxStageRetries":3,"reviewJob":{"runId":"","status":"idle","startedAt":null,"finishedAt":null,"tool":"","model":""},"transitionLog":[]}
EOF
```

Then run `/dev-build` as usual.

After `/dev-build` returns, immediately (without ending your turn) read the PR number and branch, then update state to `step: "review_dispatch"`:

```bash
WORKTREE_PATH="/workspace/.workspace/worktrees/${AREA}/issue-${ISSUE}"
BRANCH=$(git -C "$WORKTREE_PATH" rev-parse --abbrev-ref HEAD)
PR=$(gh pr list -R "$REPO" --head "$BRANCH" --json number --jq '.[0].number')
LAST_COMMIT_SHA=$(git -C "$WORKTREE_PATH" rev-parse HEAD)
```

Update the state file (same schema as the one-liner above) with the actual `pr`, `branch`, `lastCommitSha` values and `step: "review_dispatch"`. Immediately proceed to Step 2a.

### 2a. Review dispatch (`step: review_dispatch`)

Check GitHub for an existing review first:

```bash
cd .agents/skills/dev-pipeline/scripts
REVIEW_ID=$(python -m dev_pipeline check-review --area "$AREA" --pr "$PR" --last-review-id "$LAST_REVIEW_ID")
RC=$?
[ $RC -eq 2 ] && { echo "[pipeline] gh API error checking reviews - abort"; return 1; }
```

If found (`RC=0`), skip directly to Step 3 (`review_process`).

Otherwise write job metadata and dispatch the background review:

```bash
cd .agents/skills/dev-pipeline/scripts
python -m dev_pipeline state-update --issue "$ISSUE" --area "$AREA" --step review_wait
python -m dev_pipeline run --issue "$ISSUE" --area "$AREA" --pr "$PR" ${TOOL:+--tool "$TOOL"}
```

Tool defaults to `claude`.

Rules:
- This Bash call must use **background mode** (Bash-tool timeout may be shorter than review timeout).
- **End turn immediately after dispatching.** This is the only turn break in the pipeline. Resume only on task-notification. Do not sleep, poll, or output status.
- After resume, treat GitHub API as source of truth.

### 2b. Review wait (`step: review_wait`)

Entered on resume after task-notification. Check GitHub and job metadata:

```bash
cd .agents/skills/dev-pipeline/scripts
REVIEW_ID=$(python -m dev_pipeline check-review --area "$AREA" --pr "$PR" --last-review-id "$LAST_REVIEW_ID")
RC=$?
[ $RC -eq 2 ] && { echo "[pipeline] gh API error checking reviews - abort"; return 1; }
```

Outcome:

```bash
if [ -n "$REVIEW_ID" ]; then
  # Review found -> Step 3 (review_process)
else
  JOB_STATUS=$(cd .agents/skills/dev-pipeline/scripts && python -m dev_pipeline state --issue "$ISSUE" --area "$AREA" | jq -r '.reviewJob.status')
  if [ "$JOB_STATUS" = "failed" ]; then
    # Job failed + no review -> stage-retry, update step, re-enter 2a
    cd .agents/skills/dev-pipeline/scripts
    python -m dev_pipeline stage-retry --issue "$ISSUE" --area "$AREA" --stage review_dispatch
    python -m dev_pipeline state-update --issue "$ISSUE" --area "$AREA" --step review_dispatch
  else
    # Headless succeeded but no review posted -> escalation, report to user
    cd .agents/skills/dev-pipeline/scripts && python -m dev_pipeline escalation --issue "$ISSUE" --area "$AREA" --step review_wait
  fi
fi
```

### 3. Process review (`step: review_process`)

Fetch review:

```bash
REVIEW_JSON=$(gh api "repos/${REPO}/pulls/${PR}/reviews/${REVIEW_ID}")
```

Update:
- `.lastReviewId = REVIEW_ID`
- `.stageRetries.review_dispatch = 0`
- `.stageRetries.review_wait = 0`
- `.stageRetries.review_process = 0`

Parse using the CLI:

```bash
REVIEW_BODY=$(printf '%s' "$REVIEW_JSON" | jq -r '.body')
COUNTS=$(cd .agents/skills/dev-pipeline/scripts && printf '%s' "$REVIEW_BODY" | python -m dev_pipeline parse-review)
RC=$?
if [ $RC -ne 0 ]; then
  cd .agents/skills/dev-pipeline/scripts && python -m dev_pipeline escalation --issue "$ISSUE" --area "$AREA" --step review_process
  return 1
fi
CRITICAL=$(printf '%s' "$COUNTS" | jq -r '.critical')
WARNING=$(printf '%s' "$COUNTS" | jq -r '.warning')
SUGGESTION=$(printf '%s' "$COUNTS" | jq -r '.suggestion')
```

If `parse-review` fails, escalate immediately - do not attempt to continue with zero counts.

Then decide:

```
if Pending or dismissed:
  stop and report

if Critical > 0 or Warning > 0:
  if reviewResolveRound >= maxReviewResolveRounds (5):
    if headless (non-interactive): auto-abort, escalation CLI, exit
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
WORKTREE_PATH="/workspace/.workspace/worktrees/${AREA}/issue-${ISSUE}"
if [ ! -d "$WORKTREE_PATH" ]; then
  echo "[pipeline] worktree not found - escalate"
  cd .agents/skills/dev-pipeline/scripts && python -m dev_pipeline escalation --issue "$ISSUE" --area "$AREA" --step resolve
  return 1
fi
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
cd .agents/skills/dev-pipeline/scripts
NEW_SHA=$(python -m dev_pipeline check-commits --area "$AREA" --pr "$PR" --last-commit-sha "$LAST_COMMIT_SHA")
RC=$?
[ $RC -eq 2 ] && { echo "[pipeline] gh API error checking commits - abort"; return 1; }
```

If found (`RC=0`), use `NEW_SHA` from stdout directly, update `.lastCommitSha` and `.stageRetries.resolve = 0`, show diff, and ask user (skip 4a-4c since context is lost).

Otherwise resolve directly in this pipeline session:

#### 4a. Read review and inline comments

```bash
REVIEW_JSON=$(gh api "repos/${REPO}/pulls/${PR}/reviews/${REVIEW_ID}")
[ -z "$REVIEW_JSON" ] && { echo "[pipeline] failed to fetch review - abort resolve"; return 1; }
COMMENTS_JSON=$(gh api "repos/${REPO}/pulls/${PR}/reviews/${REVIEW_ID}/comments")
```

If the review fetch fails, abort the resolve step (use `stage-retry` CLI, then retry). Comments fetch failure is non-fatal (inline comments are supplementary; the review body contains severity labels).

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
  git -C "$WORKTREE_PATH" push --force-with-lease
fi
```

If no changes were staged (all items skipped or already fixed), skip directly to 4d without pushing.

#### 4c. Post response comment

Write and post a response comment summarizing fixed and skipped items:

```bash
MSG_FILE="/workspace/.workspace/messages/${AREA}-pr-${PR}-response.md"
mkdir -p "$(dirname "$MSG_FILE")"
# Write response body to MSG_FILE (Fixed table | Skipped table)
gh pr comment "$PR" -R "$REPO" --body-file "$MSG_FILE"
rm -f "$MSG_FILE"
```

#### 4d. Update state and decide next step

Get the new commit SHA. Use local git as the primary source (avoids GitHub API propagation delay after push):

```bash
NEW_SHA=$(git -C "$WORKTREE_PATH" rev-parse HEAD)
```

Update state:

```bash
cd .agents/skills/dev-pipeline/scripts
python -m dev_pipeline state-update --issue "$ISSUE" --area "$AREA" --last-commit-sha "$NEW_SHA"
```

Then:
- `skipReview: true` -> update `.step = "merge"`, go to Step 6
- `skipReview: false` -> update `.step = "review_dispatch"`, go to Step 2a (auto re-review)

### 5. Round limit reached (`reviewResolveRound >= maxReviewResolveRounds`)

This step is entered from Step 3 when the review-resolve loop has exhausted its rounds but Critical/Warning items remain.

If headless (non-interactive):

```bash
cd .agents/skills/dev-pipeline/scripts && python -m dev_pipeline escalation --issue "$ISSUE" --area "$AREA" --step resolve
```

Exit (do not auto-merge with unresolved Critical/Warning).

Otherwise show the latest review summary and the round count, then ask the user:
- Continue -> reset `.reviewResolveRound = 0`, `.stageRetries.review_dispatch = 0`, `.stageRetries.review_wait = 0`, `.stageRetries.review_process = 0`, `.stageRetries.resolve = 0`, update `.step = "resolve"`, go to Step 4
- Merge as-is -> update `.step = "merge"`, go to Step 6
- Abort -> stop and report

### 6. Merge (`step: merge`)

Recovery entry - use `REPO_DIR` and `REPO` from Step 1 area mapping:

```bash
gh pr view "$PR" -R "$REPO" --json state --jq '.state'
```

If already `MERGED`, go to Step 7. If `CLOSED`, stop and report.

Otherwise merge with the **single CLI call** (handles lock, rebase, squash internally):

```bash
cd .agents/skills/dev-pipeline/scripts
python -m dev_pipeline merge --issue "$ISSUE" --area "$AREA" --pr "$PR" --branch "$BRANCH"
```

On success, fetch and prune:

```bash
git -C "$REPO_DIR" fetch --prune
```

Update `.step = "log"` immediately after successful merge (before cleanup). This ensures recovery can resume from Step 7 if a crash occurs.

On failure:

```bash
cd .agents/skills/dev-pipeline/scripts
python -m dev_pipeline stage-retry --issue "$ISSUE" --area "$AREA" --step merge
```

Retry up to max, then escalate:

```bash
cd .agents/skills/dev-pipeline/scripts
python -m dev_pipeline escalation --issue "$ISSUE" --area "$AREA" --step merge
```

### 7. Log + cleanup (`step: log`)

Run `/dev-log` first, then clean up:

```bash
cd .agents/skills/dev-pipeline/scripts
python -m dev_pipeline cleanup --issue "$ISSUE" --area "$AREA" --branch "$BRANCH" --pr "$PR"
```

`cleanup` deletes the state file as its last action. Only call it after `/dev-log` succeeds.

## Constraints

- **Do not end your turn between pipeline steps** except Step 2a (review dispatch). Report only at milestones (PR created, merge success) or errors.
- **Auto-merge** when Critical=0 AND Warning=0, or user approves in Step 5.
- **User approval required** when review-resolve loop reaches `maxReviewResolveRounds` with Critical/Warning (Step 5).
- Source edits only in resolve step (4b), only in the issue worktree. Build edits happen in `/dev-build`.
- On unrecoverable error: save state, then `python -m dev_pipeline escalation --issue "$ISSUE" --area "$AREA" --step "<step>"`.
