# Monorepo Layout

Single source of truth for the pyosh-blog monorepo structure. All skills reference this file instead of defining their own area logic.

## Areas

| Area | Directory | GitHub Repo | Git Repo |
|------|-----------|-------------|----------|
| `client` | `{root}/client/` | `pyo-sh/pyosh-blog-fe` | Independent |
| `server` | `{root}/server/` | `pyo-sh/pyosh-blog-be` | Independent |
| `workspace` | `{root}/` | `pyo-sh/pyosh-blog-ai` | Independent |

- `{root}` = monorepo root (the directory containing `.agents/`, `client/`, `server/`, `docs/`)
- Each area is an **independent Git repo**. `cd {area_dir}` before running `git` or `gh` commands.
- `workspace` area dir is the monorepo root itself.

## Area detection hints

| Signal | Area |
|--------|------|
| tmux window name starts with `client` | `client` |
| tmux window name starts with `server` | `server` |
| Issue label `client` or `server` | Matching area |
| Root repo issue (pyosh-blog-ai) | `workspace` |
| Otherwise | Ask user |

## Worktree paths

```
{root}/.workspace/worktrees/{area}/issue-{N}
```

- Worktrees live under the **monorepo root** `.workspace/`, not inside the area directory.
- Area-scoped to avoid issue number collisions between `client` and `server`.

## Area-specific verify commands

| Area | Test | Build |
|------|------|-------|
| `client` | N/A | `pnpm compile:types && pnpm lint && pnpm build` |
| `server` | `pnpm test` | `pnpm dev` |
| `workspace` | N/A | N/A |

## docs/ paths

| Area | Records |
|------|---------|
| `client` | `docs/client/` |
| `server` | `docs/server/` |
| `workspace` | `docs/workspace/` |

## Shell helpers

For shell scripts, `source .agents/scripts/monorepo-helpers.sh` provides:

- `MONOREPO_ROOT` - absolute path to monorepo root
- `monorepo_area_dir <area>` - returns absolute path to area directory
- `monorepo_area_repo <area>` - returns GitHub repo (`owner/name`)
