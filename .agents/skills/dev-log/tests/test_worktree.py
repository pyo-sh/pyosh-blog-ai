from unittest.mock import patch

from dev_log.worktree import cleanup_worktree, create_worktree


@patch("dev_log.worktree.worktree_add")
def test_create_worktree_naming(mock_add):
    result = create_worktree("/root")
    assert "worktreePath" in result
    assert "branch" in result
    assert result["branch"].startswith("dev-log/")
    assert ".workspace/worktrees/dev-log-" in result["worktreePath"]
    mock_add.assert_called_once()


@patch("dev_log.worktree.branch_delete")
@patch("dev_log.worktree.worktree_remove")
def test_cleanup_worktree(mock_remove, mock_delete):
    wt = "/root/.workspace/worktrees/dev-log-20260312-120000"
    result = cleanup_worktree(wt, "dev-log/20260312-120000")
    assert result == {"removed": True}
    mock_remove.assert_called_once_with("/root", wt)
    mock_delete.assert_called_once_with("/root", "dev-log/20260312-120000")
