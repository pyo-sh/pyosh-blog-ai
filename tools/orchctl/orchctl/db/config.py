"""Config table accessors for orchctl."""

import sqlite3


def get_config(conn: sqlite3.Connection, key: str, default: str = "") -> str:
    """Return a config value by key, or default if not set."""
    row = conn.execute("SELECT value FROM config WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def get_config_int(conn: sqlite3.Connection, key: str, default: int = 0) -> int:
    """Return a config value as an integer."""
    return int(get_config(conn, key, str(default)))


def get_config_bool(conn: sqlite3.Connection, key: str, default: bool = False) -> bool:
    """Return a config value as a boolean (true/1/yes → True)."""
    val = get_config(conn, key, str(default)).lower()
    return val in ("1", "true", "yes")


def set_config(conn: sqlite3.Connection, key: str, value: str) -> None:
    """Upsert a config value."""
    conn.execute(
        """
        INSERT INTO config (key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value,
                                       updated_at = datetime('now')
        """,
        (key, value),
    )
    conn.commit()


def count_dispatched(conn: sqlite3.Connection, area: str | None = None) -> int:
    """Count issues currently in 'dispatched' state.

    If area is None, counts across all areas (used for maxOpenPR global check).
    """
    if area is None:
        row = conn.execute(
            "SELECT COUNT(*) FROM issues WHERE state = 'dispatched'"
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT COUNT(*) FROM issues WHERE area = ? AND state = 'dispatched'",
            (area,),
        ).fetchone()
    return row[0] if row else 0
