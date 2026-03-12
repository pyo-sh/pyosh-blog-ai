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

    Returns the number of leases removed.
    """
    rows = conn.execute(
        "SELECT area, holder_pid, expires_at FROM leases"
    ).fetchall()
    now = _utcnow()
    stale = [
        r["area"]
        for r in rows
        if r["expires_at"] < now or not _pid_alive(r["holder_pid"])
    ]
    if not stale:
        return 0
    placeholders = ",".join("?" * len(stale))
    cursor = conn.execute(
        f"DELETE FROM leases WHERE area IN ({placeholders})", stale
    )
    conn.commit()
    return cursor.rowcount


def has_active_attempt(conn: sqlite3.Connection, issue_id: int) -> bool:
    """Return True if there is already a running attempt for issue_id."""
    row = conn.execute(
        "SELECT 1 FROM attempts WHERE issue_id = ? AND status = 'running'",
        (issue_id,),
    ).fetchone()
    return row is not None
