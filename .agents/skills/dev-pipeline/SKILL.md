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

Use `pipeline_open_pane_verified()` from [pipeline-helpers.sh](scripts/pipeline-helpers.sh). This validates the working directory, opens the pane, verifies startup (3s grace period), and retries once on failure:

```bash
source scripts/pipeline-helpers.sh
REVIEW_PANE=$(pipeline_open_pane_verified \
  "$(pwd)/{area}" \
  "Run /dev-review for PR #{PR#}. After review, exit." \
  "$AGENT" "$ORCHESTRATOR_PANE" "$ISSUE" "$AREA")
rc=$?
```

**Handle result** (see [Pane Lifecycle](#pane-lifecycle) for return codes):
- `rc=0` → Save pane ID in state → `"step": "review", "reviewPane": "{pane_id}"`, proceed to Step 3
- `rc=2` (PANE_DEAD) → Report: "Review pane failed to start. Check agent binary and tmux session."
- `rc=3` (PATH_INVALID) → Report: "Working directory not found."
- `rc=4` (RETRY_FAILED) → Report: "Review pane startup failed after retry. Manual intervention needed."

### 3. Wait for Review

Poll with `pipeline_poll_review`, passing `$REVIEW_PANE` for health monitoring:

```bash
source scripts/pipeline-helpers.sh
REVIEW_ID=$(pipeline_poll_review "{area_dir}" {PR#} {lastReviewId} 900 "$REVIEW_PANE")
rc=$?
```

**Handle result**:
- `rc=0` → analyze the review (below)
- `rc=1` (TIMEOUT) → kill pane, report to user
- `rc=2` (PANE_DEAD) → **auto-retry once**: re-open review pane via `pipeline_open_pane_verified()`, then re-poll. If second pane also fails, report to user.

On success, analyze the review:

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

Kill review pane, resolve worktree path, then open verified resolve pane:

```bash
source scripts/pipeline-helpers.sh
pipeline_kill_pane "$REVIEW_PANE"

# Resolve actual worktree path (handles legacy paths)
WORKTREE_PATH=$(pipeline_resolve_worktree_path "$ISSUE" "$AREA")

RESOLVE_PANE=$(pipeline_open_pane_verified \
  "$WORKTREE_PATH" \
  "Run /dev-resolve for PR #{PR#}. After done, exit." \
  "$AGENT" "$ORCHESTRATOR_PANE" "$ISSUE" "$AREA")
rc=$?
```

**Handle result** (same as Step 2):
- `rc=0` → proceed to Step 4b
- `rc=2|3|4` → report failure to user

State → `"step": "resolve", "resolvePane": "{pane_id}"`.

### 4b. Wait for Resolve

Poll for new commits with `pipeline_poll_commits`, passing `$RESOLVE_PANE` for health monitoring:

```bash
source scripts/pipeline-helpers.sh
NEW_SHA=$(pipeline_poll_commits "{area_dir}" {PR#} "{lastCommitSha}" 900 "$RESOLVE_PANE")
rc=$?
```

**Handle result**:
- `rc=0` → new commits found, proceed below
- `rc=1` (TIMEOUT) → kill pane, report to user
- `rc=2` (PANE_DEAD) → **auto-retry once**: re-open resolve pane via `pipeline_open_pane_verified()`, then re-poll. If second pane also fails, report to user.

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

## Pane Lifecycle

Side-pane processes can fail silently (path mismatch, agent binary missing, OOM). The pipeline uses **verified pane opening** + **health-monitored polling** to detect and recover.

### Return Codes

| Code | Meaning | stdout token |
|------|---------|-------------|
| 0 | Success | pane_id / review_id / sha |
| 1 | Timeout | `TIMEOUT` |
| 2 | Pane died | `PANE_DEAD` |
| 3 | Path invalid | `PATH_INVALID` |
| 4 | Retry exhausted | `RETRY_FAILED` |

### Startup Verification

`pipeline_open_pane_verified()` validates the directory, opens the pane, waits 3 seconds, then checks `pipeline_pane_alive()`. If the pane died, it re-resolves the worktree path (current + legacy locations) and retries once.

### Health-Monitored Polling

`pipeline_poll_review()` and `pipeline_poll_commits()` accept an optional pane ID. Each iteration:
1. **Check API first** — the pane may have exited normally after completing its task
2. **Then check pane health** — if pane is dead and no result found, do one final API check before returning `PANE_DEAD`

This order prevents false positives when a pane exits normally after posting its result.

### Auto-Retry Policy

- **Max 1 automatic retry** per pane-open or polling cycle
- On retry: re-resolve worktree path via `pipeline_resolve_worktree_path()` (handles legacy paths)
- On retry failure: report to user with diagnostic token

## References

- [Recovery strategy](references/recovery.md) — crash recovery from state file
- [Pipeline helpers](scripts/pipeline-helpers.sh) — tmux and state management functions
