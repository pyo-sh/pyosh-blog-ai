"""Tests for controller module."""
import json
from pathlib import Path

import pytest

from dev_pipeline.controller import format_escalation, list_pipelines
from dev_pipeline.state_store import state_write


def test_format_escalation_basic(monorepo_root, sample_state, state_file):
    msg = format_escalation(42, "client", "merge", monorepo_root)
    assert "[pipeline] ESCALATION" in msg
    assert "stage merge failed" in msg
    assert "Current state:" in msg
    assert "Manual action:" in msg


def test_format_escalation_includes_step(monorepo_root, sample_state, state_file):
    msg = format_escalation(42, "client", "merge", monorepo_root)
    assert "review_dispatch" in msg  # sample_state step


def test_format_escalation_includes_pr(monorepo_root, sample_state, state_file):
    msg = format_escalation(42, "client", "merge", monorepo_root)
    assert "#129" in msg


def test_format_escalation_includes_branch(monorepo_root, sample_state, state_file):
    msg = format_escalation(42, "client", "merge", monorepo_root)
    assert "feat/issue-42" in msg


def test_format_escalation_transition_log_none(monorepo_root, sample_state, state_file):
    """Empty transition log should show 'none'."""
    msg = format_escalation(42, "client", "build", monorepo_root)
    assert "Last successful transition: none" in msg


def test_format_escalation_transition_log_entry(monorepo_root, sample_state):
    sample_state["transitionLog"] = [
        {"from": "build", "to": "review_dispatch", "reason": "ok", "ts": "2024-01-01T00:00:00Z"}
    ]
    state_write(42, "client", monorepo_root, sample_state)
    msg = format_escalation(42, "client", "merge", monorepo_root)
    assert "build -> review_dispatch" in msg


def test_format_escalation_recovery_log_for_stage(monorepo_root, sample_state):
    sample_state["recoveryLog"] = [
        {
            "stage": "merge",
            "error": "push failed",
            "action": "retry",
            "result": "failed again",
            "timestamp": "2024-01-01T00:00:00Z",
        },
        {
            "stage": "build",
            "error": "compile error",
            "action": "fix",
            "result": "resolved",
            "timestamp": "2024-01-01T00:01:00Z",
        },
    ]
    state_write(42, "client", monorepo_root, sample_state)
    msg = format_escalation(42, "client", "merge", monorepo_root)
    # Should show merge-stage recovery log
    assert "push failed" in msg
    # Should not show build-stage entry in merge escalation
    assert "compile error" not in msg


def test_format_escalation_recovery_log_none_when_no_matches(monorepo_root, sample_state, state_file):
    msg = format_escalation(42, "client", "merge", monorepo_root)
    assert "(none)" in msg


def test_format_escalation_includes_worktree(monorepo_root, sample_state, state_file):
    msg = format_escalation(42, "client", "merge", monorepo_root)
    assert "/workspace/.workspace/worktrees/client/issue-42" in msg


def test_format_escalation_missing_state(monorepo_root):
    """When state file is missing, escalation should still return a message."""
    msg = format_escalation(999, "client", "build", monorepo_root)
    assert "[pipeline] ESCALATION" in msg
    assert "Unable to read state" in msg


def test_format_escalation_manual_resume_command(monorepo_root, sample_state, state_file):
    msg = format_escalation(42, "client", "merge", monorepo_root)
    assert "/dev-pipeline client #42" in msg


def test_list_pipelines_empty(monorepo_root):
    result = list_pipelines(monorepo_root)
    assert result == []


def test_list_pipelines_no_pipeline_dir(tmp_path):
    result = list_pipelines(tmp_path)
    assert result == []


def test_list_pipelines_single(monorepo_root, sample_state):
    state_write(42, "client", monorepo_root, sample_state)
    result = list_pipelines(monorepo_root)
    assert len(result) == 1
    assert result[0]["issue"] == 42
    assert result[0]["area"] == "client"
    assert result[0]["step"] == "review_dispatch"
    assert result[0]["pr"] == 129


def test_list_pipelines_multiple(monorepo_root, sample_state):
    state_write(42, "client", monorepo_root, sample_state)
    # Add a second state
    state2 = dict(sample_state)
    state2["issue"] = 55
    state2["area"] = "server"
    state2["pr"] = 200
    state2["step"] = "merge"
    state_write(55, "server", monorepo_root, state2)
    result = list_pipelines(monorepo_root)
    assert len(result) == 2
    issues = {r["issue"] for r in result}
    assert {42, 55} == issues


def test_list_pipelines_ignores_corrupt_json(monorepo_root):
    """Corrupt JSON file should be silently skipped."""
    state_dir = monorepo_root / ".workspace" / "pipeline" / "client"
    state_dir.mkdir(parents=True, exist_ok=True)
    bad = state_dir / "issue-99.state.json"
    bad.write_text("{not valid json")
    result = list_pipelines(monorepo_root)
    assert all(r.get("issue") != 99 for r in result)
