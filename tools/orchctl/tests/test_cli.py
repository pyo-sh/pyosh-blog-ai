"""Tests for CLI commands."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from orchctl.cli import cli


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def db_path(tmp_path: Path) -> str:
    return str(tmp_path / "test.db")


def test_help(runner):
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "orchctl" in result.output


def test_init(runner, db_path):
    result = runner.invoke(cli, ["--db", db_path, "init"])
    assert result.exit_code == 0, result.output
    assert "initialized" in result.output


def test_status_empty(runner, db_path):
    runner.invoke(cli, ["--db", db_path, "init"])
    result = runner.invoke(cli, ["--db", db_path, "status"])
    assert result.exit_code == 0, result.output
    assert "Active attempts: 0" in result.output


def test_status_json_empty(runner, db_path):
    import json

    runner.invoke(cli, ["--db", db_path, "init"])
    result = runner.invoke(cli, ["--db", db_path, "status", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert "issues" in data
    assert "active_attempts" in data
    assert data["active_attempts"] == []


def test_doctor_healthy(runner, db_path):
    runner.invoke(cli, ["--db", db_path, "init"])
    result = runner.invoke(cli, ["--db", db_path, "doctor"])
    assert result.exit_code == 0, result.output
    assert "OK" in result.output


def test_doctor_json_healthy(runner, db_path):
    import json

    runner.invoke(cli, ["--db", db_path, "init"])
    result = runner.invoke(cli, ["--db", db_path, "doctor", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["healthy"] is True
    assert data["findings"] == []


def test_reconcile_requires_area(runner, db_path):
    runner.invoke(cli, ["--db", db_path, "init"])
    result = runner.invoke(cli, ["--db", db_path, "reconcile"])
    assert result.exit_code != 0


def test_reconcile_no_pending_issues(runner, db_path):
    runner.invoke(cli, ["--db", db_path, "init"])
    result = runner.invoke(cli, ["--db", db_path, "reconcile", "--area", "client"])
    assert result.exit_code == 0, result.output
    assert "no pending issues" in result.output


def test_reconcile_skips_when_lease_held(runner, db_path):
    from orchctl.db.connection import get_db

    runner.invoke(cli, ["--db", db_path, "init"])
    conn = get_db(db_path)
    # Use PID 1 (init) — guaranteed alive so cleanup_stale won't evict it
    conn.execute(
        "INSERT INTO leases (area, holder_pid, acquired_at, heartbeat_at, expires_at) "
        "VALUES ('client', 1, datetime('now'), datetime('now'), datetime('now', '+1 hour'))"
    )
    conn.commit()
    conn.close()

    result = runner.invoke(cli, ["--db", db_path, "reconcile", "--area", "client"])
    assert result.exit_code == 0, result.output
    assert "lease held by another process" in result.output


def test_reconcile_dispatches_pending_issues(runner, db_path):
    from orchctl.db.connection import get_db

    runner.invoke(cli, ["--db", db_path, "init"])
    conn = get_db(db_path)
    conn.execute("INSERT INTO issues (area, number, state) VALUES ('client', 10, 'pending')")
    conn.commit()
    conn.close()

    result = runner.invoke(cli, ["--db", db_path, "reconcile", "--area", "client"])
    assert result.exit_code == 0, result.output
    assert "issue #10 ready to dispatch" in result.output


def test_reconcile_skips_issue_with_active_attempt(runner, db_path):
    from orchctl.db.connection import get_db

    runner.invoke(cli, ["--db", db_path, "init"])
    conn = get_db(db_path)
    conn.execute("INSERT INTO issues (area, number, state) VALUES ('client', 20, 'pending')")
    conn.commit()
    issue_id = conn.execute(
        "SELECT id FROM issues WHERE area='client' AND number=20"
    ).fetchone()["id"]
    conn.execute(
        "INSERT INTO attempts (attempt_id, issue_id, status) VALUES ('a-active', ?, 'running')",
        (issue_id,),
    )
    conn.commit()
    conn.close()

    result = runner.invoke(cli, ["--db", db_path, "reconcile", "--area", "client"])
    assert result.exit_code == 0, result.output
    assert "already has an active attempt" in result.output


def test_reconcile_aborts_on_lost_lease(runner, db_path):
    """If the lease is revoked between acquire and renew, _run_pass should abort."""
    from unittest.mock import patch
    from orchctl.db.connection import get_db

    runner.invoke(cli, ["--db", db_path, "init"])
    conn = get_db(db_path)
    conn.execute("INSERT INTO issues (area, number, state) VALUES ('client', 30, 'pending')")
    conn.commit()
    conn.close()

    with patch("orchctl.commands.reconcile.renew", return_value=False):
        result = runner.invoke(cli, ["--db", db_path, "reconcile", "--area", "client"])

    assert result.exit_code == 0
    assert "lease lost mid-pass" in result.output


def test_reconcile_requires_init(runner, db_path):
    result = runner.invoke(cli, ["--db", db_path, "reconcile", "--area", "client"])
    assert result.exit_code != 0
    assert "not initialised" in result.output


def test_reconcile_rejects_outdated_schema(runner, db_path):
    from orchctl.db.connection import get_db

    runner.invoke(cli, ["--db", db_path, "init"])
    conn = get_db(db_path)
    # Backdate schema_version to simulate a pre-migration database
    conn.execute("UPDATE schema_version SET version = 1")
    conn.commit()
    conn.close()

    result = runner.invoke(cli, ["--db", db_path, "reconcile", "--area", "client"])
    assert result.exit_code != 0
    assert "out of date" in result.output


def test_status_requires_init(runner, db_path):
    result = runner.invoke(cli, ["--db", db_path, "status"])
    assert result.exit_code != 0
    assert "not initialised" in result.output


def test_doctor_requires_init(runner, db_path):
    result = runner.invoke(cli, ["--db", db_path, "doctor"])
    assert result.exit_code != 0
    assert "not initialised" in result.output


def test_doctor_detects_stale_lease(runner, db_path):
    import json
    from orchctl.db.connection import get_db

    runner.invoke(cli, ["--db", db_path, "init"])
    conn = get_db(db_path)
    conn.execute(
        "INSERT INTO leases (area, holder_pid, acquired_at, expires_at) VALUES (?, ?, ?, ?)",
        ("client", 9999, "2020-01-01T00:00:00", "2020-01-01T00:01:00"),
    )
    conn.commit()
    conn.close()

    result = runner.invoke(cli, ["--db", db_path, "doctor", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["healthy"] is False
    stale = next(f for f in data["findings"] if f["type"] == "stale_leases")
    assert stale["count"] == 1


def test_doctor_detects_orphan_attempt(runner, db_path):
    import json
    from orchctl.db.connection import get_db

    runner.invoke(cli, ["--db", db_path, "init"])
    conn = get_db(db_path)
    # Insert attempt referencing a non-existent issue_id (FK off for raw insert)
    conn.execute("PRAGMA foreign_keys=OFF")
    conn.execute(
        "INSERT INTO attempts (attempt_id, issue_id, status) VALUES (?, ?, ?)",
        ("orphan-1", 9999, "running"),
    )
    conn.commit()
    conn.close()

    result = runner.invoke(cli, ["--db", db_path, "doctor", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["healthy"] is False
    orphans = next(f for f in data["findings"] if f["type"] == "orphan_attempts")
    assert orphans["count"] == 1
    assert "orphan-1" in orphans["ids"]
