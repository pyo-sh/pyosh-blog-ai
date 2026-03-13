"""Tests for multi-area coordination: global quota, cross-area deps, reconcile-all."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Callable

import pytest
from click.testing import CliRunner

from orchctl.cli import cli
from orchctl.db.connection import init_db
from orchctl.db.config import count_dispatched, get_config, get_config_int, set_config
from orchctl.db.schema import LATEST_VERSION
from orchctl.commands.reconcile import _run_pass


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def conn(tmp_path: Path):
    db_path = tmp_path / "test.db"
    c, _ = init_db(db_path)
    yield c
    c.close()


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def db_path(tmp_path: Path) -> str:
    return str(tmp_path / "test.db")


def _insert_issue(
    conn: sqlite3.Connection,
    area: str,
    number: int,
    state: str = "pending",
    dependency_type: str = "none",
    retry_count: int = 0,
) -> int:
    cur = conn.execute(
        "INSERT INTO issues (area, number, state, dependency_type, retry_count)"
        " VALUES (?, ?, ?, ?, ?)",
        (area, number, state, dependency_type, retry_count),
    )
    conn.commit()
    return cur.lastrowid


def _insert_dep(
    conn: sqlite3.Connection,
    issue_id: int,
    dep_area: str,
    dep_number: int,
    dep_type: str = "hard",
) -> None:
    conn.execute(
        "INSERT INTO dependencies (issue_id, dep_area, dep_number, dep_type)"
        " VALUES (?, ?, ?, ?)",
        (issue_id, dep_area, dep_number, dep_type),
    )
    conn.commit()


def _make_dispatch_recorder() -> tuple[list, Callable]:
    """Return (log_list, dispatch_fn) for capturing dispatch calls."""
    log: list[tuple] = []

    def dispatch_fn(area, issue_id, number, attempt_id):
        log.append((area, issue_id, number, attempt_id))

    return log, dispatch_fn


# ---------------------------------------------------------------------------
# Schema migration v11 tests
# ---------------------------------------------------------------------------


def test_dependencies_table_exists(conn):
    tables = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    assert "dependencies" in tables


def test_dependencies_unique_constraint(conn):
    issue_id = _insert_issue(conn, "client", 1, "blocked", "hard")
    _insert_dep(conn, issue_id, "server", 2, "hard")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO dependencies (issue_id, dep_area, dep_number, dep_type)"
            " VALUES (?, ?, ?, ?)",
            (issue_id, "server", 2, "soft"),
        )


def test_global_quota_config_is_max_open_pr(conn):
    """global_quota is stored as max_open_pr; default is 2."""
    val = get_config_int(conn, "max_open_pr", default=0)
    assert val == 2


def test_latest_version_is_12():
    assert LATEST_VERSION == 12


# ---------------------------------------------------------------------------
# Global quota enforcement tests
# ---------------------------------------------------------------------------


def test_global_quota_caps_cross_area_dispatch(conn):
    """Dispatching from client should be blocked when global quota is reached by server."""
    # Set global quota (max_open_pr) to 1 so one dispatched issue fills the cap.
    set_config(conn, "max_open_pr", "1")

    # server issue is already dispatched.
    srv_id = _insert_issue(conn, "server", 10, "dispatched")
    conn.execute(
        "INSERT INTO attempts (attempt_id, issue_id, status) VALUES (?, ?, 'running')",
        ("srv-a001", srv_id),
    )
    conn.commit()

    # client issue is pending.
    _insert_issue(conn, "client", 1, "pending")

    dispatched, dispatch_fn = _make_dispatch_recorder()
    _run_pass(conn, "client", 99999, dry_run=False, dispatch_fn=dispatch_fn, owns_lease=False)

    assert dispatched == [], "client should not dispatch when globalQuota=1 is full"


def test_global_quota_allows_dispatch_when_below_cap(conn):
    """Dispatch proceeds when global quota is not yet reached."""
    set_config(conn, "max_open_pr", "3")

    _insert_issue(conn, "client", 1, "pending")

    dispatched, dispatch_fn = _make_dispatch_recorder()
    _run_pass(conn, "client", 99999, dry_run=False, dispatch_fn=dispatch_fn, owns_lease=False)

    assert len(dispatched) == 1


# ---------------------------------------------------------------------------
# Cross-area dependency resolution tests
# ---------------------------------------------------------------------------


def test_unblock_hard_dep_completed(conn):
    """Blocked issue with completed hard dep → unblocked to pending."""
    dep_issue_id = _insert_issue(conn, "server", 10, "completed")
    blocked_id = _insert_issue(conn, "client", 1, "blocked", "hard")
    _insert_dep(conn, blocked_id, "server", 10, "hard")

    _run_pass(conn, "client", 99999, dry_run=False, owns_lease=False)

    row = conn.execute("SELECT state FROM issues WHERE id = ?", (blocked_id,)).fetchone()
    assert row["state"] == "pending"


def test_unblock_hard_dep_failed_blocks_with_failed_dep(conn):
    """Blocked issue with failed hard dep → blocked-failed-dependency."""
    _insert_issue(conn, "server", 10, "failed-terminal")
    blocked_id = _insert_issue(conn, "client", 1, "blocked", "hard")
    _insert_dep(conn, blocked_id, "server", 10, "hard")

    _run_pass(conn, "client", 99999, dry_run=False, owns_lease=False)

    row = conn.execute("SELECT state FROM issues WHERE id = ?", (blocked_id,)).fetchone()
    assert row["state"] == "blocked-failed-dependency"


def test_unblock_soft_dep_failed_still_unblocks(conn):
    """Blocked issue with failed soft dep → unblocked (failure does not propagate)."""
    _insert_issue(conn, "server", 10, "failed-terminal")
    blocked_id = _insert_issue(conn, "client", 1, "blocked", "soft")
    _insert_dep(conn, blocked_id, "server", 10, "soft")

    _run_pass(conn, "client", 99999, dry_run=False, owns_lease=False)

    row = conn.execute("SELECT state FROM issues WHERE id = ?", (blocked_id,)).fetchone()
    assert row["state"] == "pending"


def test_unblock_dep_still_running_stays_blocked(conn):
    """Blocked issue with a dep in 'dispatched' state → stays blocked."""
    _insert_issue(conn, "server", 10, "dispatched")
    blocked_id = _insert_issue(conn, "client", 1, "blocked", "hard")
    _insert_dep(conn, blocked_id, "server", 10, "hard")

    _run_pass(conn, "client", 99999, dry_run=False, owns_lease=False)

    row = conn.execute("SELECT state FROM issues WHERE id = ?", (blocked_id,)).fetchone()
    assert row["state"] == "blocked"


def test_unblock_dep_unknown_area_stays_blocked(conn):
    """Dep not in DB → issue stays blocked."""
    blocked_id = _insert_issue(conn, "client", 1, "blocked", "hard")
    _insert_dep(conn, blocked_id, "server", 99, "hard")  # server #99 not in DB

    _run_pass(conn, "client", 99999, dry_run=False, owns_lease=False)

    row = conn.execute("SELECT state FROM issues WHERE id = ?", (blocked_id,)).fetchone()
    assert row["state"] == "blocked"


def test_unblock_no_dep_rows_with_dep_type(conn):
    """dep_type='hard' but no dependency rows → unblocked optimistically."""
    blocked_id = _insert_issue(conn, "client", 1, "blocked", "hard")
    # No rows in dependencies table for this issue.

    _run_pass(conn, "client", 99999, dry_run=False, owns_lease=False)

    row = conn.execute("SELECT state FROM issues WHERE id = ?", (blocked_id,)).fetchone()
    assert row["state"] == "pending"


def test_unblock_same_area_dep(conn):
    """Dependency within the same area (client → client) resolves correctly."""
    dep_id = _insert_issue(conn, "client", 5, "completed")
    blocked_id = _insert_issue(conn, "client", 6, "blocked", "hard")
    _insert_dep(conn, blocked_id, "client", 5, "hard")

    _run_pass(conn, "client", 99999, dry_run=False, owns_lease=False)

    row = conn.execute("SELECT state FROM issues WHERE id = ?", (blocked_id,)).fetchone()
    assert row["state"] == "pending"


# ---------------------------------------------------------------------------
# reconcile-all command tests
# ---------------------------------------------------------------------------


def test_reconcile_all_runs_all_areas(runner, db_path):
    runner.invoke(cli, ["--db", db_path, "init"])
    result = runner.invoke(cli, ["--db", db_path, "reconcile-all", "--dry-run"])
    assert result.exit_code == 0, result.output
    # Should mention all three areas.
    assert "client" in result.output
    assert "server" in result.output
    assert "workspace" in result.output


def test_reconcile_all_subset_of_areas(runner, db_path):
    runner.invoke(cli, ["--db", db_path, "init"])
    result = runner.invoke(
        cli, ["--db", db_path, "reconcile-all", "--areas", "client,server", "--dry-run"]
    )
    assert result.exit_code == 0, result.output
    assert "client" in result.output
    assert "server" in result.output
    assert "workspace" not in result.output


def test_reconcile_all_single_area(runner, db_path):
    runner.invoke(cli, ["--db", db_path, "init"])
    result = runner.invoke(
        cli, ["--db", db_path, "reconcile-all", "--areas", "workspace", "--dry-run"]
    )
    assert result.exit_code == 0, result.output
    assert "workspace" in result.output


def test_reconcile_all_requires_init(runner, db_path):
    result = runner.invoke(cli, ["--db", db_path, "reconcile-all"])
    assert result.exit_code != 0
    assert "not initialised" in result.output


def test_reconcile_all_empty_areas_rejected(runner, db_path):
    runner.invoke(cli, ["--db", db_path, "init"])
    result = runner.invoke(cli, ["--db", db_path, "reconcile-all", "--areas", ""])
    assert result.exit_code != 0


def test_reconcile_all_global_quota_shared_across_areas(runner, db_path):
    """reconcile-all enforces global_quota (max_open_pr) across all areas in one pass."""
    runner.invoke(cli, ["--db", db_path, "init"])

    db = Path(db_path)
    conn = __import__("orchctl.db.connection", fromlist=["get_db"]).get_db(db)
    # Set global quota (max_open_pr) to 1.
    set_config(conn, "max_open_pr", "1")

    # client #1 is pending.
    conn.execute(
        "INSERT INTO issues (area, number, state, dependency_type) VALUES (?, ?, ?, ?)",
        ("client", 1, "pending", "none"),
    )
    # server #2 is pending.
    conn.execute(
        "INSERT INTO issues (area, number, state, dependency_type) VALUES (?, ?, ?, ?)",
        ("server", 2, "pending", "none"),
    )
    conn.commit()
    conn.close()

    result = runner.invoke(cli, ["--db", db_path, "reconcile-all"])
    assert result.exit_code == 0, result.output

    # Only one total should have been dispatched (globalQuota=1).
    conn2 = __import__("orchctl.db.connection", fromlist=["get_db"]).get_db(db)
    total = count_dispatched(conn2, None)
    conn2.close()
    assert total == 1, f"Expected 1 dispatched, got {total}. Output:\n{result.output}"


# ---------------------------------------------------------------------------
# Policy YAML global_quota mapping tests
# ---------------------------------------------------------------------------


def test_policy_global_max_sets_max_open_pr(conn):
    from orchctl.policy import apply_policy

    policy = {"concurrency": {"global_max": 6}}
    changed = apply_policy(conn, policy)
    assert "max_open_pr" in changed
    assert get_config(conn, "max_open_pr") == "6"


def test_policy_global_quota_key_sets_max_open_pr(conn):
    from orchctl.policy import apply_policy

    policy = {"concurrency": {"global_quota": 8}}
    changed = apply_policy(conn, policy)
    assert "max_open_pr" in changed
    assert get_config(conn, "max_open_pr") == "8"
