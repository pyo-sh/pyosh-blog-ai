---
name: dev-pipeline
description: Orchestrate the full dev cycle - code, review, resolve - with automated tmux pane management and pipeline state tracking. Runs /dev-build, then triggers /dev-review and /dev-resolve in a sandboxed side pane. Activates on "/dev-pipeline", "run pipeline", "automated review", etc.
---

# Dev-Pipeline

Orchestrate: `/dev-build` -> `/dev-review` -> `/dev-resolve` -> merge. Review/resolve run in a **sandboxed side pane**. State tracked per-issue for crash recovery.

> Area definitions, directory/repo mappings, worktree paths: [monorepo-layout.md](../../references/monorepo-layout.md)
> Requires tmux session (`$TMUX`). Source helpers: `source scripts/pipeline-helpers.sh`

## Agent selection

If the prompt specifies an agent (e.g., "Use claude for review and resolve panes"), use that agent without asking. Otherwise, ask the user: **Claude** (`claude --dangerously-skip-permissions`) or **Codex** (`codex exec --dangerously-bypass-approvals-and-sandbox`). Store as `"agent": "claude"|"codex"` in state.

## Workflow

### 0. Check existing state

Verify tmux session first:

```bash
[ -z "$TMUX" ] && echo "ERROR: tmux session required. Start tmux and retry." && exit 1
```

Check for existing pipeline:

```bash
STATE_FILE=".workspace/pipeline/{area}/issue-{N}.state.json"
```

If state file exists -> show the current `step` and `pr` to the user, then ask: **"Resume from step X?"** or **"Start fresh?"**. If "Start fresh" -> delete state file, proceed to Step 1. If "Resume" -> jump directly to the current `step`. Each step self-validates on entry.

Not exists -> Step 1.

### 1. Run /dev-build

**`cd {area}` first.** Capture orchestrator pane:

```bash
ORCHESTRATOR_PANE=$(pipeline_orchestrator_pane)
```

**Recovery entry**: If state says `step: "build"`, check PR status first:

```bash
cd {area} && gh pr list --head {branch} --json number,state --jq '.[0]'
```

- PR open -> update state to `step: "review"`, jump to Step 2
- PR merged -> update state to `step: "log"`, jump to Step 7
- No PR -> re-run `/dev-build` from `.workspace/worktrees/issue-{N}`

After PR creation, capture the initial commit SHA and write state:

```bash
LAST_COMMIT_SHA=$(cd {area_dir} && gh api "repos/{owner}/{repo}/pulls/{PR#}/commits" --jq '.[-1].sha')
if [ -z "$LAST_COMMIT_SHA" ] || [ "$LAST_COMMIT_SHA" = "null" ]; then
  echo "ERROR: Failed to capture initial commit SHA for PR #{PR#}. Aborting."
  exit 1
fi
```

```json
{
  "issue": 42, "area": "client", "pr": 99,
  "branch": "feat/issue-42-add-auth",
  "worktree": ".workspace/worktrees/issue-42",
  "agent": "claude", "orchestratorPane": "%0",
  "step": "review", "reviewRound": 1, "lastReviewId": 0,
  "lastCommitSha": "{LAST_COMMIT_SHA}",
  "skipReview": false,
  "reviewPaneRetries": 0, "resolvePaneRetries": 0, "maxPaneRetries": 2,
  "createdAt": "2026-01-01T00:00:00Z", "updatedAt": "2026-01-01T00:00:00Z"
}
```

### 2. Open review pane

**Recovery entry**: Before opening a pane, check if a review already exists:

```bash
REVIEW_ID=$(pipeline_check_review_exists "{area_dir}" {PR#} {lastReviewId})
```

If found -> skip pane open, go directly to Step 3 (process review). Otherwise, continue below.

Kill any previous review pane, then open using the 3-layer protocol ([pane-lifecycle.md](references/pane-lifecycle.md)):

```bash
# Layer 1: Pre-defense
pipeline_kill_state_pane "$ISSUE" "$AREA" "reviewPane"
pipeline_pane_snapshot > /tmp/panes_before_${ISSUE}.txt

# Layer 2: Execution (file-based capture, single call)
PANE_OUT="/tmp/pipeline-pane-${ISSUE}-${AREA}.txt"
pipeline_open_pane_with_retry "$ISSUE" "$AREA" "reviewPane" \
  "$MONOREPO_ROOT" \
  "Run /dev-review for PR #{PR#} in {area} repo. After review, exit." \
  "$AGENT" "$ORCHESTRATOR_PANE" \
  > "$PANE_OUT" 2>/tmp/pipeline-pane-err.txt
RC=$?
REVIEW_PANE=$(cat "$PANE_OUT")
```

- `RC=0` -> save `"reviewPane": "{REVIEW_PANE}"` in state
- `RC=5` (MAX_RETRIES) -> run Layer 3 cleanup, report to user, stop
- `RC!=0` -> run Layer 3 cleanup, report to user, stop

### 3. Wait for review

```bash
REVIEW_ID=$(pipeline_poll_review "{area_dir}" {PR#} {lastReviewId} 900 "$REVIEW_PANE")
rc=$?
```

