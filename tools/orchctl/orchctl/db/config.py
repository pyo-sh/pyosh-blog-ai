"""Config table accessors for orchctl."""

import json
import sqlite3


def get_config(conn: sqlite3.Connection, key: str, default: str = "") -> str:
    """Return a config value by key, or default if not set."""
    row = conn.execute("SELECT value FROM config WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def get_config_int(conn: sqlite3.Connection, key: str, default: int = 0) -> int:
    """Return a config value as an integer.

    Falls back to default if the stored value is missing or not a valid integer
    (e.g. from a manual DB edit or a future migration that changes the format).
    """
    raw = get_config(conn, key, str(default))
    try:
        return int(raw)
    except (ValueError, TypeError):
        return default


def get_config_bool(conn: sqlite3.Connection, key: str, default: bool = False) -> bool:
    """Return a config value as a boolean (true/1/yes → True)."""
    val = get_config(conn, key, str(default)).lower()
    return val in ("1", "true", "yes")


def get_config_json(conn: sqlite3.Connection, key: str, default: list | dict | None = None) -> list | dict:
    """Return a config value parsed as JSON (array or object).

    Falls back to *default* (or []) when the key is missing or the stored
    value is not valid JSON.
    """
    if default is None:
        default = []
    raw = get_config(conn, key, "")
    if not raw:
        return default
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, (list, dict)) else default
    except (ValueError, TypeError):
        return default


def get_config_float(conn: sqlite3.Connection, key: str, *, default: float) -> float:
    """Return a config value as a float, returning default on error."""
    raw = get_config(conn, key, default=None)
    if raw is None:
        return default
    try:
        return float(raw)
    except (ValueError, TypeError):
        return default


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
    return row[0]
