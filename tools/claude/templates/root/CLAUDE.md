# pyosh-blog workspace

Shared Claude Code instructions for the workspace root repository.

Personal preferences belong in `CLAUDE.local.md` or `.claude/settings.local.json`, not in this file.

## Scope

- This repository contains docs, skills, and workflow configuration.
- `client/` and `server/` are separate Git repositories with their own `CLAUDE.md`.
- For git-only commands in another repository, use `git -C <path>`. For `gh`, `pnpm`, or repo-local scripts, use `(cd "$repo" && ...)`.

## Repository map

| Path | GitHub repo | Contents |
| --- | --- | --- |
| `/` | `pyo-sh/pyosh-blog-ai` | docs, skills, workflow config |
| `/client/` | `pyo-sh/pyosh-blog-fe` | Next.js frontend |
| `/server/` | `pyo-sh/pyosh-blog-be` | Fastify API server |

## Context sources

- Area definitions, directory mappings, worktree paths, and shell helpers: `.agents/references/monorepo-layout.md`
- Before changing workflow, architecture, or repo conventions, read `docs/workspace/progress.index.md`, `docs/workspace/findings.index.md`, and `docs/workspace/decisions.index.md`.

## Behavior

- If large content is pasted with no explicit task, summarize it first.
- Keep repository facts grounded in the prompt or files you actually read.
- See `.claude/rules/` for shared bash, worktree, git, docs, and writing rules.

## Root repo workflow

- Root repo work is user-directed.
- After completing root repo work, record it in `docs/workspace/` with `/dev-log`.
