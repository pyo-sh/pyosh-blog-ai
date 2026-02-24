---
name: dev-log
description: Manage progress/, findings/, and decisions/ records in the pyosh-blog monorepo. Use when (1) recording progress after task completion, (2) documenting technical research as findings, (3) writing architecture/tech decisions, (4) user requests "/dev-log", "record this", "write progress", etc. Parallel-agent safe (worktree isolation + lock merge).
---

# Dev-Log

Record-only skill. Task management via GitHub Issues, global rules in `CLAUDE.md`.

**Core strategy**: worktree isolation → scan indices → write records → lock merge → cleanup

## Directory Structure

```
docs/{client|server}/
├── progress.index.md
├── findings.index.md
├── decisions.index.md
├── progress/
│   └── progress.YYYY-MM-DD.md
├── findings/
│   └── findings.NNN-topic.md
└── decisions/
    └── decision-NNN-topic.md
```

## File Naming

| Type | Format | ID/Date |
|------|--------|---------|
| Progress | `progress.YYYY-MM-DD.md` | ISO 8601 |
| Findings | `findings.NNN-topic.md` | 3-digit seq, kebab-case |
| Decision | `decision-NNN-topic.md` | 3-digit seq, kebab-case |

## Workflow (parallel-safe)

> Use **worktree isolation** to prevent file conflicts when running parallel agents.
> Detailed git commands: [worktree-merge.md](references/worktree-merge.md)

### Phase 1: Create Worktree

Timestamp-based worktree + branch. All file operations happen inside the worktree.
→ Commands: [worktree-merge.md § Phase 1](references/worktree-merge.md)

### Phase 2: Check Context Before Recording
- Read `progress.index.md` + `findings.index.md` + `decisions.index.md` inside the worktree
- Selectively read relevant sub-files only (do not read all)

### Phase 3: Write Records (inside worktree)
- **Technical research**: Create `findings/findings.NNN-topic.md` + update `findings.index.md`
- **Architecture decision**: Create `decisions/decision-NNN-topic.md` (draft) + update `decisions.index.md`
- **Task completion**: Create/update `progress/progress.YYYY-MM-DD.md` + update `progress.index.md`
- Create missing folders/files as needed ([templates.md](references/templates.md))
- Include related GitHub Issue numbers (e.g., `#123`)

### Phase 4: Commit (inside worktree)

`git add docs/` → `git commit -m "docs: {type} - {summary}"`
→ Commands: [worktree-merge.md § Phase 4](references/worktree-merge.md)

### Phase 5: Lock → Merge → Unlock

Acquire lock → rebase → fast-forward merge → release lock. Wait up to 60s if another agent holds the lock.
On conflict/failure: always release lock, keep worktree intact.
→ Commands: [worktree-merge.md § Phase 5](references/worktree-merge.md)

### Phase 6: Cleanup

On success: remove worktree + delete branch. On failure: keep worktree for manual retry.
→ Commands: [worktree-merge.md § Phase 6](references/worktree-merge.md)

### Index Update Rules
- NNN sequence: scan directory → max sequence + 1
- progress.index.md: add new entries at **top**
- Details: [indexing-strategy.md](references/indexing-strategy.md)

## References

- [File templates](references/templates.md) — findings, progress, decision file formats
- [Indexing strategy](references/indexing-strategy.md) — index update rules, sequence collision prevention
- [Worktree merge strategy](references/worktree-merge.md) — git commands, lock mechanism, error handling
- [Workflow examples](references/examples.md) — scenario-based workflows (including parallel scenarios)
