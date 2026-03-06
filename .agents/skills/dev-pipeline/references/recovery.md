# Pipeline recovery

Resume from state file on crash/disconnect. Jump to the `step` field - each step self-validates on entry.

## Step self-validation

| step | Entry validation |
|------|-----------------|
| `build` | `gh pr list --head {branch}`. PR open -> `review`. Merged -> `log`. None -> re-run `/dev-build`. |
| `review` | `pipeline_check_review_exists`. Found -> process review. Not found -> run headless. |
| `resolve` | `pipeline_check_new_commits`. Found -> process commits. Not found -> run headless. |
| `merge` / `merge-failed` | `gh pr view --json state`. MERGED -> `log`. OPEN -> ask user. |
| `log` | Re-run `/dev-log` (idempotent). |

## Self-healing on failure

Headless exit non-zero + API finds no result:

1. `pipeline_stage_retry` - increment, check max (3)
2. Available -> `pipeline_recovery_log`, retry step
3. Exhausted -> `pipeline_format_escalation`, report to user

## Stale state

PR already merged and logged -> delete state file, report completed.
