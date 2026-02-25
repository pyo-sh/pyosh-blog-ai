---
name: dev-pipeline
description: Orchestrate the full dev cycle — code, review, resolve — with automated tmux pane management and pipeline state tracking. Runs /dev-build, then triggers /dev-review and /dev-resolve in a sandboxed side pane. Activates on "/dev-pipeline", "run pipeline", "automated review", etc.
---

# Dev-Pipeline

Orchestrate: `/dev-build` → `/dev-review` → `/dev-resolve` → merge. Review/resolve run in a **sandboxed side pane** visible to the user. Pipeline state is tracked per-issue for crash recovery.

## Prerequisites

- Running inside a **tmux session** (check `$TMUX` env var)
- `claude` CLI available
- Claude Code sandbox configured (`/sandbox` → auto-allow mode recommended)

## Git Remote (same as dev-build)

| Area | Path | GitHub Repo |
|------|------|-------------|
| server | `server/` | `pyo-sh/pyosh-blog-be` |
| client | `client/` | `pyo-sh/pyosh-blog-fe` |

## Workflow

### 0. Check for Existing Pipeline State

```bash
STATE_FILE=".workspace/pipeline/issue-{N}.state.json"
```

If state file exists → **resume from last step** (see [recovery.md](references/recovery.md)).
If not → proceed to Step 1.

### 1. Run /dev-build (code + PR)

Execute `/dev-build` as normal. After PR is created:

```bash
mkdir -p .workspace/pipeline
```

Write state file:

```json
{
  "issue": {N},
  "area": "{client|server}",
  "pr": {PR#},
  "branch": "{type}/issue-{N}-{desc}",
  "worktree": ".workspace/worktrees/issue-{N}",
  "step": "review",
  "reviewRound": 1,
  "createdAt": "{ISO8601}",
  "updatedAt": "{ISO8601}"
}
```

### 2. Open Review Pane

Launch a sandboxed Claude in a new tmux pane on the right:

```bash
REVIEW_PANE=$(tmux split-window -h -P -F '#{pane_id}' \
  "cd $(pwd)/{area} && claude --sandbox -p 'Run /dev-review for PR #{PR#} in {area}. Repo: {repo}. After review, exit.' ; echo '[Review complete - press Enter to close]'; read")
```

Save `REVIEW_PANE` ID in state file for cleanup.

Update state:
```json
{ "step": "review", "reviewPane": "{pane_id}" }
```

### 3. Wait for Review Completion

Poll GitHub for review submission:

```bash
cd {area}
# Check every 30s for up to 15 minutes
gh api repos/{owner}/{repo}/pulls/{PR#}/reviews --jq '.[].state'
```

Expected states:
- `CHANGES_REQUESTED` → proceed to Step 4a
- `COMMENTED` (no CRITICAL) → proceed to Step 5
- No review yet → keep polling

### 4a. Trigger Resolve

Triggered by:
- Step 3: `CHANGES_REQUESTED` (has Critical) — fix CRITICAL + WARNING
- Step 5: "Fix & Re-review" — fix WARNING + SUGGESTION per user feedback
- Step 5: "Fix & Merge" — fix WARNING + SUGGESTION, **skip re-review after**

Kill the review pane (if still alive) and open a resolve pane:

```bash
tmux kill-pane -t "$REVIEW_PANE" 2>/dev/null

RESOLVE_PANE=$(tmux split-window -h -P -F '#{pane_id}' \
  "cd $(pwd)/{area}/.workspace/worktrees/issue-{N} && claude --sandbox -p 'Run /dev-resolve for PR #{PR#} in {area}. Repo: {repo}. Fix {target items per trigger}. After done, exit.' ; echo '[Resolve complete - press Enter to close]'; read")
```

Update state:
```json
{ "step": "resolve", "resolvePane": "{pane_id}", "skipReview": {true|false} }
```

- `skipReview: false` — normal flow (Step 3, Step 5 "Fix & Re-review")
- `skipReview: true` — "Fix & Merge" flow (Step 5)

### 4b. Wait for Resolve + Confirm Changes

Poll for new commits on the PR branch:

```bash
gh api repos/{owner}/{repo}/pulls/{PR#}/commits --jq '.[-1].sha'
```

When new commits appear:
1. Show diff to user: `gh pr diff {PR#}`
2. Check `skipReview` in state:
   - **`skipReview: true`** (from "Fix & Merge") → proceed directly to Step 6
   - **`skipReview: false`** → **Ask user** — choose one:
     - **"Apply & Re-review"** → go back to Step 2 (full re-review cycle)
     - **"Merge as-is"** → skip re-review, proceed to Step 6 (user accepts current state)
     - **"Manual edit"** → user edits code manually, then re-trigger from Step 2

Update state:
```json
{ "step": "review", "reviewRound": {N+1}, "skipReview": false }
```

### 5. No Critical Issues — User Decision

Present review summary to user:

```bash
gh api repos/{owner}/{repo}/pulls/{PR#}/reviews --jq '.[-1].body'
```

Show severity counts (Critical: 0, Warning: N, Suggestion: M).

**Ask user** — choose one:
- **"Merge"** → accept remaining Warning/Suggestion as-is, proceed to Step 6
- **"Fix & Re-review"** → go to Step 4a (resolve Warning/Suggestion, then full re-review)
- **"Fix & Merge"** → go to Step 4a variant: resolve only, **skip re-review**, proceed to Step 6 after resolve push

### 6. Merge + Cleanup

```bash
cd {area}
gh pr merge {PR#} --squash --delete-branch

# Clean up worktree (path from state file "worktree" field)
git worktree remove .workspace/worktrees/issue-{N}
git branch -d {type}/issue-{N}-{desc} 2>/dev/null

# Kill any remaining panes
tmux kill-pane -t "$REVIEW_PANE" 2>/dev/null
tmux kill-pane -t "$RESOLVE_PANE" 2>/dev/null

# Clean up message files created during review/resolve
rm -f .workspace/messages/pr-{PR#}-*.md
```

Update state:
```json
{ "step": "log" }
```

### 7. Record with /dev-log

Run `/dev-log` to record:
- Progress: pipeline execution summary
- Findings: any technical discoveries during review/resolve

### 8. Clean Up State

```bash
rm .workspace/pipeline/issue-{N}.state.json
```

Pipeline complete.

## State File Spec

Path: `.workspace/pipeline/issue-{N}.state.json`

| Field | Type | Description |
|-------|------|-------------|
| `issue` | number | GitHub Issue number |
| `area` | string | `client` or `server` |
| `pr` | number | PR number |
| `branch` | string | Branch name |
| `worktree` | string | Worktree path |
| `step` | string | `build`, `review`, `resolve`, `merge`, `log` |
| `reviewRound` | number | Current review iteration |
| `reviewPane` | string | tmux pane ID for review |
| `resolvePane` | string | tmux pane ID for resolve |
| `skipReview` | boolean | If true, skip re-review after resolve ("Fix & Merge" flow) |
| `createdAt` | string | ISO 8601 timestamp |
| `updatedAt` | string | ISO 8601 timestamp |

## Constraints

- **Never merge without user approval**
- **Never modify code in this session** — code changes happen only in /dev-build worktree or /dev-resolve pane
- **Always clean up tmux panes** on completion or failure
- **Always release state file** on pipeline completion
- On any unrecoverable error: save state, kill panes, report to user

## References

- [Recovery strategy](references/recovery.md) — crash recovery from state file
- [Pipeline shell helpers](scripts/pipeline-helpers.sh) — tmux and state management functions
