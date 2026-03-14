# pyosh-blog monorepo

## Repos

| Area | Path | GitHub repo |
|------|------|-------------|
| workspace | `/` | `pyo-sh/pyosh-blog-ai` |
| client | `/client/` | `pyo-sh/pyosh-blog-fe` |
| server | `/server/` | `pyo-sh/pyosh-blog-be` |

Each area is an independent Git repo. Scope all `git`/`gh`/`pnpm` commands to the correct area directory.

## Constraints

NEVER:
- Push to `main` by any method
- Run `git push --force`
- Run git/gh/pnpm for client or server from the monorepo root
- Modify `.agents/`, `.claude/`, `AGENTS.md`, or `CLAUDE.md` unless the task explicitly targets those files
- Execute `rm -rf` or equivalent without dry-run inspection first
- Create a branch from a dirty working tree

## Commands

| Area | Verify (run before push) | Dev |
|------|--------------------------|-----|
| client | `(cd client && pnpm compile:types && pnpm lint && pnpm build)` | `(cd client && pnpm dev)` |
| server | `(cd server && pnpm test)` | `(cd server && pnpm dev)` |

Shell helpers: `source .agents/scripts/monorepo-helpers.sh`
Exports: `MONOREPO_ROOT`, `monorepo_area_dir <area>`, `monorepo_area_repo <area>`

## Git protocol

- Branch: `{type}/{description}` — `{type}` ∈ `feat|fix|docs|chore|refactor`
- Commit: `{type}: {description}`
- Before merge: pull `origin/main`; one branch per task

## Worktrees

Path: `.workspace/worktrees/{area}/issue-{N}`

After commit: open a PR unless explicitly instructed to merge locally.

## Pre-task

Before modifying architecture or conventions: read `docs/{area}/decisions.index.md`.
Do not proceed if the decisions file contradicts the planned approach — report the conflict.

## Shell rules

Use a script (not an inline command) when: changing git state, chaining stateful actions, or requiring 3+ env vars.
Use `mktemp` + `trap` for temp files. Inspect targets before destructive actions; use `--dry-run` when available.

## Failure

On unrecoverable error: halt, leave working tree clean (`git stash` or revert), report the failure and last successful state.
