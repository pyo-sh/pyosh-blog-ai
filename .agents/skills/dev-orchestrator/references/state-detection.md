# State Detection

How the orchestrator determines whether a dispatched issue's pipeline has completed,
failed, or stalled.

## Completion Detection

`orch_check_completion <issue> <area_dir>` checks in priority order:

### 1. Signal file (highest priority)

```
.workspace/orchestrate/{area}/issue-{N}.exit
```

Content `ok` → `completed`. Any other content → `failed`.

The signal file is written by the pipeline AI at the end of `/dev-pipeline` (Step 7 log):

```bash
echo "ok" > "$ORCH_BASE/$AREA/issue-${ISSUE}.exit"
```

If the pipeline AI does not write the signal file (older version), fall back to method 2.

### 2. Pane command (AI process running?)

Check the pane's current foreground command via tmux:

```bash
cmd=$(tmux display-message -t "$pane_id" -p '#{pane_current_command}')
```

| Command | Meaning |
|---------|---------|
| `claude`, `codex`, `node` | AI process still running → `running` |
| `bash`, `zsh`, `sh`, `fish` | AI exited, shell prompt → fall through to PR check |
| pane dead | Process crashed → fall through to PR check |

This replaces the previous pipeline state file-based detection, which caused false `failed` judgments
when the state file hadn't been created yet (grace period too short).

### 3. PR status (AI process finished)

After AI process exits or pane dies:

```bash
# Check for merged PR
gh pr list --search "Closes #${issue}" --state merged --json number --jq 'length'
```

- Merged PR exists → `completed`
- Open PR exists → `running` (pipeline may still be cleaning up)
- No PR at all → `failed`

## Stall Detection

`orch_detect_stall <area> <issue> <area_dir>` checks if the last activity timestamp
for a dispatched issue exceeds 10 minutes with no new commits on the PR.

### Activity tracking

`lastActivity` is set to current time when:
- Issue is first dispatched (`orch_record_dispatch`)
- A new commit is detected on the PR (`orch_update_last_activity`)

### Stall threshold

```
stall_seconds = 600  # 10 minutes
```

If `now - lastActivity > stall_seconds`:
1. Fetch latest commit SHA on the PR
2. Compare with `lastCommitSha` in state
3. Different → update `lastActivity` + `lastCommitSha`, return "not stalled"
4. Same → return "stalled"

### On stall detected

Orchestrator reports to user:

```
[orchestrator] STALL: Issue #N — no activity for 10+ minutes
  Pane: %3
  Last commit: abc1234 (10:05:00 UTC)
Options: [retry] [skip] [inspect]
```

User chooses:
- **retry** → kill pane, re-dispatch to same or different pane
- **skip** → mark issue `failed`, unblock any dependents
- **inspect** → user manually resolves, orchestrator resumes polling

## Status State Machine

```
pending
  └─(dispatch)──► dispatched
                    ├─(completion: ok)──► completed
                    ├─(completion: fail)─► failed
                    └─(stall + skip)──────► failed

blocked
  └─(all deps completed OR failed)──► pending

completed ──(triggers orch_unblock)
failed    ──(triggers orch_unblock — dependency was attempted, downstream unblocked)
```

## Polling Interval

Default: 30 seconds per cycle.

`orch_poll_cycle` processes ALL dispatched issues per cycle, so the effective
per-issue latency is still 30s regardless of batch size.
