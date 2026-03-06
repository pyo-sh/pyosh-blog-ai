# Headless pipeline - dev-pipeline review/resolve subprocess conversion

## Status: planned

## Context

dev-pipeline currently spawns review/resolve AI in tmux side panes. This causes frequent errors:
- Pane creation failures (PANE_DEAD, orphan panes, ID reuse)
- Complex 3-layer pane lifecycle protocol needed as workaround
- ~230 lines of defensive pane management code (46% of pipeline-helpers.sh)

Insights feedback: run pipeline AI calls headlessly to reduce error surface.

## Verified prerequisites

| Check | Result |
|-------|--------|
| `CLAUDECODE= claude -p` bypasses nesting restriction | Confirmed (v2.1.70) |
| Slash commands available in `-p` mode | Confirmed (`/dev-review`, `/dev-resolve` listed) |
| `--dangerously-skip-permissions` works with `-p` | Confirmed |
| `--no-session-persistence` available | Confirmed |

## Decision

Replace tmux pane spawning with background `claude -p` subprocesses for review and resolve steps only. Pipeline AI (main session) remains interactive.

## Design

### Execution model change

```
AS-IS: tmux split-window -h -d "claude '/dev-review ...'"

TO-BE (review):
(CLAUDECODE= claude -p --dangerously-skip-permissions --no-session-persistence \
  --allowedTools "Bash,Read,Skill" --max-turns 15 \
  '/dev-review for PR #{PR#} in {area} repo') > $LOG 2>&1 &

TO-BE (resolve):
(CLAUDECODE= claude -p --dangerously-skip-permissions --no-session-persistence \
  --allowedTools "Bash,Read,Edit,Write,Grep,Glob,Skill" --max-turns 25 \
  '/dev-resolve for PR #{PR#} in worktree {path}') > $LOG 2>&1 &
```

Tool allowlists rationale:
- Review: `Bash,Read,Skill` only - no `Glob`, `Grep`, `Agent` (prevents codebase exploration, forces diff-focused review)
- Resolve: `Bash,Read,Edit,Write,Grep,Glob,Skill` - needs code modification tools

`--max-turns` prevents infinite loops - AI hits turn limit and exits instead of hanging.

### Identifier change: pane ID -> PID

| Operation | AS-IS (pane) | TO-BE (headless) |
|-----------|-------------|-----------------|
| Execute | `tmux split-window ... claude '...'` | `(CLAUDECODE= claude -p ...) > $LOG 2>&1 &` |
| Identify | pane ID (`%3`) | PID (`$!`) |
| Health check | `tmux list-panes \| grep` | `kill -0 $PID` |
| Terminate | `tmux kill-pane -t` | `kill $PID` |
| Inspect output | `tmux capture-pane` | `tail $LOG` |
| Completion | API poll + pane alive | API poll + PID alive |

### State schema change

```diff
  {
    "issue": 42, "area": "client", "pr": 99,
    "branch": "feat/issue-42", "worktree": ".workspace/worktrees/issue-42",
-   "agent": "claude", "orchestratorPane": "%0",
+   "agent": "claude",
    "step": "review", "reviewRound": 1, "lastReviewId": 0,
    "lastCommitSha": "{SHA}", "skipReview": false,
-   "reviewPaneRetries": 0, "resolvePaneRetries": 0, "maxPaneRetries": 2,
-   "reviewPane": "%3", "resolvePane": "%4"
+   "reviewPid": null, "resolvePid": null,
+   "reviewLog": ".workspace/pipeline/logs/issue-42-review.log",
+   "resolveLog": ".workspace/pipeline/logs/issue-42-resolve.log"
  }
```

Retry fields removed - process fork does not have pane creation failure modes.

### pipeline-helpers.sh changes

**Remove (~150 lines):**
- `pipeline_orchestrator_pane()`
- `pipeline_open_pane()`, `pipeline_open_pane_verified()`, `pipeline_open_pane_with_retry()`
- `pipeline_pane_alive()`, `pipeline_pane_alive_verified()`
- `pipeline_pane_snapshot()`, `pipeline_pane_orphan_cleanup()`
- `pipeline_kill_pane()`, `pipeline_kill_state_pane()`

