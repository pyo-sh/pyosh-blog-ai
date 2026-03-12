from unittest.mock import patch

from dev_log.command_runner import RunResult
from dev_log.git_ops import (
    branch_exists_remote,
    commit,
    create_branch_from,
    current_branch,
    push,
    push_to_docs,
)


@patch("dev_log.git_ops.run")
def test_commit_returns_sha(mock_run):
    mock_run.side_effect = [
        RunResult(stdout="", stderr="", returncode=0),  # git commit
        RunResult(stdout="abc123\n", stderr="", returncode=0),  # git rev-parse
    ]
    sha = commit("/worktree", "docs: test")
    assert sha == "abc123"
    assert mock_run.call_count == 2


@patch("dev_log.git_ops.run")
def test_push_returns_branch(mock_run):
    mock_run.side_effect = [
        RunResult(stdout="dev-log/test\n", stderr="", returncode=0),  # rev-parse branch
        RunResult(stdout="", stderr="", returncode=0),  # git push
    ]
    branch = push("/worktree")
    assert branch == "dev-log/test"


@patch("dev_log.git_ops.run")
def test_current_branch(mock_run):
    mock_run.return_value = RunResult(stdout="main\n", stderr="", returncode=0)
    assert current_branch("/repo") == "main"


@patch("dev_log.git_ops.run")
def test_push_to_docs(mock_run):
    mock_run.return_value = RunResult(stdout="", stderr="", returncode=0)
    push_to_docs("/worktree")
    mock_run.assert_called_once_with(
        ["git", "-C", "/worktree", "push", "origin", "HEAD:docs"]
    )


@patch("dev_log.git_ops.run")
def test_branch_exists_remote_true(mock_run):
    mock_run.return_value = RunResult(
        stdout="abc123\trefs/heads/docs\n", stderr="", returncode=0
    )
    assert branch_exists_remote("/repo", "docs") is True


@patch("dev_log.git_ops.run")
def test_branch_exists_remote_false(mock_run):
    mock_run.return_value = RunResult(stdout="", stderr="", returncode=0)
    assert branch_exists_remote("/repo", "docs") is False


@patch("dev_log.git_ops.run")
def test_create_branch_from(mock_run):
    mock_run.return_value = RunResult(stdout="", stderr="", returncode=0)
    create_branch_from("/repo", "docs", "origin/main")
    mock_run.assert_called_once_with(
        ["git", "-C", "/repo", "branch", "docs", "origin/main"]
    )
