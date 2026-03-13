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


# ---------------------------------------------------------------------------
# Admission control tests
# ---------------------------------------------------------------------------

def test_reconcile_max_concurrent_blocks_dispatch(runner, db_path):
    """No new dispatches when active dispatched count equals maxConcurrent."""
    from orchctl.db.connection import get_db

    runner.invoke(cli, ["--db", db_path, "init"])
    conn = get_db(db_path)
    # Set maxConcurrent to 1
    conn.execute("UPDATE config SET value = '1' WHERE key = 'max_concurrent'")
    # Insert one already-dispatched issue to saturate the limit
    conn.execute("INSERT INTO issues (area, number, state) VALUES ('client', 1, 'dispatched')")
    # Insert a pending issue that should be blocked
    conn.execute("INSERT INTO issues (area, number, state) VALUES ('client', 2, 'pending')")
    conn.commit()
    conn.close()

    result = runner.invoke(cli, ["--db", db_path, "reconcile", "--area", "client"])
    assert result.exit_code == 0, result.output
    assert "maxConcurrent=1 reached" in result.output


def test_reconcile_max_open_pr_blocks_dispatch(runner, db_path):
    """No new dispatches when global dispatched count equals maxOpenPR."""
    from orchctl.db.connection import get_db

    runner.invoke(cli, ["--db", db_path, "init"])
    conn = get_db(db_path)
    # Set maxOpenPR to 1 (global limit)
    conn.execute("UPDATE config SET value = '1' WHERE key = 'max_open_pr'")
    # Dispatched issue in a *different* area to trigger the global limit
    conn.execute("INSERT INTO issues (area, number, state) VALUES ('server', 5, 'dispatched')")
    # Pending issue in client area
    conn.execute("INSERT INTO issues (area, number, state) VALUES ('client', 6, 'pending')")
    conn.commit()
    conn.close()

    result = runner.invoke(cli, ["--db", db_path, "reconcile", "--area", "client"])
    assert result.exit_code == 0, result.output
    assert "maxOpenPR=1 reached" in result.output


def test_reconcile_drain_mode_blocks_dispatch(runner, db_path):
    """No new dispatches when drain mode is active."""
    from orchctl.db.connection import get_db

    runner.invoke(cli, ["--db", db_path, "init"])
    conn = get_db(db_path)
    conn.execute("UPDATE config SET value = 'true' WHERE key = 'drain_mode'")
    conn.execute("INSERT INTO issues (area, number, state) VALUES ('client', 7, 'pending')")
    conn.commit()
    conn.close()

    result = runner.invoke(cli, ["--db", db_path, "reconcile", "--area", "client"])
    assert result.exit_code == 0, result.output
    assert "drain mode active" in result.output
    assert "ready to dispatch" not in result.output


def test_reconcile_drain_mode_does_not_block_mark_complete(runner, db_path):
    """drain mode only stops new dispatches; completing existing work is allowed."""
    from orchctl.db.connection import get_db

    runner.invoke(cli, ["--db", db_path, "init"])
    conn = get_db(db_path)
    conn.execute("UPDATE config SET value = 'true' WHERE key = 'drain_mode'")
    conn.execute("INSERT INTO issues (area, number, state) VALUES ('client', 8, 'dispatched')")
    issue_id = conn.execute(
        "SELECT id FROM issues WHERE area='client' AND number=8"
    ).fetchone()["id"]
    conn.execute(
        "INSERT INTO attempts (attempt_id, issue_id, status) VALUES ('a-done', ?, 'completed')",
        (issue_id,),
    )
    conn.commit()
    conn.close()

    result = runner.invoke(cli, ["--db", db_path, "reconcile", "--area", "client"])
    assert result.exit_code == 0, result.output
    assert "marking completed" in result.output


def test_reconcile_dispatch_transitions_issue_to_dispatched(runner, db_path):
    """A dispatched pending issue should be in 'dispatched' state after reconcile."""
    from orchctl.db.connection import get_db

    runner.invoke(cli, ["--db", db_path, "init"])
    conn = get_db(db_path)
    conn.execute("INSERT INTO issues (area, number, state) VALUES ('client', 9, 'pending')")
    conn.commit()
    conn.close()

    result = runner.invoke(cli, ["--db", db_path, "reconcile", "--area", "client"])
    assert result.exit_code == 0, result.output
    assert "ready to dispatch" in result.output

    conn = get_db(db_path)
    row = conn.execute(
        "SELECT state FROM issues WHERE area='client' AND number=9"
    ).fetchone()
    conn.close()
    assert row["state"] == "dispatched"


def test_reconcile_idempotent_double_run(runner, db_path):
    """Two consecutive reconcile calls produce no duplicate actions."""
    from orchctl.db.connection import get_db

    runner.invoke(cli, ["--db", db_path, "init"])
    conn = get_db(db_path)
    # Set maxConcurrent high enough that both runs can inspect the same state
    conn.execute("UPDATE config SET value = '10' WHERE key = 'max_concurrent'")
    conn.execute("UPDATE config SET value = '10' WHERE key = 'max_open_pr'")
    conn.execute("INSERT INTO issues (area, number, state) VALUES ('client', 11, 'pending')")
    conn.commit()
    conn.close()

    # First run: dispatches issue #11
    result1 = runner.invoke(cli, ["--db", db_path, "reconcile", "--area", "client"])
    assert result1.exit_code == 0, result1.output
    assert "ready to dispatch" in result1.output

    # Second run: issue is now dispatched — no duplicate dispatch
    result2 = runner.invoke(cli, ["--db", db_path, "reconcile", "--area", "client"])
    assert result2.exit_code == 0, result2.output
    assert "ready to dispatch" not in result2.output

    # Confirm only one attempt was created
    conn = get_db(db_path)
    count = conn.execute(
        "SELECT COUNT(*) FROM attempts WHERE issue_id = "
        "(SELECT id FROM issues WHERE area='client' AND number=11)"
    ).fetchone()[0]
    conn.close()
    assert count == 1


