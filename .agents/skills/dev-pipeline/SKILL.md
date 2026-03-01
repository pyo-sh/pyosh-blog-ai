---
name: dev-pipeline
description: Orchestrate the full dev cycle — code, review, resolve — with automated tmux pane management and pipeline state tracking. Runs /dev-build, then triggers /dev-review and /dev-resolve in a sandboxed side pane. Activates on "/dev-pipeline", "run pipeline", "automated review", etc.
---

# Dev-Pipeline

Orchestrate: `/dev-build` → `/dev-review` → `/dev-resolve` → merge. Review/resolve run in a **sandboxed side pane**. State tracked per-issue for crash recovery.

> Requires tmux session (`$TMUX`). Source helpers: `source scripts/pipeline-helpers.sh`

## Agent selection

Ask the user: **Claude** (`claude --dangerously-skip-permissions`) or **Codex** (`codex exec --dangerously-bypass-approvals-and-sandbox`). Store as `"agent": "claude"|"codex"` in state.

## Workflow

### 0. Check existing state

```bash
STATE_FILE=".workspace/pipeline/{area}/issue-{N}.state.json"
```

Exists → resume ([recovery.md](references/recovery.md)). Not exists → Step 1.

### 1. Run /dev-build

**`cd {area}` first.** Capture orchestrator pane:

```bash
ORCHESTRATOR_PANE=$(pipeline_orchestrator_pane)
```

After PR creation, write state:

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

### 2. Open review pane

```bash
REVIEW_PANE=$(pipeline_open_pane_verified \
  "$(pwd)/{area}" \
  "Run /dev-review for PR #{PR#}. After review, exit." \
  "$AGENT" "$ORCHESTRATOR_PANE" "$ISSUE" "$AREA")
rc=$?
```

`rc≠0` → handle per [pane-lifecycle.md](references/pane-lifecycle.md). Success → save `"step": "review", "reviewPane": "{pane_id}"`.

### 3. Wait for review

```bash
REVIEW_ID=$(pipeline_poll_review "{area_dir}" {PR#} {lastReviewId} 900 "$REVIEW_PANE")
rc=$?
```

- `rc=1` (TIMEOUT) → kill pane, report to user
- `rc=2` (PANE_DEAD) → auto-retry once. Second failure → report to user.

On success — kill pane, analyze:

```bash
pipeline_kill_pane "$REVIEW_PANE"
eval "$(pipeline_analyze_review "{area_dir}" {PR#} "$REVIEW_ID")"
# $STATE, $CRITICAL, $WARNING, $SUGGESTION
```

Update `"lastReviewId": REVIEW_ID`. Decision: `CHANGES_REQUESTED` or `COMMENTED+CRITICAL>0` → Step 4a | `COMMENTED+CRITICAL=0` → Step 5.

### 4a. Trigger resolve

```bash
WORKTREE_PATH=$(pipeline_resolve_worktree_path "$ISSUE" "$AREA")
RESOLVE_PANE=$(pipeline_open_pane_verified \
  "$WORKTREE_PATH" \
  "Run /dev-resolve for PR #{PR#}. After done, exit." \
  "$AGENT" "$ORCHESTRATOR_PANE" "$ISSUE" "$AREA")
rc=$?
```

`rc≠0` → handle per [pane-lifecycle.md](references/pane-lifecycle.md). Success → `"step": "resolve", "resolvePane": "{pane_id}"`.

### 4b. Wait for resolve

```bash
NEW_SHA=$(pipeline_poll_commits "{area_dir}" {PR#} "{lastCommitSha}" 900 "$RESOLVE_PANE")
rc=$?
```

Handle `rc` same as Step 3. When new commits appear: kill pane → show diff (`gh pr diff {PR#}`). `skipReview: true` → Step 6. `skipReview: false` → ask user: "Re-review" (→ Step 2) | "Merge as-is" (→ Step 6) | "Manual edit" (→ user edits, then Step 2).

### 5. No critical — user decision

Show review summary. Show check plan:

```bash
gh pr view {PR#} --json body --jq '.body' | grep -A999 '## Check plan' | tail -n +2
```

Ask user: **"Merge"** → Step 6 | **"Fix & Re-review"** → Step 4a | **"Fix & Merge"** → Step 4a with `skipReview: true`.

### 6. Merge + cleanup

Kill side panes first (before merge - prevents orphaned panes on merge failure):

```bash
tmux kill-pane -t "$REVIEW_PANE" 2>/dev/null
tmux kill-pane -t "$RESOLVE_PANE" 2>/dev/null
```

Merge and validate:

```bash
cd {area}
gh pr merge {PR#} --squash --delete-branch
if [ $? -ne 0 ]; then
  echo "ERROR: gh pr merge failed. Aborting cleanup. Check PR #{PR#} status."
  # Update state to "merge-failed", report to user. Do not proceed.
  exit 1
fi

PR_STATE=$(gh pr view {PR#} --json state -q .state)
if [ "$PR_STATE" != "MERGED" ]; then
  echo "ERROR: PR #{PR#} state is '$PR_STATE', expected 'MERGED'. Aborting cleanup."
  exit 1
fi
```

Cleanup (run inside `{area}` dir):

```bash
git fetch --prune
git worktree remove ../.workspace/worktrees/issue-{N} --force
git worktree prune
git branch -D {branch}
```

> `--delete-branch` removes the remote branch. `git fetch --prune` cleans the remote tracking ref. `git branch -D` removes the local branch after worktree removal (squash merge requires `-D` since feature commits are not ancestors of main).

State → `"step": "log"`.

### 7. Record + clean up

Run `/dev-log`, then `rm .workspace/pipeline/{area}/issue-{N}.state.json`.

## Constraints

- **Never merge without user approval**
- **Never modify code in this session** — code changes happen only in /dev-build or /dev-resolve pane
- On unrecoverable error: save state, kill panes, report to user

## References

- [Recovery strategy](references/recovery.md)
- [Pane lifecycle](references/pane-lifecycle.md)
- [Pipeline helpers](scripts/pipeline-helpers.sh)
