#!/usr/bin/env bash
# tools/agent-tracker/setup.sh
# Auto-configure Claude Code settings for agent-tracker hooks.
#
# What it does:
#   1. Backs up ~/.claude/settings.json
#   2. Sets statusLine to use statusline-wrapper.sh (wraps existing context-bar.sh)
#   3. Adds hooks for UserPromptSubmit, Stop, PreToolUse, PostToolUse
#
# Usage:
#   bash tools/agent-tracker/setup.sh           # interactive
#   bash tools/agent-tracker/setup.sh --yes     # non-interactive

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SETTINGS_FILE="${HOME}/.claude/settings.json"
BACKUP_FILE="${SETTINGS_FILE}.bak.$(date +%Y%m%d%H%M%S)"

AUTO_YES=false
[[ "${1:-}" == "--yes" ]] && AUTO_YES=true

# Check dependencies
if ! command -v jq >/dev/null; then
  printf 'Error: jq is required but not installed.\n' >&2
  printf 'Install: apt install jq / brew install jq\n' >&2
  exit 1
fi

# ─────────────────────────────────────────────────────────────────────────────
# Resolve absolute paths for hooks
# ─────────────────────────────────────────────────────────────────────────────
WRAPPER_PATH="${SCRIPT_DIR}/statusline-wrapper.sh"
ON_STATUS_PATH="${SCRIPT_DIR}/hooks/on-status.sh"

if [[ ! -f "$WRAPPER_PATH" ]]; then
  printf 'Error: %s not found\n' "$WRAPPER_PATH" >&2
  exit 1
fi

# ─────────────────────────────────────────────────────────────────────────────
# Confirm
# ─────────────────────────────────────────────────────────────────────────────
if [[ "$AUTO_YES" != true ]]; then
  printf 'This will modify: %s\n' "$SETTINGS_FILE"
  printf 'Changes:\n'
  printf '  - statusLine → %s\n' "$WRAPPER_PATH"
  printf '  - hooks.UserPromptSubmit → %s\n' "$ON_STATUS_PATH"
  printf '  - hooks.Stop → %s\n' "$ON_STATUS_PATH"
  printf '  - hooks.PreToolUse (all tools) → %s\n' "$ON_STATUS_PATH"
  printf '  - hooks.PostToolUse (all tools) → %s\n' "$ON_STATUS_PATH"
  printf '\nProceed? [y/N] '
  read -r answer
  [[ "$answer" != [yY]* ]] && { printf 'Aborted.\n'; exit 0; }
fi

# ─────────────────────────────────────────────────────────────────────────────
# Ensure settings directory exists
# ─────────────────────────────────────────────────────────────────────────────
mkdir -p "$(dirname "$SETTINGS_FILE")"

# ─────────────────────────────────────────────────────────────────────────────
# Backup existing settings
# ─────────────────────────────────────────────────────────────────────────────
if [[ -f "$SETTINGS_FILE" ]]; then
  cp "$SETTINGS_FILE" "$BACKUP_FILE"
  printf 'Backed up to: %s\n' "$BACKUP_FILE"
  existing=$(cat "$SETTINGS_FILE")
else
  existing='{}'
  printf 'No existing settings.json, creating new.\n'
fi

# ─────────────────────────────────────────────────────────────────────────────
# Make scripts executable
# ─────────────────────────────────────────────────────────────────────────────
chmod +x "$WRAPPER_PATH"
chmod +x "$ON_STATUS_PATH"
chmod +x "${SCRIPT_DIR}/hooks/on-statusline.sh"

# ─────────────────────────────────────────────────────────────────────────────
# Merge settings
# ─────────────────────────────────────────────────────────────────────────────
updated=$(printf '%s' "$existing" | jq \
  --arg wrapper "$WRAPPER_PATH" \
  --arg on_status "$ON_STATUS_PATH" \
  '
  # Helper: check if hook entry has our command (guards non-object/non-array)
  def has_cmd: if type != "object" then false else .hooks | if type == "array" then any(.command == $on_status) else false end end;

  # Helper: append tracker hook to event array if not present
  def ensure_hook(matcher):
    if any(.[]; type == "object" and .matcher == matcher and has_cmd)
    then .
    else . + [{
      matcher: matcher,
      hooks: [{
        type: "command",
        command: $on_status,
        timeout: 5
      }]
    }]
    end;

  # Set statusLine to wrapper
  .statusLine = {
    type: "command",
    command: $wrapper
  } |

  # Normalize: .hooks must be object, each event must be array
  .hooks |= (if type == "object" then . else {} end) |
  .hooks.UserPromptSubmit |= (if type == "array" then . else [] end) |
  .hooks.Stop |= (if type == "array" then . else [] end) |
  .hooks.PreToolUse |= (if type == "array" then . else [] end) |
  .hooks.PostToolUse |= (if type == "array" then . else [] end) |

  # UserPromptSubmit → working status (append, preserve existing hooks)
  .hooks.UserPromptSubmit |= ensure_hook("") |

  # Stop → idle status (append, preserve existing hooks)
  .hooks.Stop |= ensure_hook("") |

  # PreToolUse (all tools) → activity tracking + needs-input for AskUserQuestion
  .hooks.PreToolUse |= (
    # Remove old AskUserQuestion-only entry if present
    [.[] | select(type != "object" or .matcher != "AskUserQuestion" or (has_cmd | not))] |
    ensure_hook("")
  ) |

  # PostToolUse (all tools) → clear activity
  .hooks.PostToolUse |= ensure_hook("")
')

# ─────────────────────────────────────────────────────────────────────────────
# Write updated settings
# ─────────────────────────────────────────────────────────────────────────────
printf '%s\n' "$updated" > "$SETTINGS_FILE"

printf '\nSettings updated successfully.\n'
printf 'Restart Claude Code sessions for hooks to take effect.\n'

# ─────────────────────────────────────────────────────────────────────────────
# Create sidecar directory
# ─────────────────────────────────────────────────────────────────────────────
mkdir -p /tmp/agent-tracker
printf 'Sidecar directory: /tmp/agent-tracker/\n'

printf '\nDone.\n'
