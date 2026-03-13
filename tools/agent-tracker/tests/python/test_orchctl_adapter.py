"""Tests for backend/adapters/orchctl_adapter.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Allow running from the agent-tracker directory or monorepo root.
_BACKEND_PARENT = Path(__file__).resolve().parent.parent.parent
if str(_BACKEND_PARENT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_PARENT))

from backend.adapters.orchctl_adapter import (
    load_exports,
    read_exports,
    read_exports_from_fixture,
)
from backend.contract import BatchStatus
from backend.models import BatchState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_export(
    area: str = "workspace",
    issues: list[dict] | None = None,
    batches: list[dict] | None = None,
    active_workers: list[dict] | None = None,
) -> dict:
    return {
        "schema_version": "v1",
        "generated_at": 1710288000.0,
        "area": area,
        "issues": issues or [],
        "batches": batches or [],
        "active_workers": active_workers or [],
        "diagnostics": [],
    }


def _write_export(tmp_path: Path, area: str, data: dict) -> Path:
    out = tmp_path / area / "current.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data))
    return out


# ---------------------------------------------------------------------------
# read_exports
# ---------------------------------------------------------------------------

class TestReadExports:
    def test_returns_empty_when_no_files(self, tmp_path):
        result = read_exports(tmp_path)
        assert result == []

    def test_returns_empty_when_dir_missing(self, tmp_path):
        result = read_exports(tmp_path / "nonexistent")
        assert result == []

    def test_reads_single_area(self, tmp_path):
        data = _make_export("workspace")
        _write_export(tmp_path, "workspace", data)
        batches = read_exports(tmp_path)
        assert len(batches) == 1
        assert batches[0].area == "workspace"

    def test_reads_multiple_areas(self, tmp_path):
        for area in ("workspace", "client", "server"):
            _write_export(tmp_path, area, _make_export(area))
        batches = read_exports(tmp_path)
        areas = {b.area for b in batches}
        assert areas == {"workspace", "client", "server"}

    def test_skips_wrong_schema_version(self, tmp_path):
        data = _make_export()
        data["schema_version"] = "v0"
        _write_export(tmp_path, "workspace", data)
        assert read_exports(tmp_path) == []

    def test_skips_invalid_json(self, tmp_path):
        bad = tmp_path / "workspace" / "current.json"
        bad.parent.mkdir()
        bad.write_text("not json")
        assert read_exports(tmp_path) == []


# ---------------------------------------------------------------------------
# Batch status derivation
# ---------------------------------------------------------------------------

class TestBatchStatus:
    def test_active_when_worker_alive(self, tmp_path):
        data = _make_export(
            issues=[{
                "number": 1, "area": "workspace", "state": "dispatched",
                "dependency_type": "none", "attempt_id": "a-1",
                "pid": 99999, "started_at": None, "liveness": "alive",
            }],
            batches=[{
                "area": "workspace", "n_total": 1, "n_done": 0,
                "n_failed": 0, "n_pending": 0, "n_dispatched": 1, "started_at": None,
            }],
            active_workers=[{
                "attempt_id": "a-1", "issue_number": 1, "area": "workspace",
                "pid": 99999, "alive": True, "started_at": None,
            }],
        )
        _write_export(tmp_path, "workspace", data)
        batch = read_exports(tmp_path)[0]
        assert batch.batch_status == BatchStatus.ACTIVE

    def test_done_when_all_terminal(self, tmp_path):
        data = _make_export(
            issues=[{
                "number": 2, "area": "workspace", "state": "completed",
                "dependency_type": "none", "attempt_id": "a-2",
                "pid": None, "started_at": None, "liveness": "dead",
            }],
            batches=[{
                "area": "workspace", "n_total": 1, "n_done": 1,
                "n_failed": 0, "n_pending": 0, "n_dispatched": 0, "started_at": None,
            }],
            active_workers=[],
        )
        _write_export(tmp_path, "workspace", data)
        batch = read_exports(tmp_path)[0]
        assert batch.batch_status == BatchStatus.DONE

    def test_dead_when_no_active_workers_and_not_done(self, tmp_path):
        data = _make_export(
            issues=[{
                "number": 3, "area": "workspace", "state": "failed-terminal",
                "dependency_type": "none", "attempt_id": "a-3",
                "pid": None, "started_at": None, "liveness": "dead",
            }],
            batches=[{
                "area": "workspace", "n_total": 2, "n_done": 0,
                "n_failed": 1, "n_pending": 1, "n_dispatched": 0, "started_at": None,
            }],
            active_workers=[],
        )
        _write_export(tmp_path, "workspace", data)
        batch = read_exports(tmp_path)[0]
        assert batch.batch_status == BatchStatus.DEAD


# ---------------------------------------------------------------------------
# Counts
# ---------------------------------------------------------------------------

class TestCounts:
    def test_counts_from_batch_summary(self, tmp_path):
        data = _make_export(
            batches=[{
                "area": "workspace", "n_total": 10, "n_done": 3,
                "n_failed": 2, "n_pending": 4, "n_dispatched": 1, "started_at": None,
            }],
        )
        _write_export(tmp_path, "workspace", data)
        batch = read_exports(tmp_path)[0]
        assert batch.n_total == 10
        assert batch.n_done == 3
        assert batch.n_failed == 2

    def test_counts_derived_from_issues_when_no_batches(self, tmp_path):
        issues = [
            {"number": 1, "area": "workspace", "state": "completed",
             "dependency_type": "none", "attempt_id": None, "pid": None,
             "started_at": None, "liveness": "unknown"},
            {"number": 2, "area": "workspace", "state": "failed-terminal",
             "dependency_type": "none", "attempt_id": None, "pid": None,
             "started_at": None, "liveness": "unknown"},
            {"number": 3, "area": "workspace", "state": "pending",
             "dependency_type": "none", "attempt_id": None, "pid": None,
             "started_at": None, "liveness": "unknown"},
        ]
        data = _make_export(issues=issues, batches=[])
        _write_export(tmp_path, "workspace", data)
        batch = read_exports(tmp_path)[0]
        assert batch.n_total == 3
        assert batch.n_done == 1
        assert batch.n_failed == 1


# ---------------------------------------------------------------------------
# Dispatched issues
# ---------------------------------------------------------------------------

class TestDispatchedIssues:
    def test_dispatched_from_active_workers(self, tmp_path):
        data = _make_export(
            issues=[{
                "number": 5, "area": "workspace", "state": "dispatched",
                "dependency_type": "none", "attempt_id": "a-5",
                "pid": 1234, "started_at": None, "liveness": "alive",
            }],
            batches=[{
                "area": "workspace", "n_total": 1, "n_done": 0,
                "n_failed": 0, "n_pending": 0, "n_dispatched": 1, "started_at": None,
            }],
            active_workers=[{
                "attempt_id": "a-5", "issue_number": 5, "area": "workspace",
                "pid": 1234, "alive": True, "started_at": None,
            }],
        )
        _write_export(tmp_path, "workspace", data)
        batch = read_exports(tmp_path)[0]
        assert len(batch.dispatched) == 1
        d = batch.dispatched[0]
        assert d.issue == "5"
        assert d.alive is True

    def test_no_dispatched_when_no_active_workers(self, tmp_path):
        data = _make_export()
        _write_export(tmp_path, "workspace", data)
        batch = read_exports(tmp_path)[0]
        assert batch.dispatched == []


# ---------------------------------------------------------------------------
# Fixture fallback
# ---------------------------------------------------------------------------

class TestFixtureFallback:
    def test_fixture_loads(self):
        batches = read_exports_from_fixture()
        assert len(batches) == 1
        b = batches[0]
        assert b.area == "workspace"
        assert b.n_total == 3

    def test_load_exports_falls_back_to_fixture_when_empty(self, tmp_path):
        batches = load_exports(tmp_path)
        # Should return fixture data (1 batch)
        assert len(batches) == 1

    def test_load_exports_prefers_real_data(self, tmp_path):
        data = _make_export(
            "server",
            batches=[{
                "area": "server", "n_total": 99, "n_done": 0,
                "n_failed": 0, "n_pending": 99, "n_dispatched": 0, "started_at": None,
            }],
        )
        _write_export(tmp_path, "server", data)
        batches = load_exports(tmp_path)
        assert len(batches) == 1
        assert batches[0].area == "server"
        assert batches[0].n_total == 99
