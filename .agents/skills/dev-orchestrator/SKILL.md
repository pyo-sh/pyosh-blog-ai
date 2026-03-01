---
name: dev-orchestrator
description: Orchestrate multiple GitHub issues in parallel across tmux panes with dependency-aware scheduling. Dispatches /dev-pipeline per issue to idle panes, monitors completion, and auto-unblocks dependent issues. Activates on "/dev-orchestrator", "run orchestrator", "batch issues", "parallel pipeline", etc.
---

# Dev-Orchestrator

Batch orchestration: build dependency DAG from issues → dispatch to idle panes via `/dev-pipeline` → monitor completion → auto-unblock dependents.

> Requires tmux session (`$TMUX`). Source helpers at start: `source scripts/orchestrate-helpers.sh`

## Agent Selection

**Ask the user** which AI agent to use for dispatched panes:

| Agent | Command pattern |
|-------|----------------|
| **Claude Code** | `claude --dangerously-skip-permissions '{prompt}'` |
| **Codex** | `codex exec --dangerously-bypass-approvals-and-sandbox '{prompt}'` |

Store in state as `"agent": "claude"` or `"agent": "codex"`.

## State Files

```
.workspace/orchestrate/{area}/batch.state.json   # batch-level DAG + status
.workspace/orchestrate/{area}/issue-{N}.exit     # signal: pipeline completed (content: "ok" or "fail")
```

Pipeline state at `.workspace/pipeline/{area}/issue-{N}.state.json` is read-only from the orchestrator's perspective.

## Workflow

### 0. Check Existing State

```bash
STATE_FILE=".workspace/orchestrate/{area}/batch.state.json"
```

Exists → **resume** ([recovery.md](references/recovery.md)). Not exists → Step 1.

### 1. Area Detection

```bash
WINDOW_NAME=$(tmux display-message -p '#{window_name}')
```

| Window name pattern | Area |
|---------------------|------|
| `client*` | `client` |
| `server*` | `server` |
| other | ask user |

Area dir: monorepo root (e.g., `/workspace`) for `workspace`, or `{monorepo}/{area}` for client/server.

### 2. Fetch & Filter Issues

```bash
cd {area_dir}
gh issue list --assignee @me --state open --json number,title,body,labels \
  --jq '.[] | select(.labels[].name == "{area}")'
```

Exclude issues already in pipeline state (`.workspace/pipeline/{area}/issue-*.state.json`).

Present list to user for confirmation before proceeding.

### 3. Build Dependency DAG

```bash
source scripts/orchestrate-helpers.sh
ISSUES="1 2 3 4 5"

for N in $ISSUES; do
  DEPS=$(bash scripts/parse-dependencies.sh "$N" "{area_dir}")
  # stdout: space-separated dependency issue numbers, or empty
done
```

Build DAG: `dag[N]="dep1 dep2"` (N depends on dep1, dep2).

Cycle detection → abort with error if cycle found. See [dependency-resolution.md](references/dependency-resolution.md).

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
  "agent": "codex",
  "orchestratorPane": "%1",
  "createdAt": "2026-03-01T00:00:00Z",
  "updatedAt": "2026-03-01T00:00:00Z"
}
```

### 4. Initial Dispatch

Find idle panes in the same tmux session:

```bash
IDLE_PANES=$(orch_find_idle_panes)
```

For each idle pane + each `pending` issue (no unmet deps), dispatch:

```bash
orch_dispatch "$ISSUE" "$PANE_ID" "$AREA_DIR" "$AGENT"
```

Update status: `"dispatched"`. See [state-detection.md](references/state-detection.md).

### 5. Poll Cycle

Run continuously (30-second interval):

```bash
while true; do
  orch_poll_cycle "$AREA" "$AREA_DIR" "$AGENT" "$ORCH_PANE"
  sleep 30
done
```

`orch_poll_cycle` does, for each dispatched issue:

1. **Completion check** → `orch_check_completion "$ISSUE" "$AREA_DIR"`
   - Signal file exists → mark `completed` or `failed`
   - Pipeline state gone + PR merged → mark `completed`
   - Pipeline state gone + PR not merged/absent → mark `failed`

2. **Stall detection** → `orch_detect_stall "$ISSUE" "$AREA_DIR"`
   - No new commits in 10 min → warn user, offer retry

3. **Unblock** → on any `completed` or `failed`, call `orch_unblock "$AREA" "$ISSUE"`
   - Find issues whose only remaining blocker was this issue
   - For each newly-unblocked issue + idle pane → dispatch

4. **Idle pane dispatch** → for any `pending` issues with met deps + idle panes, dispatch

5. **Report** → print status summary to orchestrator pane

### 6. Batch Completion

All issues `completed` or `failed`:

```bash
orch_print_summary "$AREA" "$AREA_DIR"
```

Show table: issue → status → PR URL. For failed issues, ask user to handle manually.

Clean up:

```bash
rm -rf .workspace/orchestrate/{area}/
```

### 7. Record Progress

Run `/dev-log` to record batch completion.

## Constraints

- **Never merge PRs** — merging is handled by each `/dev-pipeline` instance
- **Never modify code** — code changes happen only inside dispatched panes
- **Dispatch at most one issue per pane** — no overloading
- **Max concurrency** = number of idle panes found at dispatch time
- On unrecoverable error: save state, report to user

## References

- [Dependency resolution](references/dependency-resolution.md) — DAG construction, cycle detection, edge cases
- [State detection](references/state-detection.md) — completion/stall detection, status state machine
- [Recovery strategy](references/recovery.md) — crash recovery, auto-retry policy
