from datetime import datetime
from pathlib import Path

from .git_ops import branch_delete, worktree_add, worktree_remove


def create_worktree(root: str) -> dict:
    """Create a timestamp-based worktree for dev-log."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    branch = f"dev-log/{timestamp}"
    wt_path = str(Path(root) / ".workspace" / "worktrees" / f"dev-log-{timestamp}")
    worktree_add(root, wt_path, branch)
    return {"worktreePath": wt_path, "branch": branch}


def cleanup_worktree(worktree: str, branch: str) -> dict:
    """Remove worktree and delete branch."""
    wt = Path(worktree)
    # .workspace/worktrees/dev-log-TIMESTAMP -> root is 3 levels up
    root = str(wt.parent.parent.parent)
    worktree_remove(root, worktree)
    branch_delete(root, branch)
    return {"removed": True}
