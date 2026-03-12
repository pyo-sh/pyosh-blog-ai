from unittest.mock import patch

from dev_log.command_runner import RunResult
from dev_log.git_ops import commit, current_branch, push


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
