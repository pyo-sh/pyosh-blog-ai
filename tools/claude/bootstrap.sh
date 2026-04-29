#!/usr/bin/env bash
set -euo pipefail

MODE="dry-run"
if [[ "${1:-}" == "--apply" ]]; then
  MODE="apply"
elif [[ "${1:-}" == "--dry-run" || -z "${1:-}" ]]; then
  MODE="dry-run"
else
  echo "Usage: bash tools/claude/bootstrap.sh [--dry-run|--apply]" >&2
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TEMPLATE_DIR="$ROOT_DIR/tools/claude/templates"
BACKUP_DIR="$ROOT_DIR/.workspace/backups/claude-code/$(date +%Y%m%d-%H%M%S)"

TARGETS=(
  "$ROOT_DIR:root"
  "$ROOT_DIR/client:client"
  "$ROOT_DIR/server:server"
)

copy_file() {
  local src="$1"
  local dst="$2"
  local repo_key="$3"

  if [[ -e "$dst" && "$MODE" == "apply" ]]; then
    mkdir -p "$BACKUP_DIR/$repo_key/$(dirname "${dst#$ROOT_DIR/}")"
    cp -R "$dst" "$BACKUP_DIR/$repo_key/${dst#$ROOT_DIR/}"
  fi

  if [[ "$MODE" == "apply" ]]; then
    mkdir -p "$(dirname "$dst")"
    cp "$src" "$dst"
  fi

  printf '%s %s -> %s\n' "$([[ "$MODE" == "apply" ]] && echo "APPLY" || echo "PLAN ")" "${src#$ROOT_DIR/}" "${dst#$ROOT_DIR/}"
}

copy_tree() {
  local src_dir="$1"
  local dst_dir="$2"
  local repo_key="$3"

  if [[ ! -d "$src_dir" ]]; then
    return 0
  fi

  while IFS= read -r -d '' file; do
    local rel="${file#$src_dir/}"
    copy_file "$file" "$dst_dir/$rel" "$repo_key"
  done < <(find "$src_dir" -type f -print0 | sort -z)
}

ensure_git_info_exclude() {
  local repo_root="$1"
  local entry="$2"

  if ! git -C "$repo_root" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    return 0
  fi

  local info_exclude
  info_exclude="$(git -C "$repo_root" rev-parse --git-path info/exclude)"

  if [[ ! -f "$info_exclude" ]]; then
    if [[ "$MODE" == "apply" ]]; then
      mkdir -p "$(dirname "$info_exclude")"
      touch "$info_exclude"
    fi
  fi

  if [[ -f "$info_exclude" ]] && grep -Fxq "$entry" "$info_exclude"; then
    return 0
  fi

  if [[ "$MODE" == "apply" ]]; then
    printf '\n%s\n' "$entry" >> "$info_exclude"
  fi

  printf '%s %s -> %s\n' "$([[ "$MODE" == "apply" ]] && echo "APPLY" || echo "PLAN ")" "$entry" "${info_exclude#$ROOT_DIR/}"
}

write_child_local_settings() {
  local repo_root="$1"
  local local_file="$repo_root/.claude/settings.local.json"

  # If the file already exists, do not overwrite - it may contain personal settings.
  if [[ -e "$local_file" ]]; then
    printf 'KEEP  %s (already exists, not overwriting personal settings)\n' "${local_file#$ROOT_DIR/}"
    return 0
  fi

  local content
  content="$(python3 - <<'PY' "$ROOT_DIR"
import json, os, sys
root = os.path.abspath(sys.argv[1])
print(json.dumps({
    "$schema": "https://json.schemastore.org/claude-code-settings.json",
    "claudeMdExcludes": [
        root + "/CLAUDE.md",
        root + "/.claude/rules/**",
    ],
}, indent=2))
PY
)"

  if [[ "$MODE" == "apply" ]]; then
    mkdir -p "$(dirname "$local_file")"
    printf '%s\n' "$content" > "$local_file"
  fi

  printf '%s generated local excludes -> %s\n' "$([[ "$MODE" == "apply" ]] && echo "APPLY" || echo "PLAN ")" "${local_file#$ROOT_DIR/}"
}

for item in "${TARGETS[@]}"; do
  IFS=':' read -r target repo_key <<< "$item"
  if [[ ! -d "$target" ]]; then
    echo "SKIP  missing target: ${target#$ROOT_DIR/}" >&2
    continue
  fi

  copy_file "$TEMPLATE_DIR/$repo_key/CLAUDE.md" "$target/CLAUDE.md" "$repo_key"
  copy_file "$TEMPLATE_DIR/$repo_key/.claude/settings.json" "$target/.claude/settings.json" "$repo_key"
  copy_tree "$TEMPLATE_DIR/shared/.claude/rules" "$target/.claude/rules" "$repo_key"
  copy_tree "$TEMPLATE_DIR/$repo_key/.claude/rules" "$target/.claude/rules" "$repo_key"

  ensure_git_info_exclude "$target" ".claude/settings.local.json"
  ensure_git_info_exclude "$target" "CLAUDE.local.md"

  if [[ "$repo_key" == "client" || "$repo_key" == "server" ]]; then
    write_child_local_settings "$target"
  fi
done

if [[ "$MODE" == "apply" ]]; then
  echo
  echo "Backups saved to: ${BACKUP_DIR#$ROOT_DIR/}"
  echo "Next steps:"
  echo "  1. Review diffs in root/client/server"
  echo "  2. Open Claude in each repo once and verify /memory and /permissions"
  echo "  3. Put personal preferences in CLAUDE.local.md or .claude/settings.local.json only"
else
  echo
  echo "Dry run complete. Re-run with --apply to write files."
fi
