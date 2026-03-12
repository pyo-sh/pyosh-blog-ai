# Pipeline recovery

Resume from state file on crash/disconnect. Jump to the `step` field - each step self-validates on entry.

## Recovery strategy (v3)

Step functions perform entry validation internally. Recovery procedure:

1. Read `.step` from the state file
2. `PYTHONPATH=$MONOREPO_ROOT/.agents/skills/dev-pipeline/scripts python3 -m dev_pipeline sync-state --issue N --area A` (syncs latest SHA and review ID from GitHub/git)
3. Run the corresponding step command - the step function internally:
   - Checks worktree existence and state
   - Compares LOCAL_HEAD vs state SHA
   - Verifies working tree clean/dirty status
   - Returns `action: recovery` on inconsistency (reports to user)

### Recovery action mapping

| Step function | Recovery situation | action |
|---|---|---|
| `resolve --phase setup` | HEAD != state SHA + clean | `recovery` (prior commit detected) |
| `resolve --phase setup` | HEAD != state SHA + dirty | `recovery` (uncommitted changes) |
| `resolve --phase setup` | HEAD == state SHA + dirty | `recovery` (partial fix) |
| `resolve --phase setup` | Remote has new commits | `recovery` (external change) |
| `build --phase setup` | Rebase failure | merge_no_edit fallback |
| `merge` | Merge failure | `retry` (stage_retry handled internally) |
| `merge` | Retries exhausted | `escalate` |

## Self-healing on failure

Headless review exit non-zero + API finds no result, or resolve fails mid-session:

1. `state_store.stage_retry()` / CLI `stage-retry` - increment, check max (3)
2. Available -> `state_store.recovery_log_append()` (via CLI `stage-retry`), retry step
3. Exhausted -> `controller.format_escalation()` / CLI `escalation`, report to user

## Stale state

PR already merged and logged -> delete state file, report completed.
