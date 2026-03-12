---
name: dev-log
description: Manage progress/, findings/, and decisions/ records in the pyosh-blog monorepo. Use when (1) recording progress after task completion, (2) documenting technical research as findings, (3) writing architecture/tech decisions, (4) user requests "/dev-log", "record this", "write progress", etc. Parallel-agent safe (worktree isolation + lock merge).
---

# Dev-log

Record-only skill. Task management via GitHub Issues, global rules in `CLAUDE.md`.

> CLI: `cd .agents/skills/dev-log/scripts && python3 -m dev_log <cmd>`
> Area definitions: [monorepo-layout.md](../../references/monorepo-layout.md) | Templates: [templates.md](references/templates.md)

## Area selection

| Area | When to use |
|------|-------------|
| `client` | Next.js frontend changes |
| `server` | Fastify API server changes |
| `workspace` | Root repo (tools, docs, skills, CLAUDE.md), Docker/tmux config |

## Workflow

### Phase 0: Detect context

`python3 -m dev_log detect-context [--cwd "$WT"]`

- `inRootWorktree: true` - skip Phase 1, 5, 6. Push to PR branch after Phase 4.
- `inRootWorktree: false` - full standalone flow (Phase 1-6).

### Phase 1: Create worktree (skip if in worktree)

`python3 -m dev_log create-worktree --root "$ROOT_REPO"` - returns `worktreePath`, `branch`.

### Phase 2: Check context

Read `progress.index.md` + `findings.index.md` + `decisions.index.md` inside worktree. Selectively read relevant sub-files only.

### Phase 3: Write records (inside worktree)

`python3 -m dev_log next-seq --dir "$DOCS_DIR/findings" --type findings`
`python3 -m dev_log check-progress --dir "$DOCS_DIR"`

- **Findings**: create `findings/findings.NNN-topic.md` + update `findings.index.md`
- **Decision**: create `decisions/decision-NNN-topic.md` (draft) + update `decisions.index.md`
- **Progress**: create/update `progress/progress.YYYY-MM-DD.md` + update `progress.index.md`
- Include related GitHub Issue numbers

### Phase 4: Commit

`python3 -m dev_log commit --worktree "$WT" --message "docs: {type} - {summary}"`

### Phase 4.5: Push to PR branch (only if in worktree)

`python3 -m dev_log push --worktree "$WT"` - done, skip Phase 5/6.

### Phase 5: Lock merge (skip if in worktree)

`python3 -m dev_log lock-merge --worktree "$WT" --branch "$BRANCH" --root "$ROOT_REPO"`

Acquires lock, fetches, rebases, fast-forward merges, releases lock. Lock always released on failure.

### Phase 6: Cleanup (skip if in worktree)

`python3 -m dev_log cleanup --worktree "$WT" --branch "$BRANCH" --root "$ROOT_REPO"`

## Index update rules

- NNN sequence: `next-seq` scans directory, returns max+1
- `progress.index.md`: add new entries at **top**
- `findings.index.md` / `decisions.index.md`: maintain sorted order by sequence
