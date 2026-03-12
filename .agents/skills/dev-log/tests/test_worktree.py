from unittest.mock import patch, call

from dev_log.worktree import cleanup_worktree, create_worktree, ensure_docs_branch


@patch("dev_log.worktree.worktree_add")
def test_create_worktree_naming(mock_add):
    result = create_worktree("/root")
    assert "worktreePath" in result
    assert "branch" in result
    assert result["branch"].startswith("dev-log/")
    assert ".workspace/worktrees/dev-log-" in result["worktreePath"]
    mock_add.assert_called_once()


@patch("dev_log.worktree.worktree_add")
def test_create_worktree_uses_docs_base(mock_add):
    create_worktree("/root")
    args, kwargs = mock_add.call_args
    assert kwargs.get("base", args[3] if len(args) > 3 else None) == "docs"


@patch("dev_log.worktree.branch_delete")
@patch("dev_log.worktree.worktree_remove")
def test_cleanup_worktree(mock_remove, mock_delete):
    wt = "/root/.workspace/worktrees/dev-log-20260312-120000"
    result = cleanup_worktree(wt, "dev-log/20260312-120000", "/root")
    assert result == {"removed": True}
    mock_remove.assert_called_once_with("/root", wt)
    mock_delete.assert_called_once_with("/root", "dev-log/20260312-120000")


@patch("dev_log.worktree.branch_exists_remote", return_value=True)
@patch("dev_log.worktree.fetch")
def test_ensure_docs_branch_exists(mock_fetch, mock_exists):
    result = ensure_docs_branch("/root")
    assert result == {"created": False}
    assert mock_fetch.call_count == 2
    mock_fetch.assert_any_call("/root", ref="main")
    mock_fetch.assert_any_call("/root", ref="docs")


@patch("dev_log.worktree.branch_delete")
@patch("dev_log.command_runner.run")
@patch("dev_log.worktree.create_branch_from")
@patch("dev_log.worktree.branch_exists_remote", return_value=False)
@patch("dev_log.worktree.fetch")
def test_ensure_docs_branch_creates(mock_fetch, mock_exists, mock_create, mock_run, mock_bd):
    result = ensure_docs_branch("/root")
    assert result == {"created": True}
    mock_create.assert_called_once_with("/root", "docs", "origin/main")
    mock_run.assert_called_once_with(["git", "-C", "/root", "push", "origin", "docs"])
    mock_bd.assert_called_once_with("/root", "docs")
