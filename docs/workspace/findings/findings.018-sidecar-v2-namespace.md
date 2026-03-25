---
title: "Agent-tracker sidecar v2 namespace design"
issue: 109
pr: 175
date: 2026-03-13
area: workspace
---

# Agent-tracker sidecar v2 namespace design

## Context

The agent-tracker push model writes a sidecar JSON file per Claude Code pane. Before v2, all sidecars lived flat in `.workspace/agent-tracker/{pane_id}.json`. This worked for a single tmux server and single session, but became ambiguous when multiple servers or sessions ran concurrently - pane IDs are not globally unique across servers.

## Findings

### Namespace structure

v2 uses a three-level path: `<socket-hash>/<session>/<pane>.json`.

- **socket-hash**: first 6 hex chars of `md5sum(socket_path)`. The socket path comes from the `$TMUX` environment variable (format: `socket_path,server_pid,session_id`). 6 chars is enough to distinguish servers in practice; full MD5 is not needed.
- **session**: tmux session name queried via `tmux display-message -p '#{session_name}'`. Human-readable and already scoped under the socket-hash.
- **pane**: numeric pane id without the `%` prefix.

Example: `.workspace/agent-tracker/a1b2c3/lab/5.json`

### Immediate cutover

No migration period. At `agent-tracker.sh` startup the flat v1 files (`SIDECAR_DIR/*.json`) are removed unconditionally. Hooks begin writing to the new namespace immediately. This avoids a reader having to check both paths on every iteration.

### Scoped cleanup

The orphan-deletion pass is scoped to the current tmux server and target session only. Files under other socket-hash directories (other servers) or other session subdirectories are never touched. This preserves sidecars written by other running agent-tracker instances.

### Source precedence

For Claude panes, the reader now documents the precedence order explicitly in `collect.sh`:
1. sidecar (push model via hooks) - most accurate, all fields available
2. pane scrape (tmux capture-pane) - fallback for status inference when sidecar absent or idle
3. session JSONL - not used for Claude; only Codex panes use session files

### md5sum portability

`md5sum` is GNU coreutils and Linux-only. macOS uses `md5 -q`. Since agent-tracker targets Linux (the workspace Docker environment), this is acceptable with a comment noting the dependency. No abstraction is needed until macOS support is required.

### Conflict with #108

PR #108 landed on main between branch creation and merge. It added:
- Path traversal guard (`pane_id` must match `^%[0-9]+$`)
- `status: "stale"` and `status: "fault"` new values
- base64 encoding for task/activity fields
- `\x1e` RS separator for `IFS`-safe field splitting

The conflict was limited to a single function signature in `_collect_claude_pane`. Resolution: keep both the v2 path parameters (`session`, `socket_hash`) and the #108 path traversal guard.
