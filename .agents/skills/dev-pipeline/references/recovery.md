# Pipeline Recovery Strategy

## Overview

When the orchestrating AI crashes or disconnects, the pipeline can be resumed from the last saved step using the state file and GitHub state.

## Recovery Flow

On startup, check for existing state files:

```bash
ls .workspace/pipeline/issue-*.state.json 2>/dev/null
```

If found, read the state file and resume based on `step` field.

## Step-by-Step Recovery

### step: "build"

PR may or may not exist.

```bash
cd {area}
gh pr list --head {branch} --json number,state --jq '.[0]'
```

- PR exists + open → update step to `review`, resume
- PR exists + merged → update step to `log`, resume
- No PR → re-run `/dev-build` from existing worktree (at `.workspace/worktrees/issue-{N}`)

### step: "review"

First check if the review pane from state is still alive:

```bash
cd {area}
source scripts/pipeline-helpers.sh
if [ -n "{reviewPane}" ] && pipeline_pane_alive "{reviewPane}"; then
  # Pane still running — just poll (with health monitoring)
  REVIEW_ID=$(pipeline_poll_review "{area_dir}" {PR#} {lastReviewId} 900 "{reviewPane}")
else
  # Pane dead or absent — check for already-submitted review
  REVIEW_ID=$(pipeline_poll_review "{area_dir}" {PR#} {lastReviewId} 0)
fi
```

- `REVIEW_ID` != "TIMEOUT" → `eval "$(pipeline_analyze_review ...)"`, update `lastReviewId`, proceed per Step 3 decision logic
- "TIMEOUT" (no new review) → re-trigger review pane via `pipeline_open_pane_verified()`

### step: "resolve"

First check if the resolve pane from state is still alive:

```bash
cd {area}
source scripts/pipeline-helpers.sh
if [ -n "{resolvePane}" ] && pipeline_pane_alive "{resolvePane}"; then
  # Pane still running — poll for commits (with health monitoring)
  NEW_SHA=$(pipeline_poll_commits "{area_dir}" {PR#} "{lastCommitSha}" 900 "{resolvePane}")
else
  # Pane dead — check for already-pushed commits
  REVIEW_DATE=$(gh api repos/{owner}/{repo}/pulls/{PR#}/reviews --jq '.[-1].submitted_at')
  LAST_COMMIT_DATE=$(gh api repos/{owner}/{repo}/pulls/{PR#}/commits --jq '.[-1].commit.committer.date')
fi
```

- Pane alive + new commits → proceed to re-review (Step 2)
- Pane alive + PANE_DEAD during poll → re-trigger resolve pane via `pipeline_open_pane_verified()`
- Pane dead + new commits after review → proceed to re-review (Step 2)
- Pane dead + no new commits → re-trigger resolve pane via `pipeline_open_pane_verified()`

### step: "merge"

```bash
cd {area}
gh pr view {PR#} --json state --jq '.state'
```

- `MERGED` → proceed to log
- `OPEN` → ask user for merge approval again

### step: "log"

Simply re-run `/dev-log`. Idempotent — safe to run multiple times.

## Orphaned Pane Cleanup

After recovery, previously opened tmux panes may be dead or orphaned. Always attempt cleanup:

```bash
tmux kill-pane -t "{reviewPane}" 2>/dev/null
tmux kill-pane -t "{resolvePane}" 2>/dev/null
```

## Pane Failure Recovery

When `pipeline_open_pane_verified()` or health-monitored polling returns a failure:

### PANE_DEAD or RETRY_FAILED

1. Verify worktree path exists:
   ```bash
   source scripts/pipeline-helpers.sh
   WORKTREE_PATH=$(pipeline_resolve_worktree_path {issue} {area})
   ```
2. Check agent binary: `which claude` or `which codex`
3. Check tmux session: `tmux list-sessions`
4. If all OK, retry via `pipeline_open_pane_verified()` with resolved path
5. If retry fails again, report diagnostics to user

### PATH_INVALID

Worktree not found at current or legacy paths.

1. Check `git worktree list` from the area repo — worktree may have been moved
2. If worktree exists elsewhere, use its path directly
3. If worktree is gone, re-run `/dev-build` from the existing branch

## Stale State Files

If a state file exists but its PR is already merged and logged:

```bash
rm .workspace/pipeline/issue-{N}.state.json
```

Report to user that the pipeline was already completed.
