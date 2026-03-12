import time
from pathlib import Path

from .git_ops import fetch, push_to_docs, rebase, rebase_abort, rev_parse_head

LOCK_TIMEOUT = 60  # seconds
LOCK_INTERVAL = 5  # seconds


def acquire_lock(
    lock_path: Path, timeout: int = LOCK_TIMEOUT, interval: int = LOCK_INTERVAL
) -> None:
    deadline = time.monotonic() + timeout
    while True:
        try:
            lock_path.mkdir(parents=True, exist_ok=False)
            return
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise TimeoutError(
                    f"Could not acquire lock {lock_path} within {timeout}s"
                )
            time.sleep(interval)


def release_lock(lock_path: Path) -> None:
    try:
        lock_path.rmdir()
    except OSError:
        pass


def merge_to_docs(worktree: str, branch: str, root: str) -> dict:
    """Acquire lock, fetch+rebase onto origin/docs, push to docs branch."""
    root_path = Path(root)
    lock_path = root_path / ".workspace" / "dev-log.lock"

    acquire_lock(lock_path)
    try:
        fetch(root, ref="docs")

        try:
            rebase(worktree, "origin/docs")
        except Exception:
            rebase_abort(worktree)
            raise

        push_to_docs(worktree)
        sha = rev_parse_head(worktree)
        return {"merged": True, "sha": sha}
    finally:
        release_lock(lock_path)
