---
name: dev-orchestrator
description: Orchestrate multiple GitHub issues in parallel via headless `claude -p` background processes with dependency-aware scheduling. Dispatches /dev-pipeline per issue as a subprocess, monitors completion, and auto-unblocks dependent issues. Activates on "/dev-orchestrator", "run orchestrator", "batch issues", "parallel pipeline", etc.
---

# Dev-Orchestrator

Thin wrapper over `orchctl`. All operational logic runs inside the controller; this skill handles user interaction, command routing, and exception reporting.

> `orchctl` install: `pip install -e tools/orchctl` from monorepo root
> DB path: `ORCHCTL_DB` env var, or default `~/.orchctl/orchctl.db`
> Area definitions: [monorepo-layout.md](../../references/monorepo-layout.md)

## Commands

Parse the user's request into one of the commands below and call `orchctl` accordingly. Report CLI output verbatim; add a brief summary when the output is long.

### start area=\<area\>

Initialize and start the reconciliation loop for an area.

```bash
# 1. Initialize DB (idempotent)
orchctl init

# 2. Apply policy if file is available (auto-discovers path)
orchctl apply-policy

# 3. Run first reconcile pass (discovery enqueues open issues when enabled)
orchctl reconcile --area <area>

# 4. Show current state
orchctl status
```

Then enter the continuous loop (poll every 30 s):

```bash
# orchctl status --json shape: {"issues": {"<state>": <count>, ...}, "active_attempts": [...]}
MAX_POLLS=120  # 1 hour at 30s intervals
POLL=0
while true; do
  sleep 30
  orchctl reconcile --area <area>
  REMAINING=$(orchctl status --json | python3 -c "
import json, sys
d = json.load(sys.stdin)
active = {'pending', 'dispatched', 'blocked'}
print(sum(v for k, v in d.get('issues', {}).items() if k in active))
")
  [ "$REMAINING" -eq 0 ] && break
  (( ++POLL >= MAX_POLLS )) && {
    echo "Timeout: issues still active after 1h — check with orchctl status"
    break
  }
done
orchctl status
```

Stop the loop when all issues are `completed`, `failed-terminal`, or `skipped`.

Run `/dev-log` to record batch completion.

### resume area=\<area\>

Resume an interrupted run without reinitializing.

```bash
orchctl reconcile --area <area>
orchctl status
```

Then enter the continuous loop (same pattern as `start`). Run `/dev-log` after completion.

### status

```bash
orchctl status
# Machine-readable:
orchctl status --json
```

### doctor

```bash
orchctl doctor
# Machine-readable:
orchctl doctor --json
```

Checks: schema version, orphan attempts, stale leases. Returns 0 if healthy, 1 if issues found.

### reconcile area=\<area\>

Run one idempotent reconcile pass.

```bash
orchctl reconcile --area <area>
# Preview without side effects:
orchctl reconcile --area <area> --dry-run
```

### pause area=\<area\>

Stop new dispatches for the area (running workers continue to completion).

```bash
orchctl control pause <area>
```

Undo:

```bash
orchctl control resume <area>
```

### drain

Stop all new dispatches globally (running workers finish normally).

```bash
orchctl control drain
```

Undo:

```bash
orchctl control undrain
```

### stop area=\<area\>

Cancel all dispatched issues for the area. **Confirm with the user before running.**

```bash
orchctl control stop <area> --confirm
```

### requeue area=\<area\> issue=\<N\>

Move a `failed-terminal`, `cancelled`, or `needs-human` issue back to `pending`.

```bash
orchctl control requeue --area <area> --issue <N>
```

### merge-gate area=\<area\> issue=\<N\>

Evaluate whether a completed issue is eligible for merge.

```bash
orchctl merge-gate --area <area> --issue <N>
# Exits 0 = eligible, 1 = blocked, 2 = error
```

## Agent selection

The pipeline runner is always `claude -p` (Claude Code is required for pipeline skills). The review subprocess tool and model are configured per issue dispatch.

Native agent/model selection in `orchctl` is planned for a future stage. Until then, the values are passed to `/dev-pipeline` outside of orchctl (for example, via the `/dev-pipeline` skill directly or via pipeline state). Supported tool values: `claude`, `claude:<model>`, `codex`, `codex:<model>`.

## Policy

`orchctl` reads `policy.yaml` automatically on every reconcile pass, or apply it explicitly:

```bash
orchctl apply-policy
# Override path:
orchctl apply-policy --policy-file path/to/policy.yaml
```

Key settings:

| Key | Default | Effect |
|-----|---------|--------|
| `discovery_enabled` | `false` | Query GitHub and auto-enqueue open issues on each reconcile pass |
| `max_concurrent` | `4` | Max issues in `dispatched` state per area |
| `max_open_pr` | `2` | Global limit on simultaneously dispatched issues |
| `max_concurrent_repair` | `1` | Max concurrent retry attempts |
| `drain_mode` | `false` | Pause all new dispatches globally |
| `scope_include_labels` | `[]` | Only enqueue issues with these labels |
| `scope_exclude_labels` | `[]` | Skip issues with these labels |
| `merge_enabled` | `false` | Allow auto-merge via `merge-gate` |
| `protected_branches` | `main` | Branches blocked from auto-merge |

Sample file: `tools/orchctl/policy.yaml.sample`

## Invariants

- **Never merge PRs** - workers stop at ready-to-merge; merging is handled externally via `merge-gate`.
- **Never modify code** - all code changes happen inside dispatched worker processes.

## Exception reporting

When `orchctl` exits non-zero, report to the user:

1. The command that failed.
2. The exit code and captured stderr.
3. The appropriate resolution:

| Error message | Resolution |
|---------------|------------|
| `Database not initialised` | Run `orchctl init` |
| `Database schema is out of date` | Run `orchctl init` to migrate |
| `lease held by another process` | Another reconcile is running - wait and retry, or check with `orchctl doctor` |
| `issue not found in area` | Verify area and issue number; run `orchctl status --json` to list known issues |
| Issue stuck in `needs-human` | Review the issue manually, then `orchctl control requeue --area <area> --issue <N>` |

For unrecognised errors, show the full stderr to the user and ask whether to continue.
