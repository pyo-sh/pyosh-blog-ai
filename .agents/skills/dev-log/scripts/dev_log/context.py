from pathlib import Path


def detect_context(cwd: str | None = None) -> dict:
    """Detect whether CWD is inside a root repo worktree."""
    path = Path(cwd) if cwd else Path.cwd()

    # Check if under .workspace/worktrees/
    for parent in path.parents:
        worktrees_dir = parent / ".workspace" / "worktrees"
        if worktrees_dir.exists() and str(path).startswith(str(worktrees_dir)):
            root_repo = parent
            branch = _get_branch(str(path))
            return {
                "inRootWorktree": True,
                "rootRepo": str(root_repo),
                "worktreePath": str(path),
                "branch": branch,
            }

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


def _get_branch(worktree: str) -> str:
    from .command_runner import run

    try:
        return run(
            ["git", "-C", worktree, "rev-parse", "--abbrev-ref", "HEAD"]
        ).stdout.strip()
    except Exception:
        return ""
