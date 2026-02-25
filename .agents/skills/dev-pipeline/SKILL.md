---
name: dev-pipeline
description: Orchestrate the full dev cycle — code, review, resolve — with automated tmux pane management and pipeline state tracking. Runs /dev-build, then triggers /dev-review and /dev-resolve in a sandboxed side pane. Activates on "/dev-pipeline", "run pipeline", "automated review", etc.
---

# Dev-Pipeline

Orchestrate: `/dev-build` → `/dev-review` → `/dev-resolve` → merge. Review/resolve run in a **sandboxed side pane**. State tracked per-issue for crash recovery.

> Requires tmux session (`$TMUX`). Git remote rules in `CLAUDE.md`.

## Agent Selection

Before starting the pipeline, **ask the user** which AI agent to use for side-pane tasks (review/resolve):

| Agent | CLI Command | Notes |
|-------|------------|-------|
| **Claude Code** | `claude --sandbox -p '{prompt}'` | Requires `claude` CLI |
| **Codex** | `codex -q '{prompt}'` | Requires `codex` CLI |

Store the choice in state as `"agent": "claude"` or `"agent": "codex"`. Use the corresponding CLI command for all side-pane operations (Steps 2, 4a).

## Workflow

### 0. Check Existing State

```bash
STATE_FILE=".workspace/pipeline/issue-{N}.state.json"
```

Exists → **resume** ([recovery.md](references/recovery.md)). Not exists → Step 1.

### 1. Run /dev-build

Execute `/dev-build`. After PR creation, write state:

```json
{
  "issue": 42,
  "area": "client",
  "pr": 99,
  "branch": "feat/issue-42-add-auth",
  "worktree": ".workspace/worktrees/issue-42",
  "agent": "claude",
  "step": "review",
  "reviewRound": 1,
  "skipReview": false,
  "createdAt": "2026-01-01T00:00:00Z",
  "updatedAt": "2026-01-01T00:00:00Z"
}
```

### 2. Open Review Pane

Use `pipeline_open_pane()` from [pipeline-helpers.sh](scripts/pipeline-helpers.sh):

```bash
# Claude Code
REVIEW_PANE=$(tmux split-window -h -P -F '#{pane_id}' \
  "cd $(pwd)/{area} && claude --sandbox -p 'Run /dev-review for PR #{PR#}. After review, exit.' ; read")
# Codex
REVIEW_PANE=$(tmux split-window -h -P -F '#{pane_id}' \
  "cd $(pwd)/{area} && codex -q 'Run /dev-review for PR #{PR#}. After review, exit.' ; read")
```

Use the agent selected in Step 0/1 (stored in state `agent` field).

Save pane ID in state → `"step": "review", "reviewPane": "{pane_id}"`.

### 3. Wait for Review

Poll `gh api repos/{owner}/{repo}/pulls/{PR#}/reviews --jq '.[].state'` every 30s (max 15min).

- `CHANGES_REQUESTED` → Step 4a
- `COMMENTED` (no CRITICAL) → Step 5
- No review → keep polling

### 4a. Trigger Resolve

Triggered by:
- Step 3: `CHANGES_REQUESTED` — fix CRITICAL + WARNING
- Step 5: "Fix & Re-review" — fix WARNING + SUGGESTION, then re-review
- Step 5: "Fix & Merge" — fix only, **skip re-review** (`skipReview: true`)

Kill review pane, open resolve pane in worktree:

```bash
tmux kill-pane -t "$REVIEW_PANE" 2>/dev/null
# Claude Code
RESOLVE_PANE=$(tmux split-window -h -P -F '#{pane_id}' \
  "cd $(pwd)/{area}/.workspace/worktrees/issue-{N} && claude --sandbox -p 'Run /dev-resolve for PR #{PR#}. After done, exit.' ; read")
# Codex
RESOLVE_PANE=$(tmux split-window -h -P -F '#{pane_id}' \
  "cd $(pwd)/{area}/.workspace/worktrees/issue-{N} && codex -q 'Run /dev-resolve for PR #{PR#}. After done, exit.' ; read")
```

State → `"step": "resolve", "resolvePane": "{pane_id}"`.

### 4b. Wait for Resolve

Poll for new commits: `gh api repos/{owner}/{repo}/pulls/{PR#}/commits --jq '.[-1].sha'`.

When new commits appear:
1. Show diff: `gh pr diff {PR#}`
2. If `skipReview: true` → Step 6
3. If `skipReview: false` → **ask user**: "Apply & Re-review" (→ Step 2) | "Merge as-is" (→ Step 6) | "Manual edit" (→ user edits, then Step 2)

### 5. No Critical — User Decision

Show review summary + severity counts.

**Ask user**:
- **"Merge"** → Step 6
- **"Fix & Re-review"** → Step 4a (resolve + re-review)
- **"Fix & Merge"** → Step 4a with `skipReview: true`

### 6. Merge + Cleanup

```bash
cd {area}
gh pr merge {PR#} --squash --delete-branch
git worktree remove .workspace/worktrees/issue-{N}
git branch -d {branch} 2>/dev/null
tmux kill-pane -t "$REVIEW_PANE" 2>/dev/null
tmux kill-pane -t "$RESOLVE_PANE" 2>/dev/null
rm -f .workspace/messages/pr-{PR#}-*.md
```

State → `"step": "log"`.

### 7. Record with /dev-log

Run `/dev-log` — progress summary + any findings.

### 8. Clean Up State

```bash
rm .workspace/pipeline/issue-{N}.state.json
```

## Constraints

- **Never merge without user approval**
- **Never modify code in this session** — code changes happen only in /dev-build or /dev-resolve pane
- **Always clean up tmux panes** on completion or failure
- **Always release state file** on pipeline completion
- On unrecoverable error: save state, kill panes, report to user

## References

- [Recovery strategy](references/recovery.md) — crash recovery from state file
- [Pipeline helpers](scripts/pipeline-helpers.sh) — tmux and state management functions
