"""Tests for orchctl import-state and control cutover/rollback commands."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from click.testing import CliRunner

from orchctl.cli import cli
from orchctl.commands.control import _sentinel_path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def db_path(tmp_path: Path) -> str:
    return str(tmp_path / "test.db")


def _init_db(runner, db_path):
    result = runner.invoke(cli, ["--db", db_path, "init"])
    assert result.exit_code == 0, result.output


def _make_batch_state(
    area: str,
    issues: list[int],
    status: dict[int, str] | None = None,
    dag: dict[str, list[int]] | None = None,
    dag_types: dict[str, dict[str, str]] | None = None,
) -> dict:
    status = status or {n: "pending" for n in issues}
    return {
        "area": area,
        "batchId": "batch-test",
        "issues": issues,
        "dag": dag or {},
        "dagTypes": dag_types or {},
        "crossAreaDeps": {},
        "status": {str(k): v for k, v in status.items()},
        "dispatched": {},
        "issueMetadata": {},
        "agent": "claude",
        "maxConcurrent": 4,
        "createdAt": "2026-01-01T00:00:00Z",
        "updatedAt": "2026-01-01T00:00:00Z",
    }


# ---------------------------------------------------------------------------
# import-state: dry-run
# ---------------------------------------------------------------------------


def test_import_state_dry_run(runner, db_path, tmp_path):
    _init_db(runner, db_path)
    state_file = tmp_path / "batch.state.json"
    state_file.write_text(
        json.dumps(_make_batch_state("workspace", [1, 2, 3])), encoding="utf-8"
    )

    result = runner.invoke(
        cli,
        ["--db", db_path, "import-state", "--area", "workspace",
         "--state-file", str(state_file), "--dry-run"],
    )
    assert result.exit_code == 0, result.output
    assert "dry-run" in result.output
    assert "3 issue(s)" in result.output

    # Dry-run must not write to DB.
    from orchctl.db import get_db
    conn = get_db(db_path)
    count = conn.execute("SELECT COUNT(*) FROM issues").fetchone()[0]
    conn.close()
    assert count == 0


# ---------------------------------------------------------------------------
# import-state: basic import
# ---------------------------------------------------------------------------


def test_import_state_inserts_issues(runner, db_path, tmp_path):
    _init_db(runner, db_path)
    state_file = tmp_path / "batch.state.json"
    state_file.write_text(
        json.dumps(
            _make_batch_state(
                "workspace",
                [10, 20, 30],
                status={10: "completed", 20: "failed-terminal", 30: "pending"},
            )
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        cli,
        ["--db", db_path, "import-state", "--area", "workspace",
         "--state-file", str(state_file)],
    )
    assert result.exit_code == 0, result.output
    assert "3 imported" in result.output

    from orchctl.db import get_db
    conn = get_db(db_path)
    rows = {
        r["number"]: r["state"]
        for r in conn.execute(
            "SELECT number, state FROM issues WHERE area = 'workspace'"
        ).fetchall()
    }
    conn.close()

    assert rows[10] == "completed"
    assert rows[20] == "failed-terminal"
    assert rows[30] == "pending"


# ---------------------------------------------------------------------------
# import-state: state remapping
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "legacy_state, expected_state",
    [
        ("pending", "pending"),
        ("dispatched", "pending"),          # interrupted dispatch → re-queue
        ("completed", "completed"),
        ("failed", "failed-terminal"),      # pre-v2 name
        ("failed-terminal", "failed-terminal"),
        ("needs-human", "needs-human"),
        ("needs-spec", "needs-human"),       # no orchctl equivalent
        ("blocked", "blocked"),
        ("blocked-external", "blocked-external"),
        ("blocked-failed-dependency", "blocked-failed-dependency"),
        ("skipped_dep_failed", "blocked-failed-dependency"),  # legacy alias
        ("cancelled", "cancelled"),
        ("cycle-isolated", "cancelled"),    # no orchctl equivalent
    ],
)
def test_import_state_remap(runner, db_path, tmp_path, legacy_state, expected_state):
    _init_db(runner, db_path)
    state_file = tmp_path / "batch.state.json"
    state_file.write_text(
        json.dumps(_make_batch_state("workspace", [1], status={1: legacy_state})),
        encoding="utf-8",
    )

    result = runner.invoke(
        cli,
        ["--db", db_path, "import-state", "--area", "workspace",
         "--state-file", str(state_file)],
    )
    assert result.exit_code == 0, result.output

    from orchctl.db import get_db
    conn = get_db(db_path)
    row = conn.execute(
        "SELECT state FROM issues WHERE area = 'workspace' AND number = 1"
    ).fetchone()
    conn.close()
    assert row["state"] == expected_state, f"Legacy '{legacy_state}' → expected '{expected_state}', got '{row['state']}'"


# ---------------------------------------------------------------------------
# import-state: dependency type derivation
# ---------------------------------------------------------------------------


def test_import_state_dep_types(runner, db_path, tmp_path):
    _init_db(runner, db_path)
    state_file = tmp_path / "batch.state.json"
    # Issue 2 depends on 1 (hard), issue 3 depends on 1 (soft only)
    state_file.write_text(
        json.dumps(
            _make_batch_state(
                "workspace",
                [1, 2, 3],
                dag={"2": [1], "3": [1]},
                dag_types={"3": {"1": "soft"}},
            )
        ),
        encoding="utf-8",
    )

    runner.invoke(
        cli,
        ["--db", db_path, "import-state", "--area", "workspace",
         "--state-file", str(state_file)],
    )

    from orchctl.db import get_db
    conn = get_db(db_path)
    rows = {
        r["number"]: r["dependency_type"]
        for r in conn.execute(
            "SELECT number, dependency_type FROM issues WHERE area = 'workspace'"
        ).fetchall()
    }
    conn.close()

    assert rows[1] == "none"
    assert rows[2] == "hard"
    assert rows[3] == "soft"


# ---------------------------------------------------------------------------
# import-state: skip existing, overwrite
# ---------------------------------------------------------------------------


def test_import_state_skip_existing(runner, db_path, tmp_path):
    _init_db(runner, db_path)
    state_file = tmp_path / "batch.state.json"
    state_file.write_text(
        json.dumps(_make_batch_state("workspace", [1])), encoding="utf-8"
    )

    # First import.
    runner.invoke(
        cli,
        ["--db", db_path, "import-state", "--area", "workspace",
         "--state-file", str(state_file)],
    )

    # Second import without --overwrite.
    result = runner.invoke(
        cli,
        ["--db", db_path, "import-state", "--area", "workspace",
         "--state-file", str(state_file)],
    )
    assert result.exit_code == 0, result.output
    assert "0 imported" in result.output
    assert "1 skipped" in result.output


def test_import_state_overwrite(runner, db_path, tmp_path):
    _init_db(runner, db_path)

    state_file = tmp_path / "batch.state.json"
    state_file.write_text(
        json.dumps(_make_batch_state("workspace", [1], status={1: "pending"})),
        encoding="utf-8",
    )
    runner.invoke(
        cli,
        ["--db", db_path, "import-state", "--area", "workspace",
         "--state-file", str(state_file)],
    )

    # Now overwrite with completed state.
    state_file.write_text(
        json.dumps(_make_batch_state("workspace", [1], status={1: "completed"})),
        encoding="utf-8",
    )
    result = runner.invoke(
        cli,
        ["--db", db_path, "import-state", "--area", "workspace",
         "--state-file", str(state_file), "--overwrite"],
    )
    assert result.exit_code == 0, result.output
    assert "1 updated" in result.output

    from orchctl.db import get_db
    conn = get_db(db_path)
    row = conn.execute(
        "SELECT state FROM issues WHERE area = 'workspace' AND number = 1"
    ).fetchone()
    conn.close()
    assert row["state"] == "completed"


# ---------------------------------------------------------------------------
# import-state: missing state file
# ---------------------------------------------------------------------------


def test_import_state_missing_file(runner, db_path):
    _init_db(runner, db_path)
    result = runner.invoke(
        cli,
        ["--db", db_path, "import-state", "--area", "workspace",
         "--state-file", "/nonexistent/batch.state.json"],
    )
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# control cutover / rollback
# ---------------------------------------------------------------------------


def test_cutover_sets_flag_and_creates_sentinel(runner, db_path, tmp_path):
    _init_db(runner, db_path)

    # Import one issue so the import check passes.
    state_file = tmp_path / "batch.state.json"
    state_file.write_text(
        json.dumps(_make_batch_state("workspace", [1], status={1: "completed"})),
        encoding="utf-8",
    )
    runner.invoke(
        cli,
        ["--db", db_path, "import-state", "--area", "workspace",
         "--state-file", str(state_file)],
    )

    sentinel = _sentinel_path("workspace")
    assert not sentinel.exists()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(
            cli,
            ["--db", db_path, "control", "cutover", "workspace"],
        )

    assert result.exit_code == 0, result.output
    assert "cutover complete" in result.output

    from orchctl.db import get_db, get_config
    conn = get_db(db_path)
    val = get_config(conn, "workspace.legacy_mode")
    conn.close()
    assert val == "false"


def test_cutover_blocks_on_dispatched(runner, db_path, tmp_path):
    _init_db(runner, db_path)

    # Insert a dispatched issue directly.
    from orchctl.db import get_db
    conn = get_db(db_path)
    conn.execute(
        "INSERT INTO issues (area, number, state) VALUES ('workspace', 99, 'dispatched')"
    )
    conn.commit()
    conn.close()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(
            cli,
            ["--db", db_path, "control", "cutover", "workspace",
             "--skip-import-check"],
        )

    assert result.exit_code != 0
    assert "dispatched" in result.output


def test_cutover_skip_import_check(runner, db_path, tmp_path):
    _init_db(runner, db_path)

    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(
            cli,
            ["--db", db_path, "control", "cutover", "workspace",
             "--skip-import-check"],
        )

    assert result.exit_code == 0, result.output
    assert "cutover complete" in result.output


def test_rollback_restores_legacy_mode(runner, db_path, tmp_path):
    _init_db(runner, db_path)

    # Perform cutover first.
    with runner.isolated_filesystem(temp_dir=tmp_path):
        runner.invoke(
            cli,
            ["--db", db_path, "control", "cutover", "workspace",
             "--skip-import-check"],
        )

        # Now rollback.
        result = runner.invoke(
            cli,
            ["--db", db_path, "control", "rollback", "workspace", "--confirm"],
        )

    assert result.exit_code == 0, result.output
    assert "rolled back" in result.output

    from orchctl.db import get_db, get_config
    conn = get_db(db_path)
    val = get_config(conn, "workspace.legacy_mode")
    conn.close()
    assert val == "true"


def test_rollback_when_not_cut_over(runner, db_path, tmp_path):
    _init_db(runner, db_path)

    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(
            cli,
            ["--db", db_path, "control", "rollback", "workspace", "--confirm"],
        )

    assert result.exit_code == 0, result.output
    assert "already in legacy mode" in result.output


def test_cutover_idempotent(runner, db_path, tmp_path):
    """Calling cutover twice should succeed both times."""
    _init_db(runner, db_path)

    with runner.isolated_filesystem(temp_dir=tmp_path):
        runner.invoke(
            cli,
            ["--db", db_path, "control", "cutover", "workspace",
             "--skip-import-check"],
        )
        result = runner.invoke(
            cli,
            ["--db", db_path, "control", "cutover", "workspace",
             "--skip-import-check"],
        )

    assert result.exit_code == 0, result.output
    assert "already cut over" in result.output
