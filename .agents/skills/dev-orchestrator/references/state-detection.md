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

The signal file is optional. If present, it takes highest priority.
It is not written automatically - the pipeline AI or an external hook must produce it.
In practice, the primary detection path is method 2 (state file absence).

If no signal file exists, fall back to method 2.

### 2. Pane command + pipeline state file

Check the pane's current foreground command via tmux:

```bash
cmd=$(tmux display-message -t "$pane_id" -p '#{pane_current_command}')
```

| Command | State file | pipelineStarted | Result |
|---------|-----------|-----------------|--------|
| `claude`/`codex`/`node` | exists | * | `running` (marks `pipelineStarted: true`) |
| `claude`/`codex`/`node` | absent | true | `completed` (Step 7 deleted it) |
| `claude`/`codex`/`node` | absent | false | `running` (not created yet) |
| shell / pane dead | * | * | fall through to method 3 |

The `pipelineStarted` flag in `batch.state.json` tracks whether the pipeline state file
was ever observed. This prevents false `completed` judgments when the state file hasn't
been created yet (dispatch just happened, pipeline still in Step 1).

Pipeline AI typically stays in the session after completing work, so the state file check
while AI is running is the primary completion detection path.

### 3. Pipeline state file (AI exited)

When AI has exited (shell prompt or pane dead):

| State file | pipelineStarted | Result |
|-----------|-----------------|--------|
| absent | true | `completed` |
| absent | false | fall through (early crash, never started) |
| exists | * | fall through (pipeline didn't finish) |

### 4. PR status (fallback)

After methods 2-3 are inconclusive:

```bash
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

## Pane Release

After marking an issue `completed` or `failed`, the orchestrator releases the
pane so it becomes available for the next dispatch.

Two-layer approach:

1. **Primary**: The dispatch prompt includes `"After completing all steps, exit the session."` -
   AI exits naturally, pane returns to shell prompt.
2. **Fallback**: `orch_release_pane` sends Ctrl+C if the AI process is still running.
   Called automatically by `orch_poll_cycle` after completion detection.

`orch_release_pane` does NOT destroy the pane (unlike `pipeline_kill_pane`).
The pane stays alive at a shell prompt, ready for the next dispatch.

## Status State Machine

```
pending
  └─(dispatch)──► dispatched
                    ├─(completion: ok)──► completed + release pane
                    ├─(completion: fail)─► failed + release pane
                    └─(stall + skip)──────► failed + release pane

blocked
  └─(all deps completed OR failed)──► pending

completed ──(triggers orch_unblock)
failed    ──(triggers orch_unblock - dependency was attempted, downstream unblocked)
```

## Polling Interval

Default: 30 seconds per cycle.

`orch_poll_cycle` processes ALL dispatched issues per cycle, so the effective
per-issue latency is still 30s regardless of batch size.
