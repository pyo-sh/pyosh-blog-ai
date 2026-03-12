"""Tests for leader lease and dispatch idempotency."""

import os
import sqlite3
from pathlib import Path

import pytest

from orchctl.db.connection import init_db
from orchctl.db.lease import acquire, cleanup_stale, has_active_attempt, release, renew


@pytest.fixture
def conn(tmp_path: Path):
    db = tmp_path / "test.db"
    c, _ = init_db(db)
    yield c
    c.close()


# ---------------------------------------------------------------------------
# acquire
# ---------------------------------------------------------------------------

def test_acquire_succeeds_when_free(conn):
    assert acquire(conn, "client", os.getpid()) is True


def test_acquire_stores_heartbeat_at(conn):
    acquire(conn, "client", os.getpid())
    row = conn.execute("SELECT heartbeat_at FROM leases WHERE area = 'client'").fetchone()
    assert row is not None
    assert row["heartbeat_at"] is not None


def test_acquire_returns_true_for_same_pid(conn):
    pid = os.getpid()
    acquire(conn, "server", pid)
    assert acquire(conn, "server", pid) is True


def test_acquire_returns_false_when_held_by_other(conn):
    # Use PID 1 (init) — guaranteed alive, so cleanup_stale will not evict it
    conn.execute(
        "INSERT INTO leases (area, holder_pid, acquired_at, heartbeat_at, expires_at) "
        "VALUES ('client', 1, datetime('now'), datetime('now'), datetime('now', '+1 hour'))"
    )
    conn.commit()
    assert acquire(conn, "client", os.getpid()) is False


# ---------------------------------------------------------------------------
# renew
# ---------------------------------------------------------------------------

def test_renew_updates_expiry(conn):
    pid = os.getpid()
    acquire(conn, "client", pid)
    result = renew(conn, "client", pid)
    assert result is True


def test_renew_fails_for_wrong_pid(conn):
    acquire(conn, "client", os.getpid())
    result = renew(conn, "client", 99999999)
    assert result is False


# ---------------------------------------------------------------------------
# release
# ---------------------------------------------------------------------------

def test_release_removes_lease(conn):
    pid = os.getpid()
    acquire(conn, "client", pid)
    assert release(conn, "client", pid) is True
    row = conn.execute("SELECT 1 FROM leases WHERE area = 'client'").fetchone()
    assert row is None


def test_release_fails_for_wrong_pid(conn):
    acquire(conn, "client", os.getpid())
    result = release(conn, "client", 99999999)
    assert result is False


def test_release_on_nonexistent_lease(conn):
    assert release(conn, "client", os.getpid()) is False


# ---------------------------------------------------------------------------
# cleanup_stale
# ---------------------------------------------------------------------------

def test_cleanup_removes_expired_lease(conn):
    conn.execute(
        "INSERT INTO leases (area, holder_pid, acquired_at, heartbeat_at, expires_at) "
        "VALUES ('client', 1, '2020-01-01 00:00:00', '2020-01-01 00:00:00', '2020-01-01 00:01:00')"
    )
    conn.commit()
    removed = cleanup_stale(conn)
    conn.commit()
    assert removed == 1
    assert conn.execute("SELECT 1 FROM leases WHERE area = 'client'").fetchone() is None


def _dead_pid() -> int:
    """Fork a child that exits immediately; return its now-dead PID."""
    pid = os.fork()
    if pid == 0:
        os._exit(0)
    os.waitpid(pid, 0)
    return pid


def test_cleanup_removes_dead_pid_lease(conn):
    dead = _dead_pid()
    conn.execute(
        "INSERT INTO leases (area, holder_pid, acquired_at, heartbeat_at, expires_at) "
        "VALUES ('server', ?, datetime('now'), datetime('now'), datetime('now', '+1 hour'))",
        (dead,),
    )
    conn.commit()
    removed = cleanup_stale(conn)
    conn.commit()
    assert removed == 1


def test_cleanup_leaves_live_lease(conn):
    pid = os.getpid()
    acquire(conn, "client", pid)
    removed = cleanup_stale(conn)
    conn.commit()
    assert removed == 0
    assert conn.execute("SELECT 1 FROM leases WHERE area = 'client'").fetchone() is not None


# ---------------------------------------------------------------------------
# has_active_attempt
# ---------------------------------------------------------------------------

def _insert_issue(conn, area="client", number=1) -> int:
    conn.execute(
        "INSERT INTO issues (area, number, state) VALUES (?, ?, 'pending')",
        (area, number),
    )
    conn.commit()
    return conn.execute(
        "SELECT id FROM issues WHERE area = ? AND number = ?", (area, number)
    ).fetchone()["id"]


def test_has_active_attempt_true(conn):
    issue_id = _insert_issue(conn)
    conn.execute(
        "INSERT INTO attempts (attempt_id, issue_id, status) VALUES ('a1', ?, 'running')",
        (issue_id,),
    )
    conn.commit()
    assert has_active_attempt(conn, issue_id) is True


def test_has_active_attempt_false_when_empty(conn):
    issue_id = _insert_issue(conn)
    assert has_active_attempt(conn, issue_id) is False


def test_has_active_attempt_false_for_terminal(conn):
    issue_id = _insert_issue(conn)
    conn.execute(
        "INSERT INTO attempts (attempt_id, issue_id, status) VALUES ('a1', ?, 'completed')",
        (issue_id,),
    )
    conn.commit()
    assert has_active_attempt(conn, issue_id) is False


def test_unique_index_prevents_duplicate_active_attempts(conn):
    issue_id = _insert_issue(conn)
    conn.execute(
        "INSERT INTO attempts (attempt_id, issue_id, status) VALUES ('a1', ?, 'running')",
        (issue_id,),
    )
    conn.commit()
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO attempts (attempt_id, issue_id, status) VALUES ('a2', ?, 'running')",
            (issue_id,),
        )
        conn.commit()


def test_unique_index_allows_multiple_terminal(conn):
    issue_id = _insert_issue(conn)
    conn.execute(
        "INSERT INTO attempts (attempt_id, issue_id, status) VALUES ('a1', ?, 'completed')",
        (issue_id,),
    )
    conn.execute(
        "INSERT INTO attempts (attempt_id, issue_id, status) VALUES ('a2', ?, 'failed')",
        (issue_id,),
    )
    conn.commit()
