---
name: dev-codex-pipeline
description: "Run dev-pipeline with synchronous review polling (no task-notification). Default tool: codex. Use when: task notifications are unavailable or codex is preferred. Do NOT use when: task notifications work and claude is preferred - use /dev-pipeline instead."
---

# Dev-Codex-Pipeline

Synchronous wrapper around `$dev-pipeline`. Runs the same state machine with no turn breaks.

## Invariants

All `$dev-pipeline` invariants apply. Additionally:

1. **No turn breaks.** Run build through log in a single turn. Stop only on terminal states.
2. **Default tool is `codex`. Always pass `--tool` to the run command.** Use `codex` unless the user explicitly provided a different value via `--tool`.
3. **Do not modify dev-pipeline skills or scripts.** This skill is a caller, not an owner.
4. **Edits only in resolve step**, only in the issue worktree.

## Inputs

- `AREA`: `client` | `server` | `workspace`
- `ISSUE`: GitHub issue number
- `TOOL` (optional): default `codex`. **Initialize `TOOL=codex` at skill start unless the user explicitly provided a different value.**

## Workflow

Before running any step, set `TOOL=codex` unless the user explicitly specified `--tool`. Never omit `--tool` from the run command.

Follow `$dev-pipeline` workflow for all steps except `review_dispatch`. Steps that are identical to base: init, build, review_process, suggestion_decide, resolve, merge, cleanup_wt, log.

### Override: review_dispatch (synchronous)

Base dev-pipeline ends the turn at dispatch and resumes on task notification. This skill runs synchronously instead.

On `dispatch` action:

1. Run synchronously (do NOT use `run_in_background`):
   `python3 -m dev_pipeline run --issue $ISSUE --area $AREA --pr $PR --tool ${TOOL:-codex}`
2. Enter poll loop:
   `python3 -m dev_pipeline step review-wait --issue $ISSUE --area $AREA`

| action | Next |
|--------|------|
| `review` | review_process with `data.reviewId` |
| `retry` | review_dispatch with `data.tool` |
| `pending` | `sleep 10`, re-call review-wait. Max 60 polls (10 min). Escalate if exceeded. |
| `escalate` | Stop, report `data.reason` |

On `found` action: go to review_process with `data.reviewId` (same as base).

## Terminal states

Stop and report on: `escalate`, `error`, `closed`.
Stop and ask user on: `round_limit` with Critical or Warning > 0.
Auto-merge on: `round_limit` with suggestion-only.

## Error handling

On any step error: `python3 -m dev_pipeline escalation --issue "$ISSUE" --area "$AREA" --step "$STEP"`