def test_reconcile_mark_complete_dispatched_to_completed(runner, db_path):
    """Dispatched issue with completed attempt transitions to completed."""
    from orchctl.db.connection import get_db

    runner.invoke(cli, ["--db", db_path, "init"])
    conn = get_db(db_path)
    conn.execute("INSERT INTO issues (area, number, state) VALUES ('client', 12, 'dispatched')")
    issue_id = conn.execute(
        "SELECT id FROM issues WHERE area='client' AND number=12"
    ).fetchone()["id"]
    conn.execute(
        "INSERT INTO attempts (attempt_id, issue_id, status) VALUES ('a-ok', ?, 'completed')",
        (issue_id,),
    )
    conn.commit()
    conn.close()

    result = runner.invoke(cli, ["--db", db_path, "reconcile", "--area", "client"])
    assert result.exit_code == 0, result.output
    assert "marking completed" in result.output

    conn = get_db(db_path)
    state = conn.execute(
        "SELECT state FROM issues WHERE area='client' AND number=12"
    ).fetchone()["state"]
    conn.close()
    assert state == "completed"


def test_reconcile_mark_complete_dispatched_to_failed_terminal(runner, db_path):
    """Dispatched issue with failed attempt transitions to failed-terminal."""
    from orchctl.db.connection import get_db

    runner.invoke(cli, ["--db", db_path, "init"])
    conn = get_db(db_path)
    conn.execute("INSERT INTO issues (area, number, state) VALUES ('client', 13, 'dispatched')")
    issue_id = conn.execute(
        "SELECT id FROM issues WHERE area='client' AND number=13"
    ).fetchone()["id"]
    conn.execute(
        "INSERT INTO attempts (attempt_id, issue_id, status) VALUES ('a-fail', ?, 'failed')",
        (issue_id,),
    )
    conn.commit()
    conn.close()

    result = runner.invoke(cli, ["--db", db_path, "reconcile", "--area", "client"])
    assert result.exit_code == 0, result.output
    assert "marking failed-terminal" in result.output

    conn = get_db(db_path)
    state = conn.execute(
        "SELECT state FROM issues WHERE area='client' AND number=13"
    ).fetchone()["state"]
    conn.close()
    assert state == "failed-terminal"


def test_reconcile_unblock_no_deps(runner, db_path):
    """Blocked issue with dependency_type='none' is unblocked to pending."""
    from orchctl.db.connection import get_db

    runner.invoke(cli, ["--db", db_path, "init"])
    conn = get_db(db_path)
    conn.execute(
        "INSERT INTO issues (area, number, state, dependency_type) VALUES ('client', 14, 'blocked', 'none')"
    )
    conn.commit()
    conn.close()

    result = runner.invoke(cli, ["--db", db_path, "reconcile", "--area", "client"])
    assert result.exit_code == 0, result.output
    assert "unblocking" in result.output

    conn = get_db(db_path)
    state = conn.execute(
        "SELECT state FROM issues WHERE area='client' AND number=14"
    ).fetchone()["state"]
    conn.close()
    assert state == "pending"


def test_reconcile_unblock_deferred_for_soft_deps(runner, db_path):
    """Blocked issue with soft dependency logs 'deferred' rather than unblocking."""
    from orchctl.db.connection import get_db

    runner.invoke(cli, ["--db", db_path, "init"])
    conn = get_db(db_path)
    conn.execute(
        "INSERT INTO issues (area, number, state, dependency_type) VALUES ('client', 15, 'blocked', 'soft')"
    )
    conn.commit()
    conn.close()

    result = runner.invoke(cli, ["--db", db_path, "reconcile", "--area", "client"])
    assert result.exit_code == 0, result.output
    assert "deferred" in result.output

    conn = get_db(db_path)
    state = conn.execute(
        "SELECT state FROM issues WHERE area='client' AND number=15"
    ).fetchone()["state"]
    conn.close()
    assert state == "blocked"  # unchanged


def test_reconcile_dry_run_no_state_change(runner, db_path):
    """--dry-run logs actions but does not change DB state."""
    from orchctl.db.connection import get_db

    runner.invoke(cli, ["--db", db_path, "init"])
    conn = get_db(db_path)
    conn.execute("INSERT INTO issues (area, number, state) VALUES ('client', 16, 'pending')")
    conn.commit()
    conn.close()

    result = runner.invoke(cli, ["--db", db_path, "reconcile", "--area", "client", "--dry-run"])
    assert result.exit_code == 0, result.output
    assert "dry-run" in result.output

    conn = get_db(db_path)
    state = conn.execute(
        "SELECT state FROM issues WHERE area='client' AND number=16"
    ).fetchone()["state"]
    attempt_count = conn.execute("SELECT COUNT(*) FROM attempts").fetchone()[0]
    conn.close()
    assert state == "pending"  # unchanged
    assert attempt_count == 0  # no attempt created
