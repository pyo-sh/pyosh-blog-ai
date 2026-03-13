"""Tests for orchctl export command and contract validation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from orchctl.cli import cli
from orchctl.contract import (
    EXPORT_SCHEMA_VERSION,
    ExportValidationError,
    validate_export,
)


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def db_path(tmp_path: Path) -> str:
    return str(tmp_path / "test.db")


def _init_db(runner, db_path):
    result = runner.invoke(cli, ["--db", db_path, "init"])
    assert result.exit_code == 0, result.output


# ---------------------------------------------------------------------------
# Contract / validate_export tests
# ---------------------------------------------------------------------------

class TestValidateExport:
    def _valid(self) -> dict:
        return {
            "schema_version": "v1",
            "generated_at": 1710288000.0,
            "area": "workspace",
            "issues": [],
            "batches": [],
            "active_workers": [],
            "diagnostics": [],
        }

    def test_valid_empty(self):
        validate_export(self._valid())  # should not raise

    def test_missing_top_level_fields(self):
        data = self._valid()
        del data["area"]
        del data["issues"]
        with pytest.raises(ExportValidationError, match="missing top-level fields"):
            validate_export(data)

    def test_wrong_schema_version(self):
        data = self._valid()
        data["schema_version"] = "v0"
        with pytest.raises(ExportValidationError, match="schema_version"):
            validate_export(data)

    def test_empty_area(self):
        data = self._valid()
        data["area"] = ""
        with pytest.raises(ExportValidationError, match="area"):
            validate_export(data)

    def test_generated_at_not_number(self):
        data = self._valid()
        data["generated_at"] = "2024-01-01"
        with pytest.raises(ExportValidationError, match="generated_at"):
            validate_export(data)

    def test_issue_missing_fields(self):
        data = self._valid()
        data["issues"] = [{"number": 1}]
        with pytest.raises(ExportValidationError, match="issues\\[0\\] missing fields"):
            validate_export(data)

    def test_issue_invalid_liveness(self):
        data = self._valid()
        data["issues"] = [{
            "number": 1,
            "area": "workspace",
            "state": "dispatched",
            "dependency_type": "none",
            "attempt_id": "a-123",
            "pid": 999,
            "started_at": "2024-01-01T00:00:00Z",
            "liveness": "maybe",
        }]
        with pytest.raises(ExportValidationError, match="liveness"):
            validate_export(data)

    def test_batch_missing_fields(self):
        data = self._valid()
        data["batches"] = [{"area": "workspace"}]
        with pytest.raises(ExportValidationError, match="batches\\[0\\] missing fields"):
            validate_export(data)

    def test_worker_missing_fields(self):
        data = self._valid()
        data["active_workers"] = [{"attempt_id": "a-1"}]
        with pytest.raises(ExportValidationError, match="active_workers\\[0\\] missing fields"):
            validate_export(data)

    def test_extra_fields_allowed(self):
        data = self._valid()
        data["future_field"] = "value"
        validate_export(data)  # should not raise


# ---------------------------------------------------------------------------
# cmd_export CLI tests
# ---------------------------------------------------------------------------

class TestCmdExport:
    def test_export_requires_area(self, runner, db_path):
        _init_db(runner, db_path)
        result = runner.invoke(cli, ["--db", db_path, "export"])
        assert result.exit_code != 0

    def test_export_requires_init(self, runner, db_path):
        result = runner.invoke(cli, ["--db", db_path, "export", "--area", "workspace"])
        assert result.exit_code != 0
        assert "not initialised" in result.output

    def test_export_empty_area(self, runner, db_path, tmp_path):
        _init_db(runner, db_path)
        out = tmp_path / "current.json"
        result = runner.invoke(
            cli,
            ["--db", db_path, "export", "--area", "workspace", "--output", str(out)],
        )
        assert result.exit_code == 0, result.output
        assert out.exists()
        data = json.loads(out.read_text())
        assert data["schema_version"] == EXPORT_SCHEMA_VERSION
        assert data["area"] == "workspace"
        assert data["issues"] == []
        assert data["batches"] == []
        assert data["active_workers"] == []

    def test_export_with_issues(self, runner, db_path, tmp_path):
        from orchctl.db.connection import get_db

        _init_db(runner, db_path)
        conn = get_db(db_path)
        conn.execute(
            "INSERT INTO issues (area, number, state) VALUES ('workspace', 10, 'pending')"
        )
        conn.execute(
            "INSERT INTO issues (area, number, state) VALUES ('workspace', 11, 'completed')"
        )
        conn.commit()
        conn.close()

        out = tmp_path / "current.json"
        result = runner.invoke(
            cli,
            ["--db", db_path, "export", "--area", "workspace", "--output", str(out)],
        )
        assert result.exit_code == 0, result.output
        data = json.loads(out.read_text())

        assert len(data["issues"]) == 2
        numbers = {i["number"] for i in data["issues"]}
        assert numbers == {10, 11}

        assert len(data["batches"]) == 1
        batch = data["batches"][0]
        assert batch["n_total"] == 2
        assert batch["n_done"] == 1
        assert batch["n_pending"] == 1
        assert batch["started_at"] is not None  # earliest issue created_at

    def test_export_active_worker_for_dispatched(self, runner, db_path, tmp_path):
        from orchctl.db.connection import get_db

        _init_db(runner, db_path)
        conn = get_db(db_path)
        conn.execute(
            "INSERT INTO issues (area, number, state) VALUES ('workspace', 20, 'dispatched')"
        )
        issue_id = conn.execute(
            "SELECT id FROM issues WHERE area='workspace' AND number=20"
        ).fetchone()["id"]
        conn.execute(
            "INSERT INTO attempts (attempt_id, issue_id, pid, status) VALUES (?, ?, ?, 'running')",
            ("a-test-20", issue_id, 99999),
        )
        conn.commit()
        conn.close()

        out = tmp_path / "current.json"
        result = runner.invoke(
            cli,
            ["--db", db_path, "export", "--area", "workspace", "--output", str(out)],
        )
        assert result.exit_code == 0, result.output
        data = json.loads(out.read_text())

        assert len(data["active_workers"]) == 1
        w = data["active_workers"][0]
        assert w["attempt_id"] == "a-test-20"
        assert w["issue_number"] == 20
        assert w["pid"] == 99999

    def test_export_print_flag(self, runner, db_path, tmp_path):
        _init_db(runner, db_path)
        out = tmp_path / "current.json"
        result = runner.invoke(
            cli,
            ["--db", db_path, "export", "--area", "workspace", "--output", str(out),
             "--print"],
        )
        assert result.exit_code == 0, result.output
        # Both the confirmation line and the JSON should be in output
        assert "export [workspace]:" in result.output
        assert '"schema_version"' in result.output

    def test_export_only_exports_requested_area(self, runner, db_path, tmp_path):
        from orchctl.db.connection import get_db

        _init_db(runner, db_path)
        conn = get_db(db_path)
        conn.execute(
            "INSERT INTO issues (area, number, state) VALUES ('workspace', 30, 'pending')"
        )
        conn.execute(
            "INSERT INTO issues (area, number, state) VALUES ('client', 31, 'pending')"
        )
        conn.commit()
        conn.close()

        out = tmp_path / "current.json"
        result = runner.invoke(
            cli,
            ["--db", db_path, "export", "--area", "workspace", "--output", str(out)],
        )
        assert result.exit_code == 0, result.output
        data = json.loads(out.read_text())
        assert all(i["area"] == "workspace" for i in data["issues"])
        assert len(data["issues"]) == 1

    def test_export_creates_parent_dirs(self, runner, db_path, tmp_path):
        _init_db(runner, db_path)
        out = tmp_path / "deep" / "nested" / "current.json"
        result = runner.invoke(
            cli,
            ["--db", db_path, "export", "--area", "workspace", "--output", str(out)],
        )
        assert result.exit_code == 0, result.output
        assert out.exists()

    def test_export_rejects_outdated_schema(self, runner, db_path, tmp_path):
        from orchctl.db.connection import get_db

        _init_db(runner, db_path)
        conn = get_db(db_path)
        conn.execute("UPDATE schema_version SET version = 1")
        conn.commit()
        conn.close()

        out = tmp_path / "current.json"
        result = runner.invoke(
            cli,
            ["--db", db_path, "export", "--area", "workspace", "--output", str(out)],
        )
        assert result.exit_code != 0
        assert "out of date" in result.output
