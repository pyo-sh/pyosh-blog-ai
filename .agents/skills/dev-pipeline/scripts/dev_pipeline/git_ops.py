import sys
from typing import Optional

from .command_runner import run


def fetch(repo_dir: str, remote: str = "origin") -> bool:
    result = run(["git", "-C", repo_dir, "fetch", remote], timeout=60)
    return result.rc == 0


def rebase(worktree_dir: str, onto: str = "origin/main") -> bool:
    result = run(["git", "-C", worktree_dir, "rebase", onto], timeout=120)
    return result.rc == 0


def rebase_abort(worktree_dir: str) -> None:
    run(["git", "-C", worktree_dir, "rebase", "--abort"], timeout=30)


def merge_abort(worktree_dir: str) -> None:
    run(["git", "-C", worktree_dir, "merge", "--abort"], timeout=30)


def merge_no_edit(worktree_dir: str, ref: str = "origin/main") -> bool:
    result = run(
        ["git", "-C", worktree_dir, "merge", "--no-edit", ref], timeout=120
    )
    return result.rc == 0


def push_safely(worktree_dir: str) -> bool:
    """Push normally when fast-forward; otherwise use --force-with-lease."""
    # Check if upstream tracking ref exists
    check = run(
        ["git", "-C", worktree_dir, "rev-parse", "--verify", "@{upstream}"],
        timeout=10,
    )
    if check.rc != 0:
        result = run(
            ["git", "-C", worktree_dir, "push", "-u", "origin", "HEAD"],
            timeout=60,
        )
        return result.rc == 0

    # Check if upstream is ancestor of HEAD (fast-forward possible)
    is_ancestor = run(
        ["git", "-C", worktree_dir, "merge-base", "--is-ancestor", "@{upstream}", "HEAD"],
        timeout=10,
    )
    if is_ancestor.rc == 0:
        result = run(["git", "-C", worktree_dir, "push"], timeout=60)
    else:
        result = run(
            ["git", "-C", worktree_dir, "push", "--force-with-lease"], timeout=60
        )
    return result.rc == 0


def add_all(worktree_dir: str) -> bool:
    result = run(["git", "-C", worktree_dir, "add", "-A"], timeout=30)
    return result.rc == 0


def has_staged_changes(worktree_dir: str) -> bool:
    result = run(
        ["git", "-C", worktree_dir, "diff", "--cached", "--quiet"], timeout=10
    )
    return result.rc != 0  # rc=1 means there are differences


def commit(worktree_dir: str, message: str) -> bool:
    result = run(
        ["git", "-C", worktree_dir, "commit", "-m", message], timeout=30
    )
    return result.rc == 0


def rev_parse_head(worktree_dir: str) -> Optional[str]:
    result = run(
        ["git", "-C", worktree_dir, "rev-parse", "HEAD"], timeout=10
    )
    if result.rc != 0:
        return None
    return result.stdout.strip()


def is_clean(worktree_dir: str) -> bool:
    result = run(
        ["git", "-C", worktree_dir, "status", "--porcelain"], timeout=10
    )
    return result.rc == 0 and result.stdout.strip() == ""


def worktree_remove(repo_dir: str, worktree_dir: str, force: bool = True) -> None:
    cmd = ["git", "-C", repo_dir, "worktree", "remove", worktree_dir]
    if force:
        cmd.append("--force")
    run(cmd, timeout=30)
    run(["git", "-C", repo_dir, "worktree", "prune"], timeout=30)


def branch_delete(repo_dir: str, branch: str) -> None:
    run(["git", "-C", repo_dir, "branch", "-D", branch], timeout=10)


def fetch_prune(repo_dir: str) -> None:
    run(["git", "-C", repo_dir, "fetch", "--prune"], timeout=60)
