#!/usr/bin/env bash
# monorepo-helpers.fixed.sh
# Shared monorepo root detection and area resolution.

_MONOREPO_HELPERS_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
MONOREPO_ROOT="$(cd -- "$_MONOREPO_HELPERS_DIR/../.." && pwd -P)"

# If sourced from inside a linked worktree (.workspace/worktrees/…), lift to real root.
case "$MONOREPO_ROOT" in
  */.workspace/worktrees/*)
    MONOREPO_ROOT="${MONOREPO_ROOT%%/.workspace/worktrees/*}"
    ;;
esac

monorepo_area_dir() {
  # Usage: monorepo_area_dir <area>
  # Returns absolute path to the canonical checkout directory for the area.
  local area=$1
  case "$area" in
    workspace) printf '%s\n' "$MONOREPO_ROOT" ;;
    client|server) printf '%s\n' "$MONOREPO_ROOT/$area" ;;
    *) printf "ERROR: unknown area '%s'\n" "$area" >&2; return 1 ;;
  esac
}

monorepo_area_repo() {
  # Usage: monorepo_area_repo <area>
  # Returns GitHub repo in owner/name format.
  local area=$1
  case "$area" in
    client) printf '%s\n' 'pyo-sh/pyosh-blog-fe' ;;
    server) printf '%s\n' 'pyo-sh/pyosh-blog-be' ;;
    workspace) printf '%s\n' 'pyo-sh/pyosh-blog-ai' ;;
    *) printf "ERROR: unknown area '%s'\n" "$area" >&2; return 1 ;;
  esac
}

monorepo_worktree_root() {
  printf '%s\n' "$MONOREPO_ROOT/.workspace/worktrees"
}

monorepo_area_from_dir() {
  # Usage: monorepo_area_from_dir <dir>
  # Resolves the area from an exact area directory, any subdirectory under it,
  # or an area-scoped worktree path (.workspace/worktrees/<area>/...).
  local input=$1
  local dir

  dir="$(cd -- "$input" 2>/dev/null && pwd -P)" || {
    printf "ERROR: cannot resolve path '%s'\n" "$input" >&2
    return 1
  }

  case "$dir" in
    "$MONOREPO_ROOT")
      printf '%s\n' 'workspace'
      ;;
    "$MONOREPO_ROOT/client"|"$MONOREPO_ROOT/client"/*|"$MONOREPO_ROOT/.workspace/worktrees/client"|"$MONOREPO_ROOT/.workspace/worktrees/client"/*)
      printf '%s\n' 'client'
      ;;
    "$MONOREPO_ROOT/server"|"$MONOREPO_ROOT/server"/*|"$MONOREPO_ROOT/.workspace/worktrees/server"|"$MONOREPO_ROOT/.workspace/worktrees/server"/*)
      printf '%s\n' 'server'
      ;;
    *)
      printf "ERROR: cannot determine area from '%s'\n" "$input" >&2
      return 1
      ;;
  esac
}
