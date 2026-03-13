"""Tests for orchctl control commands — pause, resume, drain, stop, cancel-attempt, requeue."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from orchctl.cli import cli
from orchctl.db.config import get_config, get_config_bool
from orchctl.db.connection import get_db


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def db_path(tmp_path: Path) -> str:
    path = str(tmp_path / "test.db")
    runner_ = CliRunner()
    runner_.invoke(cli, ["--db", path, "init"])
    return path


def _insert_issue(db_path: str, area: str, number: int, state: str = "pending") -> int:
    conn = get_db(db_path)
    cur = conn.execute(
        "INSERT INTO issues (area, number, state) VALUES (?, ?, ?)",
        (area, number, state),
    )
    conn.commit()
    issue_id = cur.lastrowid
    conn.close()
    return issue_id


def _get_issue_state(db_path: str, area: str, number: int) -> str:
    conn = get_db(db_path)
    row = conn.execute(
        "SELECT state FROM issues WHERE area = ? AND number = ?", (area, number)
    ).fetchone()
    conn.close()
    return row["state"]


# ---------------------------------------------------------------------------
# pause / resume
# ---------------------------------------------------------------------------


def test_pause_sets_area_paused(runner, db_path):
    result = runner.invoke(cli, ["--db", db_path, "control", "pause", "client"])
    assert result.exit_code == 0, result.output
    assert "paused" in result.output

    conn = get_db(db_path)
    assert get_config_bool(conn, "client.paused") is True
    conn.close()


def test_resume_clears_area_paused(runner, db_path):
    runner.invoke(cli, ["--db", db_path, "control", "pause", "client"])
    result = runner.invoke(cli, ["--db", db_path, "control", "resume", "client"])
    assert result.exit_code == 0, result.output
    assert "resumed" in result.output

    conn = get_db(db_path)
    assert get_config_bool(conn, "client.paused") is False
    conn.close()


def test_pause_does_not_affect_other_areas(runner, db_path):
    runner.invoke(cli, ["--db", db_path, "control", "pause", "client"])

    conn = get_db(db_path)
    assert get_config_bool(conn, "server.paused") is False
    conn.close()


# ---------------------------------------------------------------------------
# drain
# ---------------------------------------------------------------------------


def test_drain_enables_drain_mode(runner, db_path):
    result = runner.invoke(cli, ["--db", db_path, "control", "drain"])
    assert result.exit_code == 0, result.output
    assert "drain mode enabled" in result.output

    conn = get_db(db_path)
    assert get_config_bool(conn, "drain_mode") is True
    conn.close()


# ---------------------------------------------------------------------------
# stop
# ---------------------------------------------------------------------------


def test_stop_requires_confirm_flag(runner, db_path):
    result = runner.invoke(cli, ["--db", db_path, "control", "stop", "client"])
    assert result.exit_code != 0


def test_stop_cancels_dispatched_issues(runner, db_path):
    _insert_issue(db_path, "client", 1, "dispatched")
    _insert_issue(db_path, "client", 2, "dispatched")
    _insert_issue(db_path, "client", 3, "pending")  # should not be stopped

    result = runner.invoke(
        cli, ["--db", db_path, "control", "stop", "client", "--confirm"]
    )
    assert result.exit_code == 0, result.output
    assert "stopped 2 issue(s)" in result.output

    assert _get_issue_state(db_path, "client", 1) == "cancelled"
    assert _get_issue_state(db_path, "client", 2) == "cancelled"
    assert _get_issue_state(db_path, "client", 3) == "pending"  # untouched


def test_stop_reports_no_issues_when_none_dispatched(runner, db_path):
    result = runner.invoke(
        cli, ["--db", db_path, "control", "stop", "client", "--confirm"]
    )
    assert result.exit_code == 0, result.output
    assert "no dispatched issues" in result.output


def test_stop_does_not_affect_other_areas(runner, db_path):
    _insert_issue(db_path, "server", 10, "dispatched")
    _insert_issue(db_path, "client", 11, "dispatched")

    runner.invoke(cli, ["--db", db_path, "control", "stop", "client", "--confirm"])

    assert _get_issue_state(db_path, "server", 10) == "dispatched"
    assert _get_issue_state(db_path, "client", 11) == "cancelled"


# ---------------------------------------------------------------------------
# cancel-attempt
# ---------------------------------------------------------------------------


def test_cancel_attempt_cancels_dispatched_issue(runner, db_path):
    issue_id = _insert_issue(db_path, "client", 20, "dispatched")
    conn = get_db(db_path)
    conn.execute(
        "INSERT INTO attempts (attempt_id, issue_id, status) VALUES ('att-20', ?, 'running')",
        (issue_id,),
    )
    conn.commit()
    conn.close()

    result = runner.invoke(
        cli,
        ["--db", db_path, "control", "cancel-attempt", "--area", "client", "--issue", "20"],
    )
    assert result.exit_code == 0, result.output
    assert "cancelled" in result.output
    assert _get_issue_state(db_path, "client", 20) == "cancelled"


def test_cancel_attempt_marks_running_attempt_failed(runner, db_path):
    issue_id = _insert_issue(db_path, "client", 21, "dispatched")
    conn = get_db(db_path)
    conn.execute(
        "INSERT INTO attempts (attempt_id, issue_id, status) VALUES ('att-21', ?, 'running')",
        (issue_id,),
    )
    conn.commit()
    conn.close()

    runner.invoke(
        cli,
        ["--db", db_path, "control", "cancel-attempt", "--area", "client", "--issue", "21"],
    )

    conn = get_db(db_path)
    attempt = conn.execute(
        "SELECT status FROM attempts WHERE attempt_id = 'att-21'"
    ).fetchone()
    conn.close()
    assert attempt["status"] == "failed"


def test_cancel_attempt_rejects_non_dispatched_issue(runner, db_path):
    _insert_issue(db_path, "client", 22, "pending")
    result = runner.invoke(
        cli,
        ["--db", db_path, "control", "cancel-attempt", "--area", "client", "--issue", "22"],
    )
    assert result.exit_code != 0
    assert "not 'dispatched'" in result.output


def test_cancel_attempt_rejects_unknown_issue(runner, db_path):
    result = runner.invoke(
        cli,
        ["--db", db_path, "control", "cancel-attempt", "--area", "client", "--issue", "999"],
    )
    assert result.exit_code != 0
    assert "not found" in result.output


# ---------------------------------------------------------------------------
# requeue
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("state", ["failed-terminal", "cancelled", "needs-human", "blocked-failed-dependency"])
def test_requeue_requeueable_states(runner, db_path, state):
    _insert_issue(db_path, "client", 30, state)
    result = runner.invoke(
        cli,
        ["--db", db_path, "control", "requeue", "--area", "client", "--issue", "30"],
    )
    assert result.exit_code == 0, result.output
    assert "requeued" in result.output
    assert _get_issue_state(db_path, "client", 30) == "pending"


def test_requeue_rejects_dispatched_issue(runner, db_path):
    _insert_issue(db_path, "client", 31, "dispatched")
    result = runner.invoke(
        cli,
        ["--db", db_path, "control", "requeue", "--area", "client", "--issue", "31"],
    )
    assert result.exit_code != 0
    assert "requeue requires" in result.output


def test_requeue_rejects_pending_issue(runner, db_path):
    _insert_issue(db_path, "client", 32, "pending")
    result = runner.invoke(
        cli,
        ["--db", db_path, "control", "requeue", "--area", "client", "--issue", "32"],
    )
    assert result.exit_code != 0


def test_requeue_rejects_completed_issue(runner, db_path):
    _insert_issue(db_path, "client", 33, "completed")
    result = runner.invoke(
        cli,
        ["--db", db_path, "control", "requeue", "--area", "client", "--issue", "33"],
    )
    assert result.exit_code != 0


def test_requeue_rejects_unknown_issue(runner, db_path):
    result = runner.invoke(
        cli,
        ["--db", db_path, "control", "requeue", "--area", "client", "--issue", "999"],
    )
    assert result.exit_code != 0
    assert "not found" in result.output


# ---------------------------------------------------------------------------
# requires init
# ---------------------------------------------------------------------------


def test_control_pause_requires_init(runner, tmp_path):
    db_path = str(tmp_path / "new.db")
    result = runner.invoke(cli, ["--db", db_path, "control", "pause", "client"])
    assert result.exit_code != 0
    assert "not initialised" in result.output


# ---------------------------------------------------------------------------
# reconcile respects area pause
# ---------------------------------------------------------------------------


def test_reconcile_skips_when_area_paused(runner, db_path):
    _insert_issue(db_path, "client", 40, "pending")
    runner.invoke(cli, ["--db", db_path, "control", "pause", "client"])

    result = runner.invoke(cli, ["--db", db_path, "reconcile", "--area", "client"])
    assert result.exit_code == 0, result.output
    assert "area is paused" in result.output
    assert "ready to dispatch" not in result.output

    assert _get_issue_state(db_path, "client", 40) == "pending"


def test_reconcile_dispatches_after_resume(runner, db_path):
    _insert_issue(db_path, "client", 41, "pending")
    runner.invoke(cli, ["--db", db_path, "control", "pause", "client"])
    runner.invoke(cli, ["--db", db_path, "control", "resume", "client"])

    result = runner.invoke(cli, ["--db", db_path, "reconcile", "--area", "client"])
    assert result.exit_code == 0, result.output
    assert "ready to dispatch" in result.output
