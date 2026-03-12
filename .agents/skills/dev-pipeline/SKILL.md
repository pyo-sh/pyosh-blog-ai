---
name: dev-pipeline
description: Orchestrate /dev-build -> /dev-review -> resolve (direct) -> merge for a monorepo with area-scoped worktrees. Headless review sessions start from monorepo root so skills resolve correctly; resolve runs directly in the pipeline session. Activates on "/dev-pipeline", "run pipeline", "automated review", etc.
---

# Dev-Pipeline

Orchestrate build -> review -> resolve -> merge -> log for area-scoped issues.

> CLI: `cd .agents/skills/dev-pipeline/scripts && python -m dev_pipeline <cmd>`
> Worktree: `.workspace/worktrees/{area}/issue-{N}` | State: `.workspace/pipeline/{area}/issue-{N}.state.json`

## Invariants

1. **Headless review cwd is always monorepo root**. Never start `claude -p` from a worktree.
2. **Feature-branch edits happen only in the issue worktree**.
3. **gh commands use explicit repo selection** (`-R owner/name`).
4. **Review dispatch always via `python -m dev_pipeline run`**. Never invoke review tools directly.
5. **Resolve runs directly in the pipeline session**, not as a headless sub-agent.
6. **Merge lock held inside one CLI call** (`python -m dev_pipeline merge`).
7. **`run`/`cleanup` manage the issue lease internally.** `--owner manual` for interactive; `--owner pipeline` for automated.
8. **All transient files are area-scoped** (`state`, `logs`, `messages`, `worktrees` under `.workspace/.../{area}/`).

## State machine

| From | To | Trigger | Turn break? |
|---|---|---|---|
| `build` | `review_dispatch` | /dev-build + PR created | No |
| `review_dispatch` | `review_wait` | Background review dispatched | **Yes** |
| `review_wait` | `review_process` | Review found on GitHub | No |
| `review_wait` | `review_dispatch` | Review not found + job failed | No |
| `review_process` | `resolve` | Critical > 0 or Warning > 0 | No |
| `review_process` | `merge` | Critical = 0 and Warning = 0 | No |
| `resolve` | `review_dispatch` | skipReview=false, fixes applied | No |
| `resolve` | `merge` | skipReview=true | No |
| `merge` | `log` | PR merged | No |
| `log` | (done) | Cleanup complete | No |

Only `review_dispatch -> review_wait` requires a turn break. All other transitions happen within the same turn.

## Workflow

### 0. Initialize / resume
`python -m dev_pipeline init --area "$AREA" --issue "$ISSUE"`
If state exists, resume from `.step`. On crash: `python -m dev_pipeline sync-state --issue "$ISSUE" --area "$AREA"`

### 1. build
Pre: `python -m dev_pipeline step build --issue $ISSUE --area $AREA --phase setup`
Act: `/dev-build root #$ISSUE`
Post: `python -m dev_pipeline step build --issue $ISSUE --area $AREA --phase finalize` -> review_dispatch

### 2a. review_dispatch
`python -m dev_pipeline step review-dispatch --issue $ISSUE --area $AREA [--tool $TOOL]`

| action | Next |
|---|---|
| `found` | review_process (`data.reviewId`) |
| `dispatch` | `python -m dev_pipeline run ... --pr $PR --tool $TOOL` in **background** -> **end turn** (do not sleep, poll, or output status; resume on task-notification only) |
| `error` | Stop, report |

### 2b. review_wait (on resume after task-notification)
`python -m dev_pipeline step review-wait --issue $ISSUE --area $AREA`

| action | Next |
|---|---|
| `review` | review_process (`data.reviewId`) |
| `retry` | review_dispatch (`data.tool` if present) |
| `escalate` | Stop, report `data.reason` |

Extract `REVIEW_ID` from the step `data` JSON output before calling Step 3.

### 3. review_process
`python -m dev_pipeline step review-process --issue $ISSUE --area $AREA --review-id $REVIEW_ID`

| action | Next |
|---|---|
| `clean` | merge |
| `resolve` | resolve |
| `round_limit` | Interactive: ask user (continue / merge as-is / abort). Headless: `escalate` for Critical/Warning; auto-merge for suggestion-only |
| `suggestion_only` | AI decides (see below) |
| `escalate` | Stop, report |

**`suggestion_only` rules** (Critical=0, Warning=0, Suggestion>0; first matching rule wins):
- Style/formatting only, all 1-line -> merge (auto)
- Logic change or structural impact -> resolve then re-review (skipReview=false)
- All trivial, count <= 3 -> resolve then merge (skipReview=true)
- Otherwise -> merge (auto)

### 4. resolve
Pre: `python -m dev_pipeline step resolve --issue $ISSUE --area $AREA --phase setup`
`data`: `reviewBody`, `comments` (JSON array), `worktreePath`
Act: Fix code in worktree. `[CRITICAL]`/`[WARNING]`: must fix. `[SUGGESTION]`: fix if valid.
Post: `python -m dev_pipeline step resolve --issue $ISSUE --area $AREA --phase finalize`

| action | Next |
|---|---|
| `re_review` | review_dispatch |
| `merge` | merge |

### 5. merge
`python -m dev_pipeline step merge --issue $ISSUE --area $AREA`

| action | Next |
|---|---|
| `merged` / `already_merged` | log |
| `retry` | merge (re-run) |
| `closed` / `escalate` | Stop, report |

### 6. log + cleanup
Act: `/dev-log`
Post: `python -m dev_pipeline step log --issue $ISSUE --area $AREA --phase finalize` -> Done.

## Constraints

- **Do not end your turn between steps** except Step 2a (review dispatch).
- **Auto-merge** when Critical=0 AND Warning=0, or user approves.
- **User approval required** when round limit reached with Critical/Warning.
- Source edits only in resolve step, only in the issue worktree.
- On error: `python -m dev_pipeline escalation --issue "$ISSUE" --area "$AREA" --step "$STEP"`

## References

- [Process lifecycle](references/process-lifecycle.md) - headless pattern, merge queue, step subcommands
- [Recovery](references/recovery.md) - step self-validation, self-healing
- [Python migration spec](references/python-migration-spec.md) - state schema, package layout
