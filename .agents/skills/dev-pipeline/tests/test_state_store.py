"""Tests for state_store module."""
import json
from pathlib import Path

import pytest

from dev_pipeline.state_store import (
    log_transition,
    recovery_log_append,
    stage_retry,
    state_delete,
    state_exists,
    state_read,
    state_update,
    state_write,
)


def test_state_exists_false(monorepo_root):
    assert state_exists(99, "client", monorepo_root) is False


def test_state_write_and_read(monorepo_root, sample_state):
    state_write(1, "client", monorepo_root, sample_state)
    assert state_exists(1, "client", monorepo_root) is True
    data = state_read(1, "client", monorepo_root)
    assert data["issue"] == 42
    assert data["area"] == "client"


def test_state_write_creates_parent_dirs(tmp_path):
    # No pre-existing pipeline dir
    data = {"issue": 7, "area": "server", "step": "build"}
    state_write(7, "server", tmp_path, data)
    path = tmp_path / ".workspace" / "pipeline" / "server" / "issue-7.state.json"
    assert path.exists()
    assert json.loads(path.read_text())["issue"] == 7


def test_state_write_atomic(monorepo_root, sample_state):
    """Written file must be valid JSON (no partial writes)."""
    state_write(1, "client", monorepo_root, sample_state)
    raw = (
        monorepo_root / ".workspace" / "pipeline" / "client" / "issue-1.state.json"
    ).read_text()
    parsed = json.loads(raw)
    assert isinstance(parsed, dict)


def test_state_write_ends_with_newline(monorepo_root, sample_state):
    state_write(1, "client", monorepo_root, sample_state)
    raw = (
        monorepo_root / ".workspace" / "pipeline" / "client" / "issue-1.state.json"
    ).read_text()
    assert raw.endswith("\n")


def test_state_update_shallow_merge(monorepo_root, sample_state):
    state_write(42, "client", monorepo_root, sample_state)
    state_update(42, "client", monorepo_root, {"step": "merge", "pr": 200})
    data = state_read(42, "client", monorepo_root)
    assert data["step"] == "merge"
    assert data["pr"] == 200
    # Original keys preserved
    assert data["issue"] == 42


def test_state_update_deep_merge_nested_dict(monorepo_root, sample_state):
    state_write(42, "client", monorepo_root, sample_state)
    state_update(42, "client", monorepo_root, {"reviewJob": {"status": "running"}})
    data = state_read(42, "client", monorepo_root)
    # Other reviewJob fields should be preserved
    assert data["reviewJob"]["status"] == "running"
    assert "runId" in data["reviewJob"]


def test_state_update_sets_updated_at(monorepo_root, sample_state):
    state_write(42, "client", monorepo_root, sample_state)
    state_update(42, "client", monorepo_root, {"step": "merge"})
    data = state_read(42, "client", monorepo_root)
    assert data.get("updatedAt") is not None


def test_state_delete(monorepo_root, sample_state):
    state_write(42, "client", monorepo_root, sample_state)
    assert state_exists(42, "client", monorepo_root)
    state_delete(42, "client", monorepo_root)
    assert not state_exists(42, "client", monorepo_root)


def test_state_delete_nonexistent_is_noop(monorepo_root):
    # Should not raise
    state_delete(999, "client", monorepo_root)


def test_log_transition_appends_entry(monorepo_root, sample_state):
    state_write(42, "client", monorepo_root, sample_state)
    log_transition(42, "client", monorepo_root, "build", "review_dispatch", "build passed")
    data = state_read(42, "client", monorepo_root)
    assert len(data["transitionLog"]) == 1
    entry = data["transitionLog"][0]
    assert entry["from"] == "build"
    assert entry["to"] == "review_dispatch"
    assert entry["reason"] == "build passed"
    assert "ts" in entry


def test_log_transition_nonfatal_on_missing_state(monorepo_root):
    # Should not raise even if state file doesn't exist
    log_transition(999, "client", monorepo_root, "build", "review_dispatch")


def test_recovery_log_append(monorepo_root, sample_state):
    state_write(42, "client", monorepo_root, sample_state)
    recovery_log_append(42, "client", monorepo_root, "merge", "push failed", "retry", "ok")
    data = state_read(42, "client", monorepo_root)
    assert len(data["recoveryLog"]) == 1
    entry = data["recoveryLog"][0]
    assert entry["stage"] == "merge"
    assert entry["error"] == "push failed"
    assert entry["action"] == "retry"
    assert entry["result"] == "ok"


def test_stage_retry_increments(monorepo_root, sample_state):
    state_write(42, "client", monorepo_root, sample_state)
    assert stage_retry(42, "client", monorepo_root, "build") is True
    data = state_read(42, "client", monorepo_root)
    assert data["stageRetries"]["build"] == 1


def test_stage_retry_returns_false_at_max(monorepo_root, sample_state):
    # Set retries to max
    sample_state["stageRetries"]["build"] = 3
    state_write(42, "client", monorepo_root, sample_state)
    result = stage_retry(42, "client", monorepo_root, "build")
    assert result is False


def test_stage_retry_allows_up_to_max(monorepo_root, sample_state):
    state_write(42, "client", monorepo_root, sample_state)
    for _ in range(3):
        assert stage_retry(42, "client", monorepo_root, "review_dispatch") is True
    assert stage_retry(42, "client", monorepo_root, "review_dispatch") is False
