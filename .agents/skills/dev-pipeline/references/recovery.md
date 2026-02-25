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
- No PR → re-run `/dev-build` from existing worktree

### step: "review"

Review may or may not be submitted.

```bash
cd {area}
gh api repos/{owner}/{repo}/pulls/{PR#}/reviews --jq '.[-1].state'
```

- Review exists → parse result, proceed to resolve or merge approval
- No review → re-trigger review pane

### step: "resolve"

Check if new commits were pushed after the review.

```bash
cd {area}
REVIEW_DATE=$(gh api repos/{owner}/{repo}/pulls/{PR#}/reviews --jq '.[-1].submitted_at')
LAST_COMMIT_DATE=$(gh api repos/{owner}/{repo}/pulls/{PR#}/commits --jq '.[-1].commit.committer.date')
```

- New commits after review → proceed to re-review (step 2)
- No new commits → re-trigger resolve pane

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

## Stale State Files

If a state file exists but its PR is already merged and logged:

```bash
rm .workspace/pipeline/issue-{N}.state.json
```

Report to user that the pipeline was already completed.
