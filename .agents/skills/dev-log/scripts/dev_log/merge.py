import time
from pathlib import Path

from .git_ops import current_branch, fetch, merge_ff_only, rebase, rebase_abort, rev_parse_head

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


def lock_merge(worktree: str, branch: str, root: str) -> dict:
    """Acquire lock, fetch+rebase, ff-merge to main, release lock."""
    root_path = Path(root)
    lock_path = root_path / ".workspace" / "dev-log.lock"

    branch_head = current_branch(root)
    if branch_head != "main":
        raise RuntimeError(
            f"Root repo HEAD is '{branch_head}', expected 'main'"
        )

    acquire_lock(lock_path)
    try:
        fetch(root, ref="main")
        merge_ff_only(root, "origin/main")

        try:
            rebase(worktree, "main")
        except Exception:
            rebase_abort(worktree)
            raise

        merge_ff_only(root, branch)
        sha = rev_parse_head(root)
        return {"merged": True, "sha": sha}
    finally:
        release_lock(lock_path)
