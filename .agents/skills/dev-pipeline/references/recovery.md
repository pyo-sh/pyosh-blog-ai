# Pipeline recovery

Resume from state file when pipeline session crashes or disconnects.

Recovery is integrated into each workflow step's entry point (see SKILL.md). Each step validates its own state before proceeding, so the pipeline simply jumps to the current `step` field.

## Entry

```bash
ls .workspace/pipeline/*/issue-*.state.json 2>/dev/null
```

If found, read state, then jump to the step indicated by the `step` field. Each step's self-validation handles the rest.

## Step self-validation summary

| step | Entry validation |
|------|-----------------|
| `build` | Check if PR exists via `gh pr list --head {branch}`. PR open -> jump to `review`. PR merged -> jump to `log`. No PR -> re-run `/dev-build`. |
| `review` | `pipeline_check_review_exists` first. Found -> process review (skip headless run). Not found -> run headless review. |
| `resolve` | `pipeline_check_new_commits` first. Found -> process commits (skip headless run). Not found -> run headless resolve. |
| `merge` | `gh pr view --json state`. MERGED -> jump to `log`. OPEN -> ask user. |
| `merge-failed` | Same as `merge`. |
| `log` | Re-run `/dev-log` (idempotent). |

## Self-healing recovery

When `pipeline_run_headless` returns a non-zero exit code and API check finds no result:

1. Call `pipeline_stage_retry` to check/increment retry count
2. If retries available: log recovery action, retry the step
3. If max retries reached: call `pipeline_format_escalation`, report to user
4. User decides: fix and retry (reset retries in state) or abort

## Stale state

If PR already merged and logged, delete state file and report completed.
