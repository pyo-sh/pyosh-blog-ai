"""Lease acquisition, renewal, release, and stale-lease cleanup."""

import os
import sqlite3
from datetime import datetime, timedelta, timezone


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _expires(ttl: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=ttl)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def _pid_alive(pid: int) -> bool:
    """Return True if pid is a live process.

    Known limitation: if the original leaseholder crashes and the OS recycles
    its PID before the lease TTL expires, this function returns True for the
    unrelated new process.  The lease will persist until TTL elapses rather
    than being evicted immediately.  This is acceptable given the short TTL.
    """
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        # Process exists but we lack permission to signal it — it is alive.
        return True


def acquire(conn: sqlite3.Connection, area: str, pid: int, ttl: int = 60) -> bool:
    """Try to acquire the area lease for pid.

    Cleans up stale leases first, then inserts.  Returns True if this pid
    now holds the lease.
    """
    cleanup_stale(conn)
    now = _utcnow()
    exp = _expires(ttl)
    try:
        conn.execute(
            """
            INSERT INTO leases (area, holder_pid, acquired_at, heartbeat_at, expires_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (area, pid, now, now, exp),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        conn.rollback()  # discard the aborted implicit transaction
        row = conn.execute(
            "SELECT holder_pid FROM leases WHERE area = ?", (area,)
        ).fetchone()
        return row is not None and row["holder_pid"] == pid


def renew(conn: sqlite3.Connection, area: str, pid: int, ttl: int = 60) -> bool:
    """Renew the lease held by pid.  Returns True if the renewal succeeded."""
    now = _utcnow()
    exp = _expires(ttl)
    cursor = conn.execute(
        """
        UPDATE leases
        SET heartbeat_at = ?, expires_at = ?
        WHERE area = ? AND holder_pid = ?
        """,
        (now, exp, area, pid),
    )
    conn.commit()
    return cursor.rowcount > 0


def release(conn: sqlite3.Connection, area: str, pid: int) -> bool:
    """Release the lease held by pid.  Returns True if the lease was removed."""
    cursor = conn.execute(
        "DELETE FROM leases WHERE area = ? AND holder_pid = ?",
        (area, pid),
    )
    conn.commit()
    return cursor.rowcount > 0


def cleanup_stale(conn: sqlite3.Connection) -> int:
    """Delete leases that are expired or whose holder PID is no longer alive.

    Expired leases are deleted atomically in SQL to avoid TOCTOU races.
    Dead-PID leases are deleted with a precise predicate (area + holder_pid +
    expires_at) so that a concurrent insert of a fresh lease for the same area
    is not accidentally evicted.

    Does **not** call conn.commit().  The caller is responsible for committing.
    In `acquire`, the cleanup deletes and the new lease INSERT are committed
    together; in standalone usage, callers must commit explicitly.

    Returns the number of leases removed.
    """
    # Atomic expiry check — no Python snapshot involved
    expired = conn.execute(
        "DELETE FROM leases WHERE expires_at < datetime('now')"
    ).rowcount

    # Dead-PID check requires Python; use a precise predicate to avoid evicting
    # a freshly inserted lease that happens to share the same area key
    rows = conn.execute(
        "SELECT area, holder_pid, expires_at FROM leases"
    ).fetchall()
    dead = 0
    for r in rows:
        if not _pid_alive(r["holder_pid"]):
            dead += conn.execute(
                "DELETE FROM leases WHERE area = ? AND holder_pid = ? AND expires_at = ?",
                (r["area"], r["holder_pid"], r["expires_at"]),
            ).rowcount

    return expired + dead


def has_active_attempt(conn: sqlite3.Connection, issue_id: int) -> bool:
    """Return True if there is already a running attempt for issue_id."""
    row = conn.execute(
        "SELECT 1 FROM attempts WHERE issue_id = ? AND status = 'running'",
        (issue_id,),
    ).fetchone()
    return row is not None
