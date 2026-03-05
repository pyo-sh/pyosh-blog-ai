# Pipeline recovery

Resume from state file when orchestrator crashes or disconnects.

Recovery is integrated into each workflow step's entry point (see SKILL.md). Each step validates its own state before proceeding, so the orchestrator simply jumps to the current `step` field.

## Entry

```bash
ls .workspace/pipeline/*/issue-*.state.json 2>/dev/null
```

If found, read state, then jump to the step indicated by the `step` field. Each step's self-validation handles the rest.

## Step self-validation summary

| step | Entry validation |
|------|-----------------|
| `build` | Check if PR exists via `gh pr list --head {branch}`. PR open -> jump to `review`. PR merged -> jump to `log`. No PR -> re-run `/dev-build`. |
| `review` | `pipeline_check_review_exists` first. Found -> process review (skip pane open). Not found -> check if reviewPane alive -> poll or open new. |
| `resolve` | `pipeline_check_new_commits` first. Found -> process commits (skip pane open). Not found -> check if resolvePane alive -> poll or open new. |
| `merge` | `gh pr view --json state`. MERGED -> jump to `log`. OPEN -> ask user. |
| `merge-failed` | Same as `merge`. |
| `log` | Re-run `/dev-log` (idempotent). |

## Pane failure recovery

When `pipeline_open_pane_with_retry` returns `MAX_RETRIES` (rc=5):

1. stderr contains diagnosis from dead pane output
2. Check basics: `which claude`, `tmux list-sessions`, `pipeline_resolve_worktree_path`
3. Report all diagnostics to user
4. User decides: fix environment and retry (reset retries in state) or abort

## Stale state

If PR already merged and logged, delete state file and report completed.
