---
name: dev-pipeline
description: Orchestrate the full dev cycle — code, review, resolve — with automated tmux pane management and pipeline state tracking. Runs /dev-build, then triggers /dev-review and /dev-resolve in a sandboxed side pane. Activates on "/dev-pipeline", "run pipeline", "automated review", etc.
---

# Dev-Pipeline

Orchestrate: `/dev-build` → `/dev-review` → `/dev-resolve` → merge. Review/resolve run in a **sandboxed side pane**. State tracked per-issue for crash recovery.

> Requires tmux session (`$TMUX`). Git remote rules in `CLAUDE.md`.

## Agent Selection

Before starting the pipeline, **ask the user** which AI agent to use for side-pane tasks (review/resolve):

| Agent | Review Command | Resolve Command |
|-------|---------------|-----------------|
| **Claude Code** | `claude --dangerously-skip-permissions '{prompt}'` | `claude --dangerously-skip-permissions '{prompt}'` |
| **Codex** | `codex exec --dangerously-bypass-approvals-and-sandbox '{prompt}'` | `codex exec --dangerously-bypass-approvals-and-sandbox '{prompt}'` |

> Interactive TUI mode — user can watch progress in the tmux pane. Pipeline detects completion via GitHub API polling, then kills the pane.

Store the choice in state as `"agent": "claude"` or `"agent": "codex"`. Use the corresponding CLI command for all side-pane operations (Steps 2, 4a).

## Workflow

### 0. Check Existing State

```bash
STATE_FILE=".workspace/pipeline/issue-{N}.state.json"
```

Exists → **resume** ([recovery.md](references/recovery.md)). Not exists → Step 1.

### 1. Run /dev-build

**`cd {area}` first** — all git/gh commands must run inside the area's repo directory.

**Capture orchestrator pane** before starting (anchors all future splits to this pane):

```bash
ORCHESTRATOR_PANE=$(tmux display-message -p '#{pane_id}')
```

Execute `/dev-build`. After PR creation, write state:

```json
{
  "issue": 42,
  "area": "client",
  "pr": 99,
  "branch": "feat/issue-42-add-auth",
  "worktree": ".workspace/worktrees/issue-42",
  "agent": "claude",
  "orchestratorPane": "%0",
  "step": "review",
  "reviewRound": 1,
  "lastReviewId": 0,
  "skipReview": false,
  "createdAt": "2026-01-01T00:00:00Z",
  "updatedAt": "2026-01-01T00:00:00Z"
}
```

### 2. Open Review Pane

Use `pipeline_open_pane()` from [pipeline-helpers.sh](scripts/pipeline-helpers.sh), **passing `$ORCHESTRATOR_PANE`** as target to ensure the split always happens next to the orchestrator — not the user's active pane:

```bash
# Claude Code
REVIEW_PANE=$(tmux split-window -h -t "$ORCHESTRATOR_PANE" -P -F '#{pane_id}' \
  "cd $(pwd)/{area} && claude --dangerously-skip-permissions 'Run /dev-review for PR #{PR#}. After review, exit.'")
# Codex
REVIEW_PANE=$(tmux split-window -h -t "$ORCHESTRATOR_PANE" -P -F '#{pane_id}' \
  "cd $(pwd)/{area} && codex exec --dangerously-bypass-approvals-and-sandbox 'Run /dev-review for PR #{PR#}. After review, exit.'")
```

Use the agent selected in Step 0/1 (stored in state `agent` field).

Save pane ID in state → `"step": "review", "reviewPane": "{pane_id}"`.

### 3. Wait for Review

Poll with `pipeline_poll_review` from [pipeline-helpers.sh](scripts/pipeline-helpers.sh):

```bash
source scripts/pipeline-helpers.sh
REVIEW_ID=$(pipeline_poll_review "{area_dir}" {PR#} {lastReviewId})
```

- `TIMEOUT` → error, report to user
- Otherwise → analyze the review:

```bash
eval "$(pipeline_analyze_review "{area_dir}" {PR#} "$REVIEW_ID")"
# Now available: $STATE, $CRITICAL, $WARNING, $SUGGESTION
```

Update state: `"lastReviewId": REVIEW_ID`.

**Decision logic**:
- `STATE=CHANGES_REQUESTED` → Step 4a
- `STATE=COMMENTED` + `CRITICAL > 0` → Step 4a
- `STATE=COMMENTED` + `CRITICAL = 0` → Step 5 (show counts, user decision)

### 4a. Trigger Resolve

Triggered by:
- Step 3: `CHANGES_REQUESTED` — fix CRITICAL + WARNING
- Step 5: "Fix & Re-review" — fix WARNING + SUGGESTION, then re-review
- Step 5: "Fix & Merge" — fix only, **skip re-review** (`skipReview: true`)

Kill review pane (if alive), then split resolve from **`$ORCHESTRATOR_PANE`**. This is reliable on both first run and recovery — the orchestrator pane is always alive:

```bash
tmux kill-pane -t "$REVIEW_PANE" 2>/dev/null
# Claude Code
RESOLVE_PANE=$(tmux split-window -h -t "$ORCHESTRATOR_PANE" -P -F '#{pane_id}' \
  "cd $(pwd)/.workspace/worktrees/issue-{N} && claude --dangerously-skip-permissions 'Run /dev-resolve for PR #{PR#}. After done, exit.'")
# Codex
RESOLVE_PANE=$(tmux split-window -h -t "$ORCHESTRATOR_PANE" -P -F '#{pane_id}' \
  "cd $(pwd)/.workspace/worktrees/issue-{N} && codex exec --dangerously-bypass-approvals-and-sandbox 'Run /dev-resolve for PR #{PR#}. After done, exit.'")
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
git worktree remove ../.workspace/worktrees/issue-{N}
git branch -d {branch} 2>/dev/null
tmux kill-pane -t "$REVIEW_PANE" 2>/dev/null
tmux kill-pane -t "$RESOLVE_PANE" 2>/dev/null
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
