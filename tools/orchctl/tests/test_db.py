"""Tests for database initialization and schema migrations."""

import sqlite3
import tempfile
from pathlib import Path

import pytest

from orchctl.db.connection import init_db
from orchctl.db.schema import SCHEMA_VERSION


@pytest.fixture
def tmp_db(tmp_path: Path):
    return tmp_path / "test.db"


def test_init_creates_db(tmp_db):
    conn, version = init_db(tmp_db)
    assert tmp_db.exists()
    assert version == SCHEMA_VERSION
    conn.close()


def test_schema_tables_present(tmp_db):
    conn, _ = init_db(tmp_db)
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    conn.close()
    expected = {"issues", "attempts", "heartbeats", "leases", "config", "schema_version"}
    assert expected.issubset(tables)


def test_config_defaults_inserted(tmp_db):
    conn, _ = init_db(tmp_db)
    rows = {row["key"]: row["value"] for row in conn.execute("SELECT key, value FROM config")}
    conn.close()
    assert rows["max_concurrent"] == "4"
    assert rows["retry_budget"] == "3"
    assert rows["heartbeat_ttl"] == "120"
    assert rows["lease_ttl"] == "60"


def test_idempotent_migration(tmp_db):
    conn1, v1 = init_db(tmp_db)
    conn1.close()
    conn2, v2 = init_db(tmp_db)
    conn2.close()
    assert v1 == v2 == SCHEMA_VERSION


def test_issue_crud(tmp_db):
    conn, _ = init_db(tmp_db)
    conn.execute(
        "INSERT INTO issues (area, number, state) VALUES (?, ?, ?)",
        ("client", 42, "pending"),
    )
    conn.commit()
    row = conn.execute(
        "SELECT area, number, state FROM issues WHERE area=? AND number=?",
        ("client", 42),
    ).fetchone()
    conn.close()
    assert row["area"] == "client"
    assert row["number"] == 42
    assert row["state"] == "pending"
