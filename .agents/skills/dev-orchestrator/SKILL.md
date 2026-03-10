---
name: dev-orchestrator
description: Orchestrate multiple GitHub issues in parallel via headless `claude -p` background processes with dependency-aware scheduling. Dispatches /dev-pipeline per issue as a subprocess, monitors completion, and auto-unblocks dependent issues. Activates on "/dev-orchestrator", "run orchestrator", "batch issues", "parallel pipeline", etc.
---

# Dev-Orchestrator

Batch orchestration: build dependency DAG from issues -> dispatch headless `claude -p` processes via `/dev-pipeline` -> monitor completion -> auto-unblock dependents.

> Area definitions, directory/repo mappings: [monorepo-layout.md](../../references/monorepo-layout.md)
> Source helpers at start: `source scripts/orchestrate-helpers.sh`

## Agent selection

**Ask the user** which AI agent/model to use for dispatched processes:

| Agent value | Pipeline runner | Review subprocess |
|-------------|----------------|-------------------|
| `claude` | `claude -p` (default model) | `claude -p` with `/dev-review` skill |
| `claude:<model>` | `claude -p --model <model>` | `claude -p --model <model>` with `/dev-review` skill |
| `codex` | `claude -p` (default model) | `codex exec review --base origin/main` |
| `codex:<model>` | `claude -p` (default model) | `codex exec review --model <model> --base origin/main` |

Examples: `"claude"`, `"claude:sonnet"`, `"codex"`, `"codex:o3"`.

The outer pipeline runner is always `claude -p` because the pipeline requires Claude Code skills. The tool value (`claude`/`codex`) controls which CLI runs the review subprocess. When tool is `codex`, the outer pipeline uses the default Claude model (the model applies to the review subprocess only).

Store in state as `"agent": "codex:o3"` etc.

## State files

```
.workspace/orchestrate/{area}/batch.state.json                          # batch-level DAG + status + provider health
.workspace/orchestrate/{area}/gh-errors.log                             # captured stderr from failed gh calls
.workspace/orchestrate/{area}/issues/{N}/attempts/{attemptId}/          # per-attempt artifact directory
  terminal.json   # completion contract (attemptId, status, prNumber, merged, headSha)
  worker.log      # stdout from headless process
  worker.err      # stderr from headless process
  heartbeat       # epoch timestamp, updated every 60s
  pid             # wrapper PID (= PGID), transient
.workspace/orchestrate/{area}/archive/{batchId}/                        # archived batch (batch.state.json + issues/ + gh-errors.log)
```

`attemptId` format: `issue-{N}-a{M}` where M is the retry count (0-based).

Each retry creates a new attempt directory. Previous attempt artifacts are preserved for debugging. Stale artifact confusion is eliminated because paths are unique per attempt.

After batch completion, `orch_archive_batch` moves the active area content into `archive/{batchId}/`. Up to 5 archives are kept per area (rotation policy); older archives are deleted automatically.

Pipeline state at `.workspace/pipeline/{area}/issue-{N}.state.json` is read-only from the orchestrator's perspective.

State file updates use `flock` for mutual exclusion.

## Workflow

### 0. Check existing state

```bash
STATE_FILE=".workspace/orchestrate/{area}/batch.state.json"
```

Exists -> **resume** ([recovery.md](references/recovery.md)). Not exists -> Step 1.

### 1. Area detection

Determine area from user input or context (issue labels, current directory).

| Context | Area |
|---------|------|
| Issue has `client` label | `client` |
| Issue has `server` label | `server` |
| User specifies | as given |

Area dir: monorepo root (e.g., `/workspace`) for `workspace`, or `{monorepo}/{area}` for client/server.

### 2. Fetch & filter issues

Always use `-R` to target the correct GitHub repo:

```bash
REPO=$(monorepo_area_repo "$AREA")
gh issue list -R "$REPO" --assignee @me --state open \
  --json number,title,body,labels \
  --jq '.[] | select(.labels[].name == "{area}")'
```

Exclude issues already in pipeline state (`.workspace/pipeline/{area}/issue-*.state.json`).

Present list to user for confirmation before proceeding.

### 3. Build dependency DAG

Parse `### Dependencies` section from each issue body via `parse-dependencies.sh`. Build DAG: `dag[N]="dep1 dep2"`. Run cycle detection - abort if cycle found. See [dependency-resolution.md](references/dependency-resolution.md).

Write initial state via `orch_init`. Schema: `area`, `batchId`, `issues[]`, `dag{}`, `status{}`, `dispatched{}`, `agent`, `maxConcurrent` (default 4), `providers` (GitHub circuit breaker), timestamps.

### 4. Enter poll cycle (dispatch + monitor)

**Do NOT dispatch issues manually.** Use `orch_poll_cycle` for both initial and subsequent dispatches. The poll cycle handles dispatch atomically (launch + state recording in one call), respects `maxConcurrent`, and prevents orphan processes.

`orch_dispatch` is atomic: it launches the background process AND records it in state. If state recording fails, it kills the orphan process automatically.

```bash
# Run first poll cycle immediately (dispatches initial pending issues)
orch_poll_cycle "$AREA" "$AREA_DIR" "$AGENT"

# Then loop every 30 seconds
while true; do
  sleep 30
  orch_poll_cycle "$AREA" "$AREA_DIR" "$AGENT"

  REMAINING=$(orch_state_read "$AREA" | jq \
    '[.status | to_entries[] | select(.value == "pending" or .value == "dispatched" or .value == "blocked")] | length')
  [ "$REMAINING" -eq 0 ] && break
done
```

Each cycle: check completion, detect stalls, unblock dependents, dispatch newly-pending issues (up to `maxConcurrent`), and print status. See [state-detection.md](references/state-detection.md) for detection logic.

### 6. Batch completion

All issues `completed`, `failed`, or `skipped_dep_failed`:

```bash
orch_print_summary "$AREA"
```

Show table: issue -> status -> PR URL. For failed issues, ask user to handle manually.

Archive the batch (preserves state, logs, and artifacts for audit):

```bash
orch_archive_batch "$AREA"
```

This moves `.workspace/orchestrate/{area}/` content to `.workspace/orchestrate/{area}/archive/{batchId}/` and applies the rotation policy (keeps last 5 by default).

To view previous batches:

```bash
orch_archive_list "$AREA"
```

### 7. Record progress

Run `/dev-log` to record batch completion.

## Constraints

- **Never merge PRs** - merging is handled by each `/dev-pipeline` instance
- **Never modify code** - code changes happen only inside dispatched processes
- **Max concurrency** controlled by `maxConcurrent` (default: 4)
- Always use `-R <owner/repo>` or `cd {area_dir}` for `gh` commands - never run from the wrong repo
- Avoid deprecated `gh` fields (`projectCards` etc.) - use `number,title,state,body,url`
- On unrecoverable error: save state, report to user

## References

- [Dependency resolution](references/dependency-resolution.md) - DAG construction, cycle detection, edge cases
- [State detection](references/state-detection.md) - completion/stall detection, status state machine
- [Recovery strategy](references/recovery.md) - crash recovery, auto-retry policy
