# Decision 001: Docs branch git strategy

## Metadata
- **Date**: 2026-03-13
- **Status**: accepted
- **Related Issue**: #168

## Background

dev-log commits documentation directly to `main` via lock-merge. This creates noise on the main branch history and prevents batch documentation management. Each dev-log standalone run creates a worktree, writes docs, rebases onto main, and ff-merges - mixing doc commits with feature/fix commits.

## Option comparison

| Option | Pros | Cons |
|--------|------|------|
| A. Keep current (direct to main) | Simple, immediate visibility | Noisy main history, no batch management |
| B. Long-lived docs branch + squash-merge PR | Clean main history, batch control, PR traceability | Extra branch to maintain, sync after merge |
| C. Per-session PR to main | PR review possible | Too many small PRs, no batching |

## Final decision

**Option B** - long-lived `docs` branch with squash-merge via `/dev-archive` skill.

- dev-log commits go to `docs` branch (worktree branches from docs, push to origin/docs)
- `/dev-archive` creates squash-merge PR for docs -> main when batching is desired
- Pipeline order changes from log -> merge to merge -> log (log no longer blocks merge)

## Follow-up actions

- dev-log SKILL.md rewritten for linear 7-phase flow
- dev-archive skill created with check-diff, ensure-label, create-pr, squash-merge, sync-branch
- Pipeline steps.py reordered: merge before log, log runs cleanup and returns done
