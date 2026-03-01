# agent-tracker

Real-time tmux dashboard for monitoring Claude Code and Codex agents.

## Architecture

### Push model (Claude Code)

Claude Code pushes data via hooks and statusLine. No `/proc` scanning or JSONL parsing needed.

```
Claude Code session
  ├─ statusLine (every ~300ms)
  │    └─ statusline-wrapper.sh
  │         ├─ hooks/on-statusline.sh  → writes /tmp/agent-tracker/{pane}.json
  │         └─ scripts/context-bar.sh  → status bar display (unchanged)
  │
  └─ hooks (on events)
       └─ hooks/on-status.sh
            ├─ UserPromptSubmit → status: working, task: prompt text, clear activity
            ├─ Stop             → status: idle, clear activity
            ├─ PreToolUse       → activity: "{ToolName}: {key_arg}"
            │                     + status: needs-input (AskUserQuestion only)
            └─ PostToolUse      → clear activity

agent-tracker.sh (dashboard)
  └─ reads /tmp/agent-tracker/*.json → renders table
```

### Pull model (Codex fallback)

Codex has no hooks support. The dashboard falls back to pane scraping and session JSONL parsing.

## Files

```
tools/agent-tracker/
├── README.md              # this file
├── hooks/
│   ├── on-statusline.sh   # StatusLine → sidecar write (session, model, tokens, cwd)
│   └── on-status.sh       # Event hooks → sidecar status update (working/idle/needs-input)
├── statusline-wrapper.sh  # Wraps context-bar.sh + triggers on-statusline.sh
├── agent-tracker.sh       # Dashboard (reads sidecar files)
└── setup.sh               # Auto-configure ~/.claude/settings.json
```

## Sidecar format

Location: `/tmp/agent-tracker/{pane_id}.json` (pane_id without `%` prefix)

```json
{
  "pane_id": "%1",
  "session_id": "9ce2db1d-...",
  "model": "Opus 4.6",
  "status": "working",
  "tokens": { "used": 62000, "max": 200000, "pct": 31 },
  "task": "implement hooks for agent-tracker",
  "activity": "Edit: on-status.sh",
  "cwd": "/workspace",
  "transcript_path": "/home/dev/.claude/projects/-workspace/9ce2db1d.jsonl",
  "updated_at": 1772376267
}
```

## Setup

### Automatic

```bash
bash tools/agent-tracker/setup.sh
```

This backs up `~/.claude/settings.json` and adds the required configuration.

### Manual

Add to `~/.claude/settings.json`:

```json
{
  "statusLine": {
    "type": "command",
    "command": "/workspace/tools/agent-tracker/statusline-wrapper.sh"
  },
  "hooks": {
    "UserPromptSubmit": [{
      "matcher": "",
      "hooks": [{
        "type": "command",
        "command": "/workspace/tools/agent-tracker/hooks/on-status.sh",
        "timeout": 5
      }]
    }],
    "Stop": [{
      "matcher": "",
      "hooks": [{
        "type": "command",
        "command": "/workspace/tools/agent-tracker/hooks/on-status.sh",
        "timeout": 5
      }]
    }],
    "PreToolUse": [{
      "matcher": "",
      "hooks": [{
        "type": "command",
        "command": "/workspace/tools/agent-tracker/hooks/on-status.sh",
        "timeout": 5
      }]
    }],
    "PostToolUse": [{
      "matcher": "",
      "hooks": [{
        "type": "command",
        "command": "/workspace/tools/agent-tracker/hooks/on-status.sh",
        "timeout": 5
      }]
    }]
  }
}
```

Restart Claude Code sessions after changing settings.

## Usage

```bash
bash tools/agent-tracker/agent-tracker.sh [-s SESSION] [-i INTERVAL]
```

- `-s SESSION` - tmux session name (default: `lab`)
- `-i INTERVAL` - refresh interval in seconds (default: `1`)

## Host vs Docker

- **Host**: only `statusLine` is needed (context-bar.sh). Hooks are optional since `/proc` access works.
- **Docker**: both `statusLine` (via wrapper) and `hooks` are needed. `/proc/PID/fd` scanning fails because Claude doesn't keep JSONL files open.

## Previous approach (deprecated)

The previous `scripts/agent-tracker.sh` used:
1. `/proc/PID/fd` scanning to map panes to transcript files
2. Direct JSONL parsing for model, tokens, and task data
3. Pane scraping as fallback

This failed in multi-agent setups where multiple Claude instances shared the same project directory - the fd scan always failed and the fallback returned the same JSONL for all panes.
