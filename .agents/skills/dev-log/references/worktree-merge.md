# Worktree Merge Strategy

## Overview

Worktree isolation + lock-based merge to prevent conflicts when parallel agents modify `docs/` simultaneously.

```
Agent A: [create worktree] [write docs] [commit] [LOCK] [rebase+merge] [UNLOCK] [cleanup]
Agent B: [create worktree] [write docs] [commit] ......[LOCK] [rebase+merge] [UNLOCK] [cleanup]
                                                        ↑ wait
```

## Constants

```bash
# Detect monorepo root — if inside area repo (server/client), go up one level
_GIT_ROOT="$(git rev-parse --show-toplevel)"
if [ -d "$_GIT_ROOT/../server" ] && [ -f "$_GIT_ROOT/../CLAUDE.md" ]; then
  ROOT_REPO="$(cd "$_GIT_ROOT/.." && pwd)"
else
  ROOT_REPO="$_GIT_ROOT"
fi
LOCK_FILE="$ROOT_REPO/.workspace/dev-log.lock"
LOCK_TIMEOUT=60   # seconds
LOCK_INTERVAL=5   # seconds
```

## Phase 1: Create Worktree

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

## Phase 5: Lock → Merge → Unlock

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

## Phase 6: Cleanup

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
