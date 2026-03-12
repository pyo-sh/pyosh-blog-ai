---
name: dev-log
description: Manage progress/, findings/, and decisions/ records in the pyosh-blog monorepo. Commits go to a long-lived docs branch (not main). Use when (1) recording progress after task completion, (2) documenting technical research as findings, (3) writing architecture/tech decisions, (4) user requests "/dev-log", "record this", "write progress", etc. Parallel-agent safe (worktree isolation + lock merge).
---

# Dev-log

Record-only skill. All commits target the `docs` branch. Merge to `main` via `/dev-archive`.

> CLI: `cd .agents/skills/dev-log/scripts && python3 -m dev_log <cmd>`
> Area definitions: [monorepo-layout.md](../../references/monorepo-layout.md) | Templates: [templates.md](references/templates.md)

## Area selection

| Area | When to use |
|------|-------------|
| `client` | Next.js frontend changes |
| `server` | Fastify API server changes |
| `workspace` | Root repo (tools, docs, skills, CLAUDE.md), Docker/tmux config |

## Workflow

### Phase 1: Ensure docs branch

`python3 -m dev_log ensure-branch --root "$ROOT_REPO"` - creates `docs` from `origin/main` if not exists.

### Phase 2: Create worktree

`python3 -m dev_log create-worktree --root "$ROOT_REPO"` - returns `worktreePath`, `branch`. Worktree branches from `docs`.

### Phase 3: Check context

Read `progress.index.md` + `findings.index.md` + `decisions.index.md` inside worktree. Selectively read relevant sub-files only.

### Phase 4: Write records (inside worktree)

`python3 -m dev_log next-seq --dir "$DOCS_DIR/findings" --type findings`
`python3 -m dev_log next-seq --dir "$DOCS_DIR/decisions" --type decision`
`python3 -m dev_log check-progress --dir "$DOCS_DIR"`

- **Findings**: create `findings/findings.NNN-topic.md` + update `findings.index.md`
- **Decision**: create `decisions/decision-NNN-topic.md` (draft) + update `decisions.index.md`
- **Progress**: create/update `progress/progress.YYYY-MM-DD.md` + update `progress.index.md`
- Include related GitHub Issue numbers

### Phase 5: Commit

`python3 -m dev_log commit --worktree "$WT" --message "docs: {type} - {summary}"`

### Phase 6: Merge to docs

`python3 -m dev_log merge-to-docs --worktree "$WT" --branch "$BRANCH" --root "$ROOT_REPO"`

Acquires lock, fetches `origin/docs`, rebases, pushes to `origin docs`, releases lock. Lock always released on failure.

### Phase 7: Cleanup

`python3 -m dev_log cleanup --worktree "$WT" --branch "$BRANCH" --root "$ROOT_REPO"`

## Index update rules

- NNN sequence: `next-seq` scans directory, returns max+1
- `progress.index.md`: add new entries at **top**
- `findings.index.md` / `decisions.index.md`: maintain sorted order by sequence
