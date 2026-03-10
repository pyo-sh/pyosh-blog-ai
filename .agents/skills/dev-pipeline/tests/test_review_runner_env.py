"""Regression tests for review_runner._dispatch_claude environment handling."""
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from dev_pipeline.command_runner import RunResult


def _make_result(rc=0, stdout="", stderr="", timed_out=False):
    return RunResult(command=[], rc=rc, stdout=stdout, stderr=stderr, timed_out=timed_out)


def test_dispatch_claude_removes_claudecode_from_env(tmp_path, monkeypatch):
    """The subprocess must receive a merged env with CLAUDECODE stripped."""
    (tmp_path / ".workspace" / "pipeline" / "client").mkdir(parents=True)
    (tmp_path / ".workspace" / "pipeline" / "logs" / "client").mkdir(parents=True)
    (tmp_path / ".workspace" / "messages").mkdir(parents=True)
    (tmp_path / ".workspace" / "worktrees" / "client").mkdir(parents=True)

    monkeypatch.setenv("CLAUDECODE", "1")
    monkeypatch.setenv("EXISTING_VAR", "keep_me")

    captured_env = {}

    def fake_run(cmd, *, cwd=None, env=None, timeout=None, capture_output=True):
        captured_env.update(env or {})
        return _make_result(rc=0, stdout="review output")

    with patch("dev_pipeline.review_runner.run", side_effect=fake_run):
        from dev_pipeline import review_runner
        review_runner._dispatch_claude(
            issue=1, area="client", pr=10, monorepo_root=tmp_path, model=""
        )

    assert "CLAUDECODE" not in captured_env, "CLAUDECODE must be stripped from subprocess env"
    assert "EXISTING_VAR" in captured_env, "Existing env vars must be preserved"
    assert captured_env.get("PIPELINE_AREA") == "client"
    assert captured_env.get("PIPELINE_ISSUE") == "1"


def test_dispatch_claude_pipeline_vars_in_env(tmp_path, monkeypatch):
    """PIPELINE_* vars must be present in the subprocess env."""
    (tmp_path / ".workspace" / "pipeline" / "client").mkdir(parents=True)
    (tmp_path / ".workspace" / "pipeline" / "logs" / "client").mkdir(parents=True)
    (tmp_path / ".workspace" / "messages").mkdir(parents=True)
    (tmp_path / ".workspace" / "worktrees" / "client").mkdir(parents=True)

    monkeypatch.delenv("CLAUDECODE", raising=False)

    captured_env = {}

    def fake_run(cmd, *, cwd=None, env=None, timeout=None, capture_output=True):
        captured_env.update(env or {})
        return _make_result(rc=0, stdout="")

    with patch("dev_pipeline.review_runner.run", side_effect=fake_run):
        from dev_pipeline import review_runner
        review_runner._dispatch_claude(
            issue=5, area="client", pr=20, monorepo_root=tmp_path, model=""
        )

    assert captured_env.get("PIPELINE_PR") == "20"
    assert captured_env.get("PIPELINE_STAGE") == "review"
    assert captured_env.get("PIPELINE_MONOREPO_ROOT") == str(tmp_path)