**Add (~50 lines):**
- `pipeline_run_headless()` - spawn `claude -p` as background process, 3s startup check, return PID
- `pipeline_proc_alive()` - `kill -0` wrapper
- `pipeline_kill_proc()` - graceful kill with SIGKILL fallback
- `pipeline_kill_state_proc()` - kill process recorded in state by field name

**Modify:**
- `pipeline_poll_review()` - `$5` param: pane_id -> pid, health check: `pipeline_pane_alive` -> `pipeline_proc_alive`
- `pipeline_poll_commits()` - same change
- `pipeline_cleanup()` - `pipeline_kill_pane` -> `pipeline_kill_proc`

**Keep unchanged:**
- All state management functions
- `pipeline_resolve_worktree_path()`
- `pipeline_check_review_exists()`, `pipeline_check_new_commits()`
- `pipeline_fetch_review()`
- `pipeline_list()`

### SKILL.md changes

- Step 0: Remove `$TMUX` check
- Step 1: Remove `pipeline_orchestrator_pane()` capture
- Step 2: `pipeline_open_pane_with_retry` -> `pipeline_run_headless`, state field `reviewPane` -> `reviewPid`
- Step 3: poll param change, `pipeline_kill_pane` -> `pipeline_kill_proc`
- Step 4a: Same pattern as Step 2 for resolve
- Step 4b: Same pattern as Step 3
- Step 6: `pipeline_kill_state_pane` -> `pipeline_kill_state_proc`
- Recovery entry points: `pipeline_pane_alive_verified` -> `pipeline_proc_alive`

### Reference docs changes

- `pane-lifecycle.md` -> `process-lifecycle.md` (rewrite, ~25 lines replacing ~72)
- `recovery.md` - simplify pane failure section

### Sub-skill changes (from insights feedback)

Changes to dev-review, dev-resolve, dev-build SKILL.md - applied alongside headless conversion.

#### dev-review SKILL.md

