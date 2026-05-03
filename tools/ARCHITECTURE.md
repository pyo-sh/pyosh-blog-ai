# Development Environment Architecture

This document describes the current root-repo development environment. It is scoped to `pyosh-blog-ai`; `client/` and `server/` are independent application repositories that live beside it in the same workspace.

## System Overview

```text
Host OS
  └─ Docker container: dev-lab (Ubuntu 24.04, user: dev)
       ├─ /workspace              bind mount of pyosh-blog workspace
       ├─ /home/dev/.auth         named volume for tool auth/config
       └─ tmux session: lab
            ├─ window 0: lab      2 panes
            ├─ window 1: server1  2 panes
            └─ window 2: client1  2 panes
```

The root repo provides shared context and automation. Source edits for product code happen in the independent `client` and `server` repos, usually through issue worktrees under `.workspace/worktrees/{area}/issue-{N}`.

## Repository Boundaries

| Area | Path | Git repo | GitHub repo |
|------|------|----------|-------------|
| `workspace` | `/workspace` | independent | `pyo-sh/pyosh-blog-ai` |
| `client` | `/workspace/client` | independent | `pyo-sh/pyosh-blog-fe` |
| `server` | `/workspace/server` | independent | `pyo-sh/pyosh-blog-be` |

The root repo ignores `client/` and `server/`. Do not run `git`, `gh`, or `pnpm` for child repos from the root directory unless the command explicitly scopes itself to that repo.

## Root Components

```text
/workspace
├── AGENTS.md                  agent rules shared with Codex
├── CLAUDE.md                  root Claude Code context
├── .agents/
│   ├── references/            monorepo area and worktree definitions
│   ├── scripts/               shell helpers
│   └── skills/                workflow and support skills
├── .claude/                   deployed root Claude settings and shared rules
├── docs/                      area-scoped progress, findings, decisions
├── scripts/context-bar.sh     Claude Code statusLine command
├── tools/
│   ├── claude/                settings templates and bootstrap
│   ├── docker/                dev-lab image, compose, entrypoint, aliases
│   └── tmux/                  host/container tmux configs and sessions
└── .workspace/                ignored runtime state, worktrees, pipeline logs
```

## Runtime Flow

```text
User request
  └─ Claude/Codex session in /workspace
       ├─ reads AGENTS.md / CLAUDE.md / .claude/rules
       ├─ invokes .agents/skills as needed
       ├─ creates area worktrees under .workspace/worktrees/
       ├─ runs git/gh/pnpm in the correct area repo
       ├─ opens PRs in client/server/workspace repos
       └─ records progress through dev-log on the docs branch
```

`dev-pipeline` coordinates a single issue lifecycle: build, review, resolve, merge, cleanup, and log. Review can run headlessly, but there is no batch orchestrator layer in the current runtime architecture.

## Docker Layer

`tools/docker/docker-compose.yaml` builds and runs the `dev-lab` container.

| Concern | Implementation |
|---------|----------------|
| Base image | Ubuntu 24.04 |
| User | `dev` non-root user |
| Network | `network_mode: host` |
| Workspace | `../../` mounted at `/workspace` |
| Auth/config | `dev-lab-auth` named volume mounted at `/home/dev/.auth` |
| Startup | `entrypoint.sh` symlinks auth/config, runs `dev-update`, starts tmuxinator |
| Core tools | Git, gh, Node.js 22, pnpm, Python, tmux, tmuxinator, Claude Code, Codex |

The container uses directory bind mounts plus symlinks rather than single-file bind mounts for shell and tmux config. This avoids stale inode problems when editors replace files.

## Auth And Config Volume

`/home/dev/.auth` persists across container recreation.

```text
/home/dev/.auth/
├── gh/            -> ~/.config/gh
├── claude/        -> ~/.claude
├── claude.json    -> ~/.claude.json
├── codex/         -> ~/.codex
├── gitconfig      -> ~/.gitconfig
└── ssh/           -> ~/.ssh
```

`entrypoint.sh` also ensures Claude Code has this status line:

```json
{
  "statusLine": {
    "type": "command",
    "command": "/workspace/scripts/context-bar.sh"
  }
}
```

No Claude hook is required for the current root workflow.

## Claude Configuration Layer

`tools/claude/templates/` is the source of truth for repo-level Claude files.

```text
tools/claude/
├── bootstrap.sh
├── templates/root/
├── templates/client/
├── templates/server/
└── templates/shared/.claude/rules/
```

`bootstrap.sh --apply` copies the appropriate `CLAUDE.md`, `.claude/settings.json`, and shared rules into each repo. `client` and `server` get local excludes so parent workspace context is not duplicated.

## Skills Layer

The active workflow skills live under `.agents/skills/`.

| Group | Skills |
|-------|--------|
| Issue workflow | `dev-build`, `dev-review`, `dev-resolve`, `dev-pipeline`, `dev-codex-pipeline` |
| Docs workflow | `dev-log`, `dev-archive`, `dev-issue` |
| Support | `gh-cli`, `handoff`, `skill-creator` |
| Design/system helpers | `tailwind-design-system`, Supanova-related skills |

Shared path and repo definitions live in `.agents/references/monorepo-layout.md`. Shell integrations should source `.agents/scripts/monorepo-helpers.sh` instead of duplicating area logic.

## Docs Layer

`docs/` stores area-scoped records.

| Path | Contents |
|------|----------|
| `docs/client/` | client progress, findings, decisions, specs |
| `docs/server/` | server progress, findings, decisions, specs |
| `docs/workspace/` | root repo, tooling, workflow records |

`dev-log` writes to the long-lived `docs` branch. `dev-archive` later creates a PR to squash accumulated docs changes into `main`.

## Tmux Layer

The host can run an outer `blog` session, then attach to the inner Docker `lab` session.

```text
blog
├─ lab        2 panes (first pane attaches to dev-lab:lab)
├─ server1    2 panes
└─ client1    2 panes

lab
├─ lab        2 panes
├─ server1    2 panes
└─ client1    2 panes
```

tmux is a convenience for parallel sessions. Pipeline execution does not depend on tmux panes.

## Runtime State

`.workspace/` is ignored and transient.

| Path | Purpose |
|------|---------|
| `.workspace/worktrees/{area}/issue-{N}` | issue worktrees |
| `.workspace/pipeline/{area}/` | pipeline state |
| `.workspace/dev-review/` | review artifacts |
| `.workspace/messages/` | generated PR/comment bodies |

Historical subdirectories may remain after tool removals. They should not be used as active source definitions.

## Retired Components

The following runtime components have been removed from the active architecture:

- `dev-orchestrator`
- `tools/orchctl`
- `tools/agent-tracker`
- Claude hook based tracker integration
- Figma MCP configuration under `.mcp.json` and `mcp/figma-*`

Historical notes remain under `docs/` and Git history.
