# Worktree Merge Strategy

## Overview

Worktree isolation + context-aware merge to prevent conflicts when parallel agents modify `docs/` simultaneously.

Three modes based on context:

```
Standalone:        [detect] [create worktree] [write docs] [commit] [LOCK] [rebase+merge] [UNLOCK] [cleanup]
Root repo worktree:[detect] ................ [write docs] [commit] [push to PR branch] .................
```

## Constants

```bash
# Source shared monorepo helpers (→ .agents/references/monorepo-layout.md)
source "$ROOT_REPO/.agents/scripts/monorepo-helpers.sh"
ROOT_REPO="$MONOREPO_ROOT"
LOCK_FILE="$ROOT_REPO/.workspace/dev-log.lock"
LOCK_TIMEOUT=60   # seconds
LOCK_INTERVAL=5   # seconds
```

> **Note**: The AI must resolve `$ROOT_REPO` before sourcing. Use the monorepo root directory where `.agents/` lives. Do not use `git rev-parse` - this monorepo has multiple independent git repos.

## Phase 0: Detect context

Check if the current working directory is a root repo worktree under `.workspace/worktrees/`.

```bash
CWD="$(pwd)"
if [[ "$CWD" == "$ROOT_REPO/.workspace/worktrees/"* ]]; then
  IN_ROOT_WORKTREE=true
  WORKTREE_PATH="$CWD"
  BRANCH_NAME="$(git rev-parse --abbrev-ref HEAD)"
  echo "In root repo worktree: $WORKTREE_PATH (branch: $BRANCH_NAME)"
  echo "Will push docs commit to PR branch after Phase 4. Skipping Phase 1, 5, 6."
else
  IN_ROOT_WORKTREE=false
  echo "Not in root repo worktree - using full standalone flow"
fi
```

- **`IN_ROOT_WORKTREE=true`**: Use current path as `$WORKTREE_PATH`. After Phase 4, push docs commit to the existing PR branch (Phase 4.5). Skip Phase 1 (create), Phase 5 (lock merge), Phase 6 (cleanup).
- **`IN_ROOT_WORKTREE=false`**: Follow the full standalone flow below.

## Phase 1: Create worktree (skip if `IN_ROOT_WORKTREE=true`)

```bash
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
WORKTREE_PATH="$ROOT_REPO/.workspace/worktrees/dev-log-${TIMESTAMP}"
BRANCH_NAME="dev-log/${TIMESTAMP}"

cd "$ROOT_REPO"
git worktree add "$WORKTREE_PATH" -b "$BRANCH_NAME" main
```

- `.workspace/worktrees/` is in `.gitignore`
- Timestamp-based branch names guarantee uniqueness

## Phase 4: Commit

```bash
cd "$WORKTREE_PATH"
git add docs/
git commit -m "docs: {type} - {summary}"
```

- `{type}`: progress, findings, or decision
- Multiple types at once: `docs: progress + findings - {summary}`

## Phase 4.5: Push to PR branch (only if `IN_ROOT_WORKTREE=true`)

```bash
cd "$WORKTREE_PATH"
git push origin "$BRANCH_NAME"
echo "Docs commit pushed to PR branch: $BRANCH_NAME"
```

Done. The docs commit is now part of the existing PR. Skip Phase 5 and 6.

## Phase 5: Lock → Merge → Unlock (skip if `IN_ROOT_WORKTREE=true`)

### Acquire Lock

`mkdir` is atomic — only one concurrent call succeeds.

```bash
cd "$ROOT_REPO"
ELAPSED=0
while ! mkdir "$LOCK_FILE" 2>/dev/null; do
  ELAPSED=$((ELAPSED + LOCK_INTERVAL))
  if [ "$ELAPSED" -ge "$LOCK_TIMEOUT" ]; then
    echo "ERROR: Lock acquisition timed out (${LOCK_TIMEOUT}s). Another agent may be merging."
    echo "Manual check: ls -la $LOCK_FILE"
    exit 1
  fi
  echo "Waiting for lock... (${ELAPSED}/${LOCK_TIMEOUT}s)"
  sleep "$LOCK_INTERVAL"
done
echo "Lock acquired"
```

### Rebase + Merge

```bash
# Rebase worktree branch onto latest main
cd "$WORKTREE_PATH"
if ! git rebase main; then
  echo "ERROR: Rebase conflict"
  git rebase --abort
  cd "$ROOT_REPO"
  rmdir "$LOCK_FILE"  # always release lock
  echo "Lock released. Worktree preserved: $WORKTREE_PATH"
  echo "Manual resolution required"
  exit 1
fi

# Fast-forward merge
cd "$ROOT_REPO"
if ! git merge "$BRANCH_NAME" --ff-only; then
  echo "ERROR: Fast-forward merge failed"
  rmdir "$LOCK_FILE"  # always release lock
  echo "Lock released. Worktree preserved: $WORKTREE_PATH"
  exit 1
fi
```

### Release Lock

```bash
rmdir "$LOCK_FILE"
echo "Lock released. Merge successful."
```

**Important**: Always execute `rmdir "$LOCK_FILE"` when exiting Phase 5 regardless of path.

## Phase 6: Cleanup (skip if `IN_ROOT_WORKTREE=true`)

### On Success

```bash
cd "$ROOT_REPO"
git worktree remove "$WORKTREE_PATH"
git branch -d "$BRANCH_NAME"
echo "Worktree cleanup complete: $WORKTREE_PATH"
```

### On Failure

Keep worktree for manual retry:

```bash
echo "Worktree preserved: $WORKTREE_PATH"
echo "Branch: $BRANCH_NAME"
echo ""
echo "Retry steps:"
echo "  cd $WORKTREE_PATH"
echo "  git rebase main"
echo "  # resolve conflicts"
echo "  cd $ROOT_REPO"
echo "  mkdir $LOCK_FILE && git merge $BRANCH_NAME --ff-only && rmdir $LOCK_FILE"
echo "  git worktree remove $WORKTREE_PATH && git branch -d $BRANCH_NAME"
```

## Stale Lock Handling

If lock remains due to agent crash:

```bash
# Check lock directory
ls -la "$LOCK_FILE"

# After confirming no other agent is using it, manually release
rmdir "$LOCK_FILE"
```

## Implementation Notes

1. **All file paths are worktree-relative**: work in `$WORKTREE_PATH/docs/...`
2. **Use absolute paths** with Read/Write/Edit tools inside the worktree
3. **Minimize lock duration**: finish commit before acquiring lock
4. **Always release lock on error**: implement try-finally pattern
5. **Sequence numbers based on worktree creation time**: re-check after rebase if conflicts occur
