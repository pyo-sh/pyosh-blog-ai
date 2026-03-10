"""Tests for MergeLock."""
import shutil
import time
from pathlib import Path

import pytest

from dev_pipeline.merge_lock import MergeLock, MergeLockError
from dev_pipeline.paths import pipeline_state_dir


def test_acquire_and_release(monorepo_root):
    lock = MergeLock("client", 1, monorepo_root)
    lock.acquire()
    assert lock.lock_dir.is_dir()
    assert lock._acquired is True
    lock.release(expected_issue=1)
    assert not lock.lock_dir.is_dir()
    assert lock._acquired is False


def test_context_manager(monorepo_root):
    with MergeLock("client", 2, monorepo_root) as lock:
        assert lock.lock_dir.is_dir()
    assert not lock.lock_dir.is_dir()


def test_lock_dir_contains_owner_files(monorepo_root):
    lock = MergeLock("client", 5, monorepo_root)
    lock.acquire()
    assert (lock.lock_dir / "issue").read_text() == "5"
    assert (lock.lock_dir / "acquired").read_text().endswith("Z")
    lock.release()


def test_release_wrong_owner_raises(monorepo_root):
    lock = MergeLock("client", 1, monorepo_root)
    lock.acquire()
    with pytest.raises(MergeLockError, match="belongs to #1"):
        lock.release(expected_issue=99)
    # Cleanup
    lock.release()


def test_release_nonexistent_is_noop(monorepo_root):
    lock = MergeLock("client", 1, monorepo_root)
    # No acquire
    lock.release()  # Should not raise


def test_stale_lock_reclaim(monorepo_root):
    """A lock with an old timestamp should be reclaimed."""
    state_dir = pipeline_state_dir("client", monorepo_root)
    state_dir.mkdir(parents=True, exist_ok=True)
    lock_dir = state_dir / "merge.lock"
    lock_dir.mkdir()
    # Write a timestamp 2 hours ago
    old_ts = "2000-01-01T00:00:00Z"
    (lock_dir / "issue").write_text("99")
    (lock_dir / "acquired").write_text(old_ts)

    # New lock with very short stale_after to force reclaim
    lock = MergeLock("client", 7, monorepo_root, stale_after=1)
    lock.acquire()
    assert (lock.lock_dir / "issue").read_text() == "7"
    lock.release()


def test_timeout_raises(monorepo_root):
    """Lock held by another process → timeout after max_wait."""
    state_dir = pipeline_state_dir("client", monorepo_root)
    state_dir.mkdir(parents=True, exist_ok=True)
    lock_dir = state_dir / "merge.lock"
    lock_dir.mkdir()
    # Write a fresh timestamp so it's not considered stale
    from datetime import datetime, timezone
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    (lock_dir / "issue").write_text("88")
    (lock_dir / "acquired").write_text(now_iso)

    # Very short timeout with large stale_after to avoid reclaim
    lock = MergeLock("client", 7, monorepo_root, max_wait=0, stale_after=9999)
    with pytest.raises(MergeLockError, match="timeout"):
        lock.acquire()

    # Cleanup
    shutil.rmtree(lock_dir)


def test_acquire_creates_state_dir(tmp_path):
    """acquire() should create state dir if it doesn't exist."""
    lock = MergeLock("newarea", 1, tmp_path)
    lock.acquire()
    assert lock.lock_dir.is_dir()
    lock.release()


def test_context_manager_releases_on_exception(monorepo_root):
    """Lock is released even if exception is raised in body."""
    lock_ref = None
    with pytest.raises(RuntimeError):
        with MergeLock("client", 3, monorepo_root) as lock:
            lock_ref = lock
            raise RuntimeError("test error")
    assert not lock_ref.lock_dir.is_dir()
