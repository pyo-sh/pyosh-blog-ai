"""Schema migration runner."""

import sqlite3

from .schema import MIGRATIONS, SCHEMA_VERSION


def _current_version(conn: sqlite3.Connection) -> int:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
    ).fetchone()
    if row is None:
        return 0
    row = conn.execute("SELECT version FROM schema_version").fetchone()
    return row[0] if row else 0


def run_migrations(conn: sqlite3.Connection) -> int:
    """Apply pending migrations. Returns the new schema version."""
    current = _current_version(conn)
    pending = [(v, sql) for v, sql in MIGRATIONS if v > current]
    if not pending:
        return current

    for version, sql in sorted(pending, key=lambda x: x[0]):
        conn.executescript(sql)
        conn.execute("DELETE FROM schema_version")
        conn.execute("INSERT INTO schema_version (version) VALUES (?)", (version,))
        conn.commit()

    return SCHEMA_VERSION
