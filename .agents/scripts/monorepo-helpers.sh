#!/bin/bash
# monorepo-helpers.sh — Shared monorepo root detection and area resolution.
# Source this file from any skill script. Provides MONOREPO_ROOT and helper functions.
#
# Usage:
#   source /path/to/.agents/scripts/monorepo-helpers.sh
#   # or from a skill script:
#   source "$MONOREPO_ROOT/.agents/scripts/monorepo-helpers.sh"

# ──────────────────────────────────────────────
# Root detection
# ──────────────────────────────────────────────
# Strategy: locate this script file, then resolve 2 levels up (.agents/scripts/ → root).
# This is reliable regardless of cwd or which git repo is active.

_MONOREPO_HELPERS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MONOREPO_ROOT="$(cd "$_MONOREPO_HELPERS_DIR/../.." && pwd)"

# If sourced from inside a linked worktree (.workspace/worktrees/…), lift to real root.
if [[ "$MONOREPO_ROOT" == *"/.workspace/worktrees/"* ]]; then
  MONOREPO_ROOT="${MONOREPO_ROOT%%/.workspace/worktrees/*}"
fi

# ──────────────────────────────────────────────
# Area resolution
# ──────────────────────────────────────────────

monorepo_area_dir() {
  # Usage: monorepo_area_dir <area>
  # Returns absolute path to area directory.
  local area=$1
  case "$area" in
    workspace) echo "$MONOREPO_ROOT" ;;
    client|server) echo "$MONOREPO_ROOT/$area" ;;
    *) echo "ERROR: unknown area '$area'" >&2; return 1 ;;
  esac
}

monorepo_area_repo() {
  # Usage: monorepo_area_repo <area>
  # Returns GitHub repo in owner/name format.
  local area=$1
  case "$area" in
    client) echo "pyo-sh/pyosh-blog-fe" ;;
    server) echo "pyo-sh/pyosh-blog-be" ;;
    workspace) echo "pyo-sh/pyosh-blog-ai" ;;
    *) echo "ERROR: unknown area '$area'" >&2; return 1 ;;
  esac
}

monorepo_area_from_dir() {
  # Usage: monorepo_area_from_dir <dir>
  # Returns area name given a directory path.
  # Useful for reverse-resolving: directory → area label.
  local dir=$1
  if [ "$dir" = "$MONOREPO_ROOT" ]; then
    echo "workspace"
  else
    basename "$dir"
  fi
}
