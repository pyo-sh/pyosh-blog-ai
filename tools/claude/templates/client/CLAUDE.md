# Client - Next.js frontend

Shared Claude Code instructions for the frontend repository.

Personal preferences belong in `CLAUDE.local.md` or `.claude/settings.local.json`, not in this file.

## Purpose

Blog public pages plus admin pages. FSD - Feature-Sliced Design architecture.

## Tech stack

Next.js 14.2 - App Router
React 18.2
TypeScript 5.9
TailwindCSS 4.1
ESLint 9

## Commands

```bash
pnpm dev
pnpm build
pnpm lint
pnpm compile:types
```

## Architecture notes

- `src/app/` is for routing only.
- Import direction is `app -> widgets -> features -> entities -> shared`. Reverse dependencies are forbidden.
- Repo-specific coding rules live in `.claude/rules/`.

## Context sources

- Before changing behavior, architecture, or conventions, read `../docs/client/progress.index.md`, `../docs/client/findings.index.md`, and `../docs/client/decisions.index.md`.
- For workspace mappings and shell helpers, read `../.agents/references/monorepo-layout.md`.

## Workflow

- `/dev-pipeline` manages the full cycle for issue-driven work.
- Records go in `../docs/client/`.
