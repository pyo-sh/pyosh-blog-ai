# Pipeline recovery

Resume from state file on crash/disconnect. Jump to the `step` field - each step self-validates on entry.

## Step self-validation

| step | Entry validation |
|------|-----------------|
| `build` | If `.branch` exists: `gh pr list --head {branch}`. PR open -> `review`. Merged -> `log`. None -> re-run `/dev-build`. If no state file or no `.branch`: start fresh. |
| `review` | `pipeline_check_review_exists`. Found -> process review (count severities, auto-decide based on round count). Not found -> run headless. |
| `resolve` | Check local `git rev-parse HEAD` vs `lastCommitSha`. Mismatch + clean -> push and skip to 4d. Mismatch + dirty -> stop, report to user. Match + dirty -> stop, report to user. Match + clean -> `pipeline_check_new_commits`. Found -> update `.lastCommitSha` + reset `.stageRetries.resolve`, show diff, ask user (context lost). Not found -> resolve directly in pipeline session. |
| `merge` | `gh pr view --json state`. MERGED -> `log`. CLOSED -> stop, report. OPEN -> merge. |
| `log` | Re-run `/dev-log` (idempotent). Delete state file after. |

## Self-healing on failure

Headless review exit non-zero + API finds no result, or resolve fails mid-session:

1. `pipeline_stage_retry` - increment, check max (3)
2. Available -> `pipeline_recovery_log`, retry step
3. Exhausted -> `pipeline_format_escalation`, report to user

## Stale state

PR already merged and logged -> delete state file, report completed.
