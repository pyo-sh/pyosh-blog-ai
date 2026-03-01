# Pipeline Recovery

Resume from state file when orchestrator crashes or disconnects.

## Entry

```bash
ls .workspace/pipeline/*/issue-*.state.json 2>/dev/null
```

If found → read state, resume by `step` field. First, clean orphaned panes:

```bash
tmux kill-pane -t "{reviewPane}" 2>/dev/null
tmux kill-pane -t "{resolvePane}" 2>/dev/null
```

## By Step

### step: "build"

```bash
cd {area} && gh pr list --head {branch} --json number,state --jq '.[0]'
```

- PR open → step=`review`, resume
- PR merged → step=`log`, resume
- No PR → re-run `/dev-build` from `.workspace/worktrees/issue-{N}`

### step: "review"

```bash
source scripts/pipeline-helpers.sh
if [ -n "{reviewPane}" ] && pipeline_pane_alive "{reviewPane}"; then
  REVIEW_ID=$(pipeline_poll_review "{area_dir}" {PR#} {lastReviewId} 900 "{reviewPane}")
else
  REVIEW_ID=$(pipeline_poll_review "{area_dir}" {PR#} {lastReviewId} 0)
fi
```

- Review found → analyze, proceed per Step 3 decision logic
- TIMEOUT → re-trigger via `pipeline_open_pane_verified()`

### step: "resolve"

```bash
source scripts/pipeline-helpers.sh
if [ -n "{resolvePane}" ] && pipeline_pane_alive "{resolvePane}"; then
  NEW_SHA=$(pipeline_poll_commits "{area_dir}" {PR#} "{lastCommitSha}" 900 "{resolvePane}")
else
  REVIEW_DATE=$(gh api repos/{owner}/{repo}/pulls/{PR#}/reviews --jq '.[-1].submitted_at')
  LAST_COMMIT_DATE=$(gh api repos/{owner}/{repo}/pulls/{PR#}/commits --jq '.[-1].commit.committer.date')
fi
```

- New commits after review → Step 2 (re-review)
- PANE_DEAD during poll → re-trigger via `pipeline_open_pane_verified()`
- No new commits, pane dead → re-trigger resolve pane

### step: "merge"

```bash
cd {area} && gh pr view {PR#} --json state --jq '.state'
```

- `MERGED` → proceed to log
- `OPEN` → ask user for merge approval

### step: "log"

Re-run `/dev-log`. Idempotent.

## Pane Failure Recovery

### PANE_DEAD / RETRY_FAILED

1. `pipeline_resolve_worktree_path {issue} {area}` — verify path
2. `which claude` or `which codex` — verify agent binary
3. `tmux list-sessions` — verify tmux
4. All OK → retry via `pipeline_open_pane_verified()`
5. Still fails → report diagnostics to user

### PATH_INVALID

1. `git worktree list` from area repo — find actual location
2. Found → use path directly
3. Gone → re-run `/dev-build` from existing branch

## Stale State

If PR already merged and logged → `rm .workspace/pipeline/{area}/issue-{N}.state.json`, report completed.
