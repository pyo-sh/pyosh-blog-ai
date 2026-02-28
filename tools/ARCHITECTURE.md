# Development Environment Architecture

> AI agent reference for the dev environment.

## Overview

**Host Tmux → Docker (Ubuntu 24.04) → Tmux** three-layer structure. All tools run inside Docker; tmux enables parallel multi-agent workloads.

```
Host OS
  └─ tmux "blog"                    ← tmux/host.tmux.conf
       ├─ window 0: work (2 panes)
       └─ window 1: project → docker exec -it dev-lab tmux attach -t lab
            └─ Docker container (user: dev, non-root)
                 └─ tmux "lab"      ← tmux/docker.tmux.conf
                      ├─ window 0: lab (2x2 tiled, 4 panes)
                      ├─ window 1-2: server agents (4 panes each)
                      └─ window 3-4: client agents (4 panes each)
```

## Files

```
tools/
├── docker/
│   ├── Dockerfile          # Image (Node 22, pnpm, Python, gh, Claude Code native, Codex)
│   ├── docker-compose.yaml # Service definition, volume mounts
│   ├── entrypoint.sh       # Init (auth symlinks, config linking, dev-update)
│   └── .bash_aliases       # Agent aliases and helper functions
└── tmux/
    ├── host.tmux.conf / docker.tmux.conf
    ├── session.host.yml / session.docker.yml
    └── session.host.wait-and-attach.sh
```

## Container

- **Name**: `dev-lab` | **User**: `dev` (non-root — required for Claude Code `--dangerously-skip-permissions`)
- **Network**: `network_mode: host` — shares `localhost`, no port mapping needed
- **Init**: `entrypoint.sh` → auth symlinks → config symlinks → `dev-update` → tmuxinator `lab` session
- **Tool details**: see `docker/Dockerfile`

## Volumes & Symlinks

| Source         | Container Path    | Purpose                         |
| -------------- | ----------------- | ------------------------------- |
| Project root   | `/workspace`      | Source code (bind)              |
| `dev-lab-auth` | `/home/dev/.auth` | Auth credentials (named volume) |

Config files — symlinked via `/workspace` (created by `entrypoint.sh`):

```
~/.tmux.conf    → /workspace/tools/tmux/docker.tmux.conf
~/.bash_aliases → /workspace/tools/docker/.bash_aliases
```

Auth symlinks:

```
/home/dev/.auth/
  ├── gh/         ← ~/.config/gh
  ├── claude/     ← ~/.claude
  ├── claude.json ← ~/.claude.json
  ├── codex/      ← ~/.codex
  ├── gitconfig   ← ~/.gitconfig
  └── ssh/        ← ~/.ssh
```

## Environment Variables

`.env` (gitignored, managed per host):

| Variable    | Purpose                                    |
| ----------- | ------------------------------------------ |
| `TMUX_ROOT` | tmuxinator session root directory          |
| `TZ`        | Container timezone (default: `Asia/Seoul`) |

## Shell Aliases

Inside container — full details: see `docker/.bash_aliases`

| Alias | Description               |
| ----- | ------------------------- |
| `cc`  | Run Claude Code           |
| `ccc` | Continue previous session |
| `cr`  | Resume specific session   |
| `ch`  | Run with Chrome browser   |
| `cdx` | Run Codex                 |

Helpers: `dev-update` (update tools) · `dev-refresh` (reload bashrc) · `dev-auth-setup` (auth setup) · `dev-auth-status` (auth status check)
