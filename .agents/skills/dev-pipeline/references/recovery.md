# Pipeline recovery

Resume from state file on crash/disconnect. Jump to the `step` field - each step self-validates on entry.

## Step self-validation

| step | Entry validation |
|------|-----------------|
| `build` | If `.branch` exists: `gh pr list --head {branch}`. PR open -> `review`. Merged -> `log`. None -> re-run `/dev-build`. If no state file or no `.branch`: start fresh. |
| `review` | `github_client.check_review_exists()` / CLI `check-review`. Found -> process review (count severities, auto-decide based on round count). Not found -> run headless. |
| `resolve` | Check local `git rev-parse HEAD` vs `lastCommitSha`. Mismatch + clean -> push and skip to 4d. Mismatch + dirty -> stop, report to user. Match + dirty -> stop, report to user. Match + clean -> `github_client.check_new_commits()` / CLI `check-commits`. Found -> update `.lastCommitSha` + reset `.stageRetries.resolve`, show diff, ask user (context lost). Not found -> resolve directly in pipeline session. |
| `merge` | `gh pr view --json state`. MERGED -> `log`. CLOSED -> stop, report. OPEN -> merge. |
| `log` | Re-run `/dev-log` (idempotent). Delete state file after. |

## Self-healing on failure

Headless review exit non-zero + API finds no result, or resolve fails mid-session:

1. `state_store.stage_retry()` / CLI `stage-retry` - increment, check max (3)
2. Available -> `state_store.recovery_log_append()` (via CLI `stage-retry`), retry step
3. Exhausted -> `controller.format_escalation()` / CLI `escalation`, report to user

## Stale state

PR already merged and logged -> delete state file, report completed.
