# pyosh-blog

Personal blog monorepo — Next.js frontend + Fastify API server.

## Git Repo Structure (Important)

Each directory is an **independent Git repo**. Run `gh` commands from the corresponding directory.

| Path | GitHub Repo | Contents |
|------|------------|----------|
| `/` (root) | `pyo-sh/pyosh-blog-ai` | docs, skills, workflow config |
| `/client/` | `pyo-sh/pyosh-blog-fe` | Next.js frontend |
| `/server/` | `pyo-sh/pyosh-blog-be` | Fastify API server |

```bash
# Example: check server issues
cd /Users/pyosh/Workspace/pyosh-blog/server && gh issue list
```

## Directory Structure

```
pyosh-blog/
├── client/                      # Next.js (independent repo) → client/CLAUDE.md
├── server/                      # Fastify (independent repo) → server/CLAUDE.md
├── docs/{client,server,workspace}/ # progress/, findings/, decisions/ records
├── skills/                      # Skill sources
└── .workspace/                  # gitignored — worktrees, pipeline state
```

### docs/ Reference

When you need context about past work, technical decisions, or known issues, **read the relevant docs first**:

| Path | Contents |
|------|----------|
| `docs/{area}/progress.index.md` | Task completion timeline |
| `docs/{area}/findings.index.md` | Technical research & issue resolutions |
| `docs/{area}/decisions.index.md` | Architecture/tech decisions |

- `workspace` area covers root repo changes (tools/, Docker, tmux, skills, workflow config)
- CI/CD is recorded under the respective area (`client` or `server`), not `workspace`

## Common Dev Principles

- TypeScript Strict Mode
- pnpm package manager
- ESLint + Prettier auto-formatting
- File names in kebab-case

---

## Task Rules

Follow this order when receiving coding tasks:

1. **Check Issue** — verify with `gh issue list`, create with user approval if missing
2. **Run `/dev-build`** — create worktree → code → create PR
3. **Run `/dev-log`** — record in `docs/{area}/` when technical research/decisions occur

## Git Workflow

main + feature branches only. Never push directly to main.

```
Branch: {feat|fix|docs|refactor}/issue-{N}-{description}
Commit: {type}: {description} (#{N})
PR:     Include Closes #{N}
```

```
Check Issue → create worktree → code → push → PR → review → user approval → merge → cleanup worktree
```

## Multi-Agent

- 1 agent = 1 Issue, worktree isolation required
- Never work on Issues that modify the same files simultaneously
- Technical decisions: draft in `docs/{area}/decisions/` → proceed after user approval

## Skills

| Skill | Purpose |
|-------|---------|
| `/dev-pipeline` | Auto orchestration (build → review → resolve → merge) |
| `/dev-build` | Issue → Worktree → Code → PR workflow |
| `/dev-log` | progress / findings / decisions records |
| `/dev-review` | PR code review |
| `/dev-resolve` | Address review comments |
| `/frontend-design` | Use for UI design tasks |
