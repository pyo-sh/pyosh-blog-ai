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

### client / server (Issue-driven)

`/dev-pipeline`이 전체 사이클을 관리: build → review → resolve → merge.
브랜치/커밋/PR/워크트리 규칙은 스킬 내장.

### root repo (사용자 지시 기반)

사용자가 지시한 작업을 수행한다. 경중에 따라 Issue를 작성할 수도 있다.
작업 완료 후 `/dev-log`로 `docs/workspace/`에 기록.

```
worktree 생성 → 작업 → 사용자 선택 (로컬 merge 또는 PR) → /dev-log
```

- Worktree: `.workspace/worktrees/{type}-{description}`
- Branch: `{type}/{description}`
- Commit: `{type}: {description}`

## Git Rules

- main + feature branches only. Never push directly to main.
- All work must go through a worktree (`.workspace/worktrees/`).
- Multi-agent: 1 agent = 1 task, worktree isolation. 같은 파일을 동시에 수정하지 않는다.

## Skills

| Skill | Purpose |
|-------|---------|
| `/dev-pipeline` | Full cycle: build → review → resolve → merge (client/server) |
| `/dev-build` | Issue → Worktree → Code → PR (client/server) |
| `/dev-log` | progress / findings / decisions records |
| `/dev-review` | PR code review |
| `/dev-resolve` | Address review comments |
| `/frontend-design` | UI design tasks |
