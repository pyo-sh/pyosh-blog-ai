"""Tests for paths module."""
from pathlib import Path

import pytest

from dev_pipeline.paths import (
    pipeline_dir,
    pipeline_err_path,
    pipeline_headless_meta_path,
    pipeline_init,
    pipeline_log_dir,
    pipeline_log_path,
    pipeline_message_path,
    pipeline_state_dir,
    pipeline_state_path,
    pipeline_worktree_path,
    resolve_worktree_path,
)


def test_pipeline_dir(tmp_path):
    assert pipeline_dir(tmp_path) == tmp_path / ".workspace" / "pipeline"


def test_pipeline_state_dir(tmp_path):
    assert pipeline_state_dir("client", tmp_path) == (
        tmp_path / ".workspace" / "pipeline" / "client"
    )


def test_pipeline_log_dir(tmp_path):
    assert pipeline_log_dir("server", tmp_path) == (
        tmp_path / ".workspace" / "pipeline" / "logs" / "server"
    )


def test_pipeline_state_path(tmp_path):
    path = pipeline_state_path(42, "client", tmp_path)
    assert path == tmp_path / ".workspace" / "pipeline" / "client" / "issue-42.state.json"
    assert path.name == "issue-42.state.json"


def test_pipeline_log_path(tmp_path):
    path = pipeline_log_path(42, "client", "review", tmp_path)
    assert path == (
        tmp_path / ".workspace" / "pipeline" / "logs" / "client" / "issue-42-review.log"
    )


def test_pipeline_err_path(tmp_path):
    path = pipeline_err_path(42, "client", "review", tmp_path)
    assert path == (
        tmp_path / ".workspace" / "pipeline" / "logs" / "client" / "issue-42-review.err"
    )


def test_pipeline_headless_meta_path(tmp_path):
    path = pipeline_headless_meta_path(42, "client", "review", tmp_path)
    assert path == (
        tmp_path / ".workspace" / "pipeline" / "client" / "issue-42-review.job.json"
    )


def test_pipeline_message_path(tmp_path):
    path = pipeline_message_path("client", 129, "review", tmp_path)
    assert path == tmp_path / ".workspace" / "messages" / "client-pr-129-review.md"


def test_pipeline_worktree_path(tmp_path):
    path = pipeline_worktree_path(42, "client", tmp_path)
    assert path == tmp_path / ".workspace" / "worktrees" / "client" / "issue-42"


def test_resolve_worktree_path_missing(tmp_path):
    result = resolve_worktree_path(42, "client", tmp_path)
    assert result is None


def test_resolve_worktree_path_exists(tmp_path):
    wt = tmp_path / ".workspace" / "worktrees" / "client" / "issue-42"
    wt.mkdir(parents=True)
    result = resolve_worktree_path(42, "client", tmp_path)
    assert result == wt


def test_pipeline_init_creates_dirs(tmp_path):
    pipeline_init("client", tmp_path)
    assert (tmp_path / ".workspace" / "pipeline" / "client").is_dir()
    assert (tmp_path / ".workspace" / "pipeline" / "logs" / "client").is_dir()
    assert (tmp_path / ".workspace" / "messages").is_dir()
    assert (tmp_path / ".workspace" / "worktrees" / "client").is_dir()


def test_pipeline_init_idempotent(tmp_path):
    pipeline_init("server", tmp_path)
    pipeline_init("server", tmp_path)  # Should not raise


def test_different_issues_different_paths(tmp_path):
    p1 = pipeline_state_path(1, "client", tmp_path)
    p2 = pipeline_state_path(2, "client", tmp_path)
    assert p1 != p2
    assert "issue-1" in p1.name
    assert "issue-2" in p2.name


def test_different_areas_different_paths(tmp_path):
    p1 = pipeline_state_path(1, "client", tmp_path)
    p2 = pipeline_state_path(1, "server", tmp_path)
    assert p1 != p2
    assert "client" in str(p1)
    assert "server" in str(p2)
