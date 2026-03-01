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
  # Set statusLine to wrapper
  .statusLine = {
    type: "command",
    command: $wrapper
  } |

  # Initialize hooks object if missing
  .hooks //= {} |

  # UserPromptSubmit → working status (append, preserve existing hooks)
  .hooks.UserPromptSubmit = (
    (.hooks.UserPromptSubmit // []) |
    if any(.[]; .matcher == "" and (.hooks | any(.command == $on_status)))
    then .
    else . + [{
      matcher: "",
      hooks: [{
        type: "command",
        command: $on_status,
        timeout: 5
      }]
    }]
    end
  ) |

  # Stop → idle status (append, preserve existing hooks)
  .hooks.Stop = (
    (.hooks.Stop // []) |
    if any(.[]; .matcher == "" and (.hooks | any(.command == $on_status)))
    then .
    else . + [{
      matcher: "",
      hooks: [{
        type: "command",
        command: $on_status,
        timeout: 5
      }]
    }]
    end
  ) |

  # PreToolUse (all tools) → activity tracking + needs-input for AskUserQuestion
  .hooks.PreToolUse = (
    (.hooks.PreToolUse // []) |
    # Remove old AskUserQuestion-only entry if present
    [.[] | select(.matcher != "AskUserQuestion" or (.hooks | any(.command == $on_status) | not))] |
    if any(.[]; .matcher == "" and (.hooks | any(.command == $on_status)))
    then .
    else . + [{
      matcher: "",
      hooks: [{
        type: "command",
        command: $on_status,
        timeout: 5
      }]
    }]
    end
  ) |

  # PostToolUse (all tools) → clear activity
  .hooks.PostToolUse = (
    (.hooks.PostToolUse // []) |
    if any(.[]; .matcher == "" and (.hooks | any(.command == $on_status)))
    then .
    else . + [{
      matcher: "",
      hooks: [{
        type: "command",
        command: $on_status,
        timeout: 5
      }]
    }]
    end
  )
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
