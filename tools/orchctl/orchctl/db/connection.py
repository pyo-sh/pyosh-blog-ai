"""Database connection helpers."""

import sqlite3
from pathlib import Path

_DEFAULT_DB = Path.home() / ".orchctl" / "orchctl.db"


def get_db(db_path: str | Path | None = None) -> sqlite3.Connection:
    """Return a SQLite connection with WAL mode and FK enforcement."""
    path = Path(db_path) if db_path else _DEFAULT_DB
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(db_path: str | Path | None = None) -> tuple[sqlite3.Connection, int]:
    """Open DB and run migrations. Returns (connection, schema_version)."""
    from .migrate import run_migrations

    conn = get_db(db_path)
    version = run_migrations(conn)
    return conn, version