1. **Diff-first, no codebase exploration** (feedback #1)

```diff
  ### 1. Read PR

- gh pr view {PR#}
- gh pr diff {PR#}
- gh issue view {Issue#}
+ gh pr diff {PR#}
+ gh pr view {PR#} --json number,title,state,body

  ### 2. Analyze code

- Read diff + surrounding context. Check `{area}/CLAUDE.md` compliance.
+ Analyze the diff output directly. Do NOT explore the broader codebase.
+ Only read specific files when the diff context is insufficient to understand the change.
+ Check `{area}/CLAUDE.md` compliance.
```

Enforced at runtime by `--allowedTools "Bash,Read,Skill"` (no Glob, Grep, Agent).

2. **Correct repo for gh commands** (feedback #2)

Add warning to constraints:

```
> Always verify you are in the correct area directory before running `gh` commands.
> Client PRs: `cd client && gh pr ...` or `gh pr ... -R pyo-sh/pyosh-blog-fe`
> Server PRs: `cd server && gh pr ...` or `gh pr ... -R pyo-sh/pyosh-blog-be`
```

3. **Avoid deprecated gh fields** (feedback #4)

```diff
- gh pr view {PR#}
+ gh pr view {PR#} --json number,title,state,body,reviews
```

#### dev-resolve SKILL.md

- Same repo warning (feedback #2)

#### dev-build SKILL.md

1. **Fetch + rebase before worktree creation** (feedback #3)

```diff
  ### 1. Create worktree

  cd {area}
+ git fetch origin
+ git rebase origin/main || git merge origin/main
  git worktree add -b {type}/issue-{N}-{desc} ../.workspace/worktrees/issue-{N} main
```

2. **Avoid deprecated gh fields** (feedback #4)

- Same `--json` field list for any `gh pr view` calls

#### dev-pipeline SKILL.md

- Same `--json` field list for `gh pr view` in Step 1 recovery and Step 6

### Unchanged

- User decision points (Step 4b, 5, 6) - all in Pipeline AI main session
- Polling core logic (GitHub API check interval, timeout)

## Impact on dev-orchestrator

dev-orchestrator uses these pipeline-helpers functions:
- `pipeline_kill_state_pane` -> will need update to `pipeline_kill_state_proc`
- `pipeline_pane_alive` -> will need update to `pipeline_proc_alive`

Options:
1. Update orchestrator simultaneously
2. Add temporary compat wrappers (not recommended - adds complexity)

Recommendation: orchestrator conversion is a separate follow-up task. Since orchestrator dispatches `/dev-pipeline` to existing panes (not creating new ones), its pane management is independent from pipeline's internal review/resolve pane management. The functions orchestrator calls from pipeline-helpers are only for inspecting pipeline's side panes, which can be handled by updating the function names.

## pipeline_run_headless() updated design

```bash
pipeline_run_headless() {
  # Usage: pipeline_run_headless <workdir> <prompt> <agent> <issue> <area> <field>
  # field: "reviewPid" or "resolvePid" (determines tool allowlist and max-turns)
  local workdir=$1 prompt=$2 agent=${3:-claude} issue=$4 area=$5 field=$6

  mkdir -p "$PIPELINE_LOG_DIR"
  local log="$PIPELINE_LOG_DIR/issue-${issue}-${field}.log"

  local tools max_turns
  case "$field" in
    reviewPid)
      tools="Bash,Read,Skill"
      max_turns=15
      ;;
    resolvePid)
      tools="Bash,Read,Edit,Write,Grep,Glob,Skill"
      max_turns=25
      ;;
  esac

  local cmd
  if [ "$agent" = "codex" ]; then
    cmd="codex exec --dangerously-bypass-approvals-and-sandbox '$prompt'"
  else
    cmd="CLAUDECODE= claude -p --dangerously-skip-permissions --no-session-persistence"
    cmd="$cmd --allowedTools \"$tools\" --max-turns $max_turns '$prompt'"
  fi

  (cd "$workdir" && eval "$cmd" > "$log" 2>&1) &
  local pid=$!

  sleep 3
  if ! kill -0 "$pid" 2>/dev/null; then
    echo "PROC_DEAD"
    >&2 echo "[pipeline] Process died within 3s. Log: $log"
    >&2 tail -20 "$log"
    return 2
  fi

  echo "$pid"
  return 0
}
```

## Self-healing pipeline (integrated into dev-pipeline)

Feedback suggested a separate wrapper skill, but integrating into dev-pipeline is better because:
- dev-pipeline already has step-based recovery, state persistence, and pre-checks
- A wrapper would need to know pipeline internals anyway (strong coupling, no encapsulation benefit)
- Two skills sharing one state file risks race conditions
- Failures occur at specific steps - handle them at the source

### Error mode mapping

| Error mode | Step | Auto-recovery | Max retries |
|-----------|------|---------------|-------------|
| Stale branch | 1 (build) | `git fetch origin && git rebase origin/main` | 3 |
| Rebase conflict | 1 (build) | `git rebase --abort && git merge origin/main` | 3 |
| gh CLI deprecated field | 1, 3, 6 | Use `--json` explicit fields (preventive, not reactive) | N/A |
| Import path mismatch (`@/` vs `@shared/`) | 4a (resolve) | Handled by resolve AI, not pipeline | N/A |
| Headless process dead | 2, 3, 4a, 4b | Re-run `pipeline_run_headless()` | 3 |
| Merge failure | 6 (merge) | `git fetch && git rebase origin/main` then retry merge | 3 |
| gh API rate limit / network | Any | Wait 30s, retry | 3 |

### State schema additions

```diff
  {
    ...
    "reviewPid": null, "resolvePid": null,
    "reviewLog": "...", "resolveLog": "...",
+   "stageRetries": { "build": 0, "review": 0, "resolve": 0, "merge": 0 },
+   "maxStageRetries": 3,
+   "recoveryLog": []
  }
```

`recoveryLog` entries:

```json
{
  "stage": "merge",
  "attempt": 2,
  "error": "merge conflict in src/index.ts",
  "action": "git fetch + rebase origin/main",
  "result": "success",
  "timestamp": "2026-03-06T10:30:00Z"
}
```

### Recovery flow per step

**Step 1 (build) - stale branch / rebase conflict:**

```
build fails → check error pattern
  → "stale branch" or "diverged" → git fetch && git rebase origin/main
    → rebase conflict → git rebase --abort && git merge origin/main
      → merge conflict → increment stageRetries.build, log to recoveryLog
        → retries < 3 → retry step 1
        → retries >= 3 → escalate to user
```

**Step 2/3 (review) - headless process dead:**

```
pipeline_run_headless returns PROC_DEAD or poll returns PANE_DEAD (rc=2)
  → increment stageRetries.review, log to recoveryLog
  → retries < 3 → re-run pipeline_run_headless
  → retries >= 3 → escalate with log tail
```

**Step 4a/4b (resolve) - same pattern as review**

**Step 6 (merge) - merge failure:**

```
gh pr merge fails → check error
  → "not mergeable" or "out of date" → git fetch && git rebase origin/main && git push
    → retries < 3 → retry gh pr merge
    → retries >= 3 → escalate
  → "review required" → escalate immediately (not auto-recoverable)
```

### Escalation format

When retries are exhausted, report to user:

```
[pipeline] Stage "merge" failed after 3 recovery attempts.

Recovery log:
  #1 [10:25] merge conflict in src/index.ts → git fetch + rebase → conflict persists
  #2 [10:26] merge conflict in src/index.ts → git merge origin/main → conflict persists
  #3 [10:27] manual merge markers present → rebase --abort → no resolution

Worktree: .workspace/worktrees/issue-42
Branch: feat/issue-42-add-auth
PR: #99

Action needed: resolve conflict manually, then resume with /dev-pipeline
```

### Changes to pipeline-helpers.sh

Additional functions (~30 lines):

```bash
pipeline_stage_retry() {
  # Increment stage retry counter, check against max.
  # Usage: pipeline_stage_retry <issue> <area> <stage>
  # Returns: 0 = can retry, 1 = max reached
  local issue=$1 area=$2 stage=$3
  local retries
  retries=$(pipeline_state_read "$issue" "$area" | jq -r ".stageRetries.${stage} // 0")
  local max
  max=$(pipeline_state_read "$issue" "$area" | jq -r ".maxStageRetries // 3")
  if [ "$retries" -ge "$max" ]; then
    return 1
  fi
  pipeline_state_update "$issue" "$area" ".stageRetries.${stage} = $((retries + 1))"
}

pipeline_recovery_log() {
  # Append a recovery attempt to recoveryLog.
  # Usage: pipeline_recovery_log <issue> <area> <stage> <error> <action> <result>
  local issue=$1 area=$2 stage=$3 error=$4 action=$5 result=$6
  local entry
  entry=$(jq -n --arg s "$stage" --arg e "$error" --arg a "$action" --arg r "$result" \
    '{stage:$s, error:$e, action:$a, result:$r, timestamp:(now|todate)}')
  pipeline_state_update "$issue" "$area" ".recoveryLog += [$entry]"
}
```

### Impact on code volume (updated)

## Code volume change

| File | Lines removed | Lines added | Net |
|------|--------------|-------------|-----|
| pipeline-helpers.sh | ~150 (pane mgmt) | ~80 (headless + self-heal) | -70 |
| SKILL.md | ~30 (pane refs) | ~35 (headless + recovery flow) | +5 |
| pane-lifecycle.md | ~72 (full) | ~25 (process-lifecycle.md) | -47 |
| recovery.md | ~15 (pane section) | ~20 (self-heal section) | +5 |
| dev-review SKILL.md | ~5 | ~10 | +5 |
| dev-build SKILL.md | ~2 | ~5 | +3 |
| **Total** | | | **~-99** |

## Risks

1. **PID persistence across sessions** - PIDs are ephemeral. If Pipeline AI crashes and resumes, stored PID is stale. Mitigated: recovery entry already checks API first (review exists? commits exist?) before checking process health. Stale PID -> `kill -0` fails -> treated as dead -> re-check API -> re-run if needed.
2. **Log disk usage** - full AI output goes to log files. Mitigated: `pipeline_cleanup()` can delete log files. Low risk.
3. **Orchestrator compat** - addressed above.
