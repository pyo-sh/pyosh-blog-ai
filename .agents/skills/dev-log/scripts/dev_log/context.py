from pathlib import Path
from typing import Optional


def detect_context(cwd: Optional[str] = None) -> dict:
    """Detect whether CWD is inside a root repo worktree."""
    path = Path(cwd) if cwd else Path.cwd()

    # Check if under .workspace/worktrees/ AND belongs to the root repo
    for parent in path.parents:
        worktrees_dir = parent / ".workspace" / "worktrees"
        if worktrees_dir.exists() and path.is_relative_to(worktrees_dir):
            root_repo = parent
            wt_root = _find_worktree_root(path, worktrees_dir)
            if wt_root and _is_root_repo_worktree(wt_root, root_repo):
                branch = _get_branch(str(wt_root))
                return {
                    "inRootWorktree": True,
                    "rootRepo": str(root_repo),
                    "worktreePath": str(wt_root),
                    "branch": branch,
                }
            break  # Under .workspace/worktrees/ but not root repo's worktree

    # Find root repo by .agents/ directory
    for candidate in [path] + list(path.parents):
        if (candidate / ".agents").is_dir():
            return {
                "inRootWorktree": False,
                "rootRepo": str(candidate),
                "worktreePath": "",
                "branch": "",
            }

    return {
        "inRootWorktree": False,
        "rootRepo": str(path),
        "worktreePath": "",
        "branch": "",
    }


def _find_worktree_root(path: Path, worktrees_dir: Path) -> Optional[Path]:
    """Walk up from *path* toward *worktrees_dir* to find the .git file."""
    current = path
    while current != worktrees_dir and current.is_relative_to(worktrees_dir):
        if (current / ".git").is_file():
            return current
        current = current.parent
    return None


def _is_root_repo_worktree(worktree: Path, root_repo: Path) -> bool:
    """Check if the worktree's git repo is the root repo.

    Git worktrees have a .git *file* (not directory) containing
    ``gitdir: <path>`` pointing into the parent repo's .git/worktrees/.
    For a root repo worktree this resolves under ``<root_repo>/.git/``.
    """
    git_file = worktree / ".git"
    if not git_file.is_file():
        return False
    try:
        content = git_file.read_text().strip()
    except OSError:
        return False
    if not content.startswith("gitdir: "):
        return False
    gitdir = Path(content[len("gitdir: "):])
    if not gitdir.is_absolute():
        gitdir = (git_file.parent / gitdir).resolve()
    else:
        gitdir = gitdir.resolve()
    root_git = (root_repo / ".git").resolve()
    return gitdir == root_git or str(gitdir).startswith(str(root_git) + "/")


def _get_branch(worktree: str) -> str:
    from .command_runner import run

    try:
        return run(
            ["git", "-C", worktree, "rev-parse", "--abbrev-ref", "HEAD"]
        ).stdout.strip()
    except Exception:
        return ""
