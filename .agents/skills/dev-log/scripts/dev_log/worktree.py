from datetime import datetime
from pathlib import Path

from .git_ops import (
    branch_delete,
    branch_exists_remote,
    create_branch_from,
    fetch,
    worktree_add,
    worktree_remove,
)


def ensure_docs_branch(root: str) -> dict:
    """Ensure the docs branch exists on origin, creating from origin/main if needed."""
    fetch(root, ref="main")
    if branch_exists_remote(root, "docs"):
        fetch(root, ref="docs")
        return {"created": False}
    create_branch_from(root, "docs", "origin/main")
    from .command_runner import run

    run(["git", "-C", root, "push", "origin", "docs"])
    branch_delete(root, "docs")
    return {"created": True}


def create_worktree(root: str) -> dict:
    """Create a timestamp-based worktree for dev-log."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    branch = f"dev-log/{timestamp}"
    wt_path = str(Path(root) / ".workspace" / "worktrees" / f"dev-log-{timestamp}")
    worktree_add(root, wt_path, branch, base="origin/docs")
    return {"worktreePath": wt_path, "branch": branch}


def cleanup_worktree(worktree: str, branch: str, root: str) -> dict:
    """Remove worktree and delete branch."""
    worktree_remove(root, worktree)
    branch_delete(root, branch)
    return {"removed": True}