- `rc=0` -> success, continue below
- `rc=1` (TIMEOUT) -> kill pane, report to user
- `rc=2` (PANE_DEAD) -> reset `reviewPaneRetries` to 0 in state, go back to Step 2

On success - kill pane, fetch and read review:

```bash
pipeline_kill_pane "$REVIEW_PANE"
pipeline_fetch_review "{area_dir}" {PR#} "$REVIEW_ID"
```

Read `state` and severity counts (`[CRITICAL]`, `[WARNING]`, `[SUGGESTION]`). Update state:

```bash
pipeline_state_update "$ISSUE" "$AREA" \
  '.lastReviewId = {REVIEW_ID} | .reviewPaneRetries = 0'
```

Decision:
- `CHANGES_REQUESTED` or `COMMENTED` + `CRITICAL > 0` -> Step 4a
- `COMMENTED` + `CRITICAL = 0` -> Step 5
- `APPROVED` -> Step 5 (treat as no critical)
- `PENDING` or `DISMISSED` -> report unexpected state to user, stop

### 4a. Trigger resolve

**Recovery entry**: Before opening a pane, check if new commits already exist:

```bash
NEW_SHA=$(pipeline_check_new_commits "{area_dir}" {PR#} "{lastCommitSha}")
```

If found -> skip pane open, go directly to Step 4b (process commits). Otherwise, continue below.

```bash
# Layer 1
pipeline_kill_state_pane "$ISSUE" "$AREA" "resolvePane"
pipeline_pane_snapshot > /tmp/panes_before_${ISSUE}.txt

# Layer 2
WORKTREE_PATH=$(pipeline_resolve_worktree_path "$ISSUE" "$AREA")
PANE_OUT="/tmp/pipeline-pane-${ISSUE}-${AREA}.txt"
pipeline_open_pane_with_retry "$ISSUE" "$AREA" "resolvePane" \
  "$MONOREPO_ROOT" \
  "Run /dev-resolve for PR #{PR#} in worktree ${WORKTREE_PATH}. After done, exit." \
  "$AGENT" "$ORCHESTRATOR_PANE" \
  > "$PANE_OUT" 2>/tmp/pipeline-pane-err.txt
RC=$?
RESOLVE_PANE=$(cat "$PANE_OUT")
```

`RC=0` -> save state with `"step": "resolve", "resolvePane": "{RESOLVE_PANE}"`. `RC!=0` -> Layer 3, report, stop.

### 4b. Wait for resolve

```bash
NEW_SHA=$(pipeline_poll_commits "{area_dir}" {PR#} "{lastCommitSha}" 900 "$RESOLVE_PANE")
rc=$?
```

- `rc=0` -> continue below
- `rc=1` (TIMEOUT) -> kill pane, report to user
- `rc=2` (PANE_DEAD) -> reset `resolvePaneRetries` to 0, go back to Step 4a

When new commits found: kill pane, update `lastCommitSha`, show diff (`gh pr diff {PR#}`).

- `skipReview: true` -> Step 6
- `skipReview: false` -> ask user: "Re-review" (reset `reviewPaneRetries` to 0 -> Step 2) | "Merge as-is" (-> Step 6) | "Manual edit" (user edits, then Step 2)

### 5. No critical - user decision

Show review summary.

Ask user: **"Merge"** -> Step 6 | **"Fix & Re-review"** -> Step 4a | **"Fix & Merge"** -> Step 4a with `skipReview: true`.

### 6. Merge + cleanup

**Recovery entry**: Check PR state first:

```bash
PR_STATE=$(cd {area} && gh pr view {PR#} --json state -q .state)
```

- `MERGED` -> skip merge, proceed to cleanup
- `OPEN` -> ask user for merge approval, then merge

Kill side panes first:

```bash
pipeline_kill_state_pane "$ISSUE" "$AREA" "reviewPane"
pipeline_kill_state_pane "$ISSUE" "$AREA" "resolvePane"
```

Merge and validate:

```bash
cd {area}
gh pr merge {PR#} --squash --delete-branch
if [ $? -ne 0 ]; then
  echo "ERROR: gh pr merge failed."
  pipeline_state_update "$ISSUE" "$AREA" '.step = "merge-failed"'
  exit 1
fi

PR_STATE=$(gh pr view {PR#} --json state -q .state)
if [ "$PR_STATE" != "MERGED" ]; then
  echo "ERROR: PR #{PR#} state is '$PR_STATE', expected 'MERGED'."
  pipeline_state_update "$ISSUE" "$AREA" '.step = "merge-failed"'
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

State -> `"step": "log"`.

### 7. Record + clean up

Run `/dev-log`, then `rm .workspace/pipeline/{area}/issue-{N}.state.json`.

## Constraints

- **Never merge without user approval**
- **Never modify code in this session** - code changes happen only in /dev-build or /dev-resolve pane
- **Never call `pipeline_open_pane_verified` or `pipeline_open_pane_with_retry` more than once per step attempt** - if it fails, run Layer 3 cleanup and report to user
- On unrecoverable error: save state, kill panes, report to user

## References

- [Recovery strategy](references/recovery.md)
- [Pane lifecycle](references/pane-lifecycle.md)
- [Pipeline helpers](scripts/pipeline-helpers.sh)
