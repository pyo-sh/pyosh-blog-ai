---
name: dev-pipeline
description: Orchestrate the full dev cycle — code, review, resolve — with automated tmux pane management and pipeline state tracking. Runs /dev-build, then triggers /dev-review and /dev-resolve in a sandboxed side pane. Activates on "/dev-pipeline", "run pipeline", "automated review", etc.
---

# Dev-Pipeline

Orchestrate: `/dev-build` → `/dev-review` → `/dev-resolve` → merge. Review/resolve run in a **sandboxed side pane**. State tracked per-issue for crash recovery.

> Requires tmux session (`$TMUX`). Git remote rules in `CLAUDE.md`.
> Source helpers once at pipeline start: `source scripts/pipeline-helpers.sh`

## Agent Selection

**Ask the user** which AI agent to use for side-pane tasks:

| Agent | Command pattern |
|-------|----------------|
| **Claude Code** | `claude --dangerously-skip-permissions '{prompt}'` |
| **Codex** | `codex exec --dangerously-bypass-approvals-and-sandbox '{prompt}'` |

Store in state as `"agent": "claude"` or `"agent": "codex"`.

## Workflow

### 0. Check Existing State

```bash
STATE_FILE=".workspace/pipeline/issue-{N}.state.json"
```

Exists → **resume** ([recovery.md](references/recovery.md)). Not exists → Step 1.

### 1. Run /dev-build

**`cd {area}` first** — all git/gh commands must run inside the area's repo directory.

Capture orchestrator pane (anchors all future splits):

```bash
ORCHESTRATOR_PANE=$(pipeline_orchestrator_pane)
```

Execute `/dev-build`. After PR creation, write state:

```json
{
  "issue": 42, "area": "client", "pr": 99,
  "branch": "feat/issue-42-add-auth",
  "worktree": ".workspace/worktrees/issue-42",
  "agent": "claude", "orchestratorPane": "%0",
  "step": "review", "reviewRound": 1, "lastReviewId": 0,
  "skipReview": false,
  "createdAt": "2026-01-01T00:00:00Z", "updatedAt": "2026-01-01T00:00:00Z"
}
```

### 2. Open Review Pane

```bash
REVIEW_PANE=$(pipeline_open_pane_verified \
  "$(pwd)/{area}" \
  "Run /dev-review for PR #{PR#}. After review, exit." \
  "$AGENT" "$ORCHESTRATOR_PANE" "$ISSUE" "$AREA")
rc=$?
```

On `rc≠0` → handle per [Pane Lifecycle](#pane-lifecycle) return codes.
On success → save `"step": "review", "reviewPane": "{pane_id}"`.

### 3. Wait for Review

```bash
REVIEW_ID=$(pipeline_poll_review "{area_dir}" {PR#} {lastReviewId} 900 "$REVIEW_PANE")
rc=$?
```

- `rc=0` → analyze review (below)
- `rc=1` (TIMEOUT) → kill pane, report to user
- `rc=2` (PANE_DEAD) → auto-retry: re-open via `pipeline_open_pane_verified()`, re-poll. Second failure → report to user.

On success — kill review pane immediately, then analyze:

```bash
pipeline_kill_pane "$REVIEW_PANE"
eval "$(pipeline_analyze_review "{area_dir}" {PR#} "$REVIEW_ID")"
# $STATE, $CRITICAL, $WARNING, $SUGGESTION
```

Update state: `"lastReviewId": REVIEW_ID`.

**Decision logic**:
- `CHANGES_REQUESTED` → Step 4a
- `COMMENTED` + `CRITICAL > 0` → Step 4a
- `COMMENTED` + `CRITICAL = 0` → Step 5

### 4a. Trigger Resolve

Triggered by: Step 3 (`CHANGES_REQUESTED`), Step 5 ("Fix & Re-review" or "Fix & Merge" with `skipReview: true`).

```bash
WORKTREE_PATH=$(pipeline_resolve_worktree_path "$ISSUE" "$AREA")

RESOLVE_PANE=$(pipeline_open_pane_verified \
  "$WORKTREE_PATH" \
  "Run /dev-resolve for PR #{PR#}. After done, exit." \
  "$AGENT" "$ORCHESTRATOR_PANE" "$ISSUE" "$AREA")
rc=$?
```

On `rc≠0` → handle per [Pane Lifecycle](#pane-lifecycle).
On success → `"step": "resolve", "resolvePane": "{pane_id}"`.

### 4b. Wait for Resolve

```bash
NEW_SHA=$(pipeline_poll_commits "{area_dir}" {PR#} "{lastCommitSha}" 900 "$RESOLVE_PANE")
rc=$?
```

Handle `rc` same as Step 3 (TIMEOUT → report, PANE_DEAD → auto-retry once).

When new commits appear:
1. Kill resolve pane immediately: `pipeline_kill_pane "$RESOLVE_PANE"`
2. Show diff: `gh pr diff {PR#}`
3. `skipReview: true` → Step 6
4. `skipReview: false` → **ask user**: "Apply & Re-review" (→ Step 2) | "Merge as-is" (→ Step 6) | "Manual edit" (→ user edits, then Step 2)

### 5. No Critical — User Decision

Show review summary + severity counts. Check for unchecked test plan items:

```bash
UNCHECKED=$(gh pr view {PR#} --json body \
  --jq '[.body | split("\n")[] | select(startswith("- [ ]"))] | length')
[ "$UNCHECKED" -gt 0 ] && echo "⚠️  ${UNCHECKED} unchecked test plan item(s) remain"
```

**Ask user**:
- **"Merge"** → Step 6
- **"Fix & Re-review"** → Step 4a
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

### 7. Record + Clean Up

Run `/dev-log`, then `rm .workspace/pipeline/issue-{N}.state.json`.

## Constraints

- **Never merge without user approval**
- **Never modify code in this session** — code changes happen only in /dev-build or /dev-resolve pane
- **Always clean up tmux panes** on completion or failure
- On unrecoverable error: save state, kill panes, report to user

## Pane Lifecycle

Side-pane processes can fail silently. All pane/poll functions use consistent return codes:

| Code | stdout | Meaning |
|------|--------|---------|
| 0 | result | Success |
| 1 | `TIMEOUT` | Polling expired |
| 2 | `PANE_DEAD` | Pane process died |
| 3 | `PATH_INVALID` | Working directory not found |
| 4 | `RETRY_FAILED` | Auto-retry also failed |

**Key behaviors**:
- `pipeline_open_pane_verified()`: validates dir → opens pane → 3s startup check → auto-retries once with path re-resolution on failure
- `pipeline_poll_review()` / `pipeline_poll_commits()`: checks API first (catches normal exit), then pane health. Prevents false PANE_DEAD when task completed normally.
- **Auto-retry policy**: max 1 retry per pane-open or polling cycle. On retry failure → report to user.

## References

- [Recovery strategy](references/recovery.md) — crash recovery from state file
- [Pipeline helpers](scripts/pipeline-helpers.sh) — tmux and state management functions
