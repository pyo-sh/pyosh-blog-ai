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

```bash
source scripts/orchestrate-helpers.sh
ISSUES="1 2 3 4 5"

for N in $ISSUES; do
  DEPS=$(bash scripts/parse-dependencies.sh "$N" "{area_dir}")
  # stdout: space-separated dependency issue numbers, or empty
done
```

Build DAG: `dag[N]="dep1 dep2"` (N depends on dep1, dep2).

Cycle detection -> abort with error if cycle found. See [dependency-resolution.md](references/dependency-resolution.md).

Write initial state:

```json
{
  "area": "client",
  "batchId": "batch-20260301-001",
  "issues": [1, 2, 3, 4, 5],
  "dag": {"3": [1, 2], "4": [3]},
  "status": {
    "1": "pending", "2": "pending",
    "3": "blocked", "4": "blocked", "5": "pending"
  },
  "dispatched": {},
  "agent": "claude:sonnet",
  "maxConcurrent": 4,
  "createdAt": "2026-03-01T00:00:00Z",
  "updatedAt": "2026-03-01T00:00:00Z"
}
```

### 4. Initial dispatch

For each `pending` issue (no unmet deps), up to `maxConcurrent`:

```bash
PID=$(orch_dispatch "$ISSUE" "$AREA_DIR" "$AGENT")
orch_record_dispatch "$AREA" "$ISSUE" "$PID"
```

Each dispatch launches a background `claude -p` process running `/dev-pipeline`. The process runs autonomously - no stdin, no user interaction needed.

Update status: `"dispatched"`. See [state-detection.md](references/state-detection.md).

### 5. Poll cycle

Run continuously (30-second interval):

```bash
while true; do
  orch_poll_cycle "$AREA" "$AREA_DIR" "$AGENT"
  REMAINING=$(orch_state_read "$AREA" | jq \
    '[.status | to_entries[] | select(.value == "pending" or .value == "dispatched" or .value == "blocked")] | length')
  [ "$REMAINING" -eq 0 ] && break
  sleep 30
done
```

`orch_poll_cycle` does, for each dispatched issue:

1. **Completion check** -> `orch_check_completion "$ISSUE" "$AREA_DIR"`
   - Signal file exists -> mark `completed` or `failed`
   - Process exited + pipeline state gone -> mark `completed`
   - Process exited + no PR -> mark `failed`

2. **Stall detection** -> `orch_detect_stall "$ISSUE" "$AREA_DIR"`
   - No new commits in 10 min -> warn user, offer retry

3. **Unblock** -> on any `completed` or `failed`, call `orch_unblock "$AREA" "$ISSUE"`
   - Find issues whose only remaining blocker was this issue
   - For each newly-unblocked issue -> dispatch

4. **Dispatch pending** -> for any `pending` issues with met deps, launch new process

5. **Report** -> print status to orchestrator output

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
