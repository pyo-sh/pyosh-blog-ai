from pathlib import Path
from unittest.mock import patch

import pytest

from dev_log.merge import acquire_lock, lock_merge, release_lock


def test_lock_acquire_release(tmp_path):
    lock_path = tmp_path / "test.lock"
    acquire_lock(lock_path)
    assert lock_path.is_dir()
    release_lock(lock_path)
    assert not lock_path.exists()


def test_lock_timeout(tmp_path):
    lock_path = tmp_path / "test.lock"
    lock_path.mkdir()  # pre-create to simulate held lock
    with pytest.raises(TimeoutError):
        acquire_lock(lock_path, timeout=1, interval=0.5)


def test_lock_release_idempotent(tmp_path):
    lock_path = tmp_path / "test.lock"
    release_lock(lock_path)  # no error on non-existent


@patch("dev_log.merge.rev_parse_head", return_value="abc123")
@patch("dev_log.merge.merge_ff_only")
@patch("dev_log.merge.rebase")
@patch("dev_log.merge.fetch")
@patch("dev_log.merge.current_branch", return_value="main")
def test_lock_merge_success(mock_branch, mock_fetch, mock_rebase, mock_merge, mock_rev, tmp_path):
    (tmp_path / ".workspace").mkdir()
    result = lock_merge("/worktree", "dev-log/test", str(tmp_path))
    assert result == {"merged": True, "sha": "abc123"}
    mock_fetch.assert_called_once()
    mock_rebase.assert_called_once_with("/worktree", "main")
    assert not (tmp_path / ".workspace" / "dev-log.lock").exists()


@patch("dev_log.merge.merge_ff_only")
@patch("dev_log.merge.rebase_abort")
@patch("dev_log.merge.rebase", side_effect=RuntimeError("conflict"))
@patch("dev_log.merge.fetch")
@patch("dev_log.merge.current_branch", return_value="main")
def test_lock_merge_rebase_abort(mock_branch, mock_fetch, mock_rebase, mock_abort, mock_merge, tmp_path):
    (tmp_path / ".workspace").mkdir()
    with pytest.raises(RuntimeError, match="conflict"):
        lock_merge("/worktree", "dev-log/test", str(tmp_path))
    mock_abort.assert_called_once_with("/worktree")
    # Lock must be released even on failure
    assert not (tmp_path / ".workspace" / "dev-log.lock").exists()


@patch("dev_log.merge.current_branch", return_value="feature/something")
def test_lock_merge_rejects_non_main(mock_branch, tmp_path):
    (tmp_path / ".workspace").mkdir()
    with pytest.raises(RuntimeError, match="expected 'main'"):
        lock_merge("/worktree", "dev-log/test", str(tmp_path))
