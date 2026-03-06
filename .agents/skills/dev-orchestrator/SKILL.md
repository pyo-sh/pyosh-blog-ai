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

| Agent value | Headless command |
|-------------|-----------------|
| `claude` | `claude -p --dangerously-skip-permissions ...` |
| `claude:<model>` | `claude -p --model <model> --dangerously-skip-permissions ...` |

Examples: `"claude"`, `"claude:sonnet"`, `"claude:opus"`.

Store in state as `"agent": "claude:sonnet"` etc. Model aliases (`sonnet`, `opus`) are resolved by the CLI.

## State files

```
.workspace/orchestrate/{area}/batch.state.json   # batch-level DAG + status
.workspace/orchestrate/{area}/issue-{N}.exit     # signal: pipeline completed (content: "ok" or "fail")
.workspace/orchestrate/{area}/issue-{N}.log      # stdout from headless process
.workspace/orchestrate/{area}/issue-{N}.err      # stderr from headless process
```

Pipeline state at `.workspace/pipeline/{area}/issue-{N}.state.json` is read-only from the orchestrator's perspective.

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

Write initial state via `orch_init`. Schema: `area`, `batchId`, `issues[]`, `dag{}`, `status{}`, `dispatched{}`, `agent`, `maxConcurrent` (default 4), timestamps.

### 4. Initial dispatch

For each `pending` issue (no unmet deps), up to `maxConcurrent`:

```bash
PID=$(orch_dispatch "$ISSUE" "$AREA_DIR" "$AGENT")
orch_record_dispatch "$AREA" "$ISSUE" "$PID"
```

Each dispatch launches a background `claude -p` process running `/dev-pipeline`. The process runs autonomously - no stdin, no user interaction needed.

Update status: `"dispatched"`. See [state-detection.md](references/state-detection.md).

### 5. Poll cycle

Loop `orch_poll_cycle "$AREA" "$AREA_DIR" "$AGENT"` every 30 seconds until no `pending`/`dispatched`/`blocked` issues remain.

Each cycle, for every dispatched issue: check completion (`orch_check_completion`), detect stalls (`orch_detect_stall`), unblock dependents (`orch_unblock`), dispatch newly-pending issues, and print status. See [state-detection.md](references/state-detection.md) for detection logic.

### 6. Batch completion

All issues `completed` or `failed`:

```bash
orch_print_summary "$AREA"
```

Show table: issue -> status -> PR URL. For failed issues, ask user to handle manually.

Clean up:

```bash
rm -rf .workspace/orchestrate/{area}/
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
