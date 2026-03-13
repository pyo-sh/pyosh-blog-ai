"""orchctl export — produce a normalized per-area export for agent-tracker."""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import time
from pathlib import Path

import click

from ..contract import (
    EXPORT_PATH_TEMPLATE,
    EXPORT_SCHEMA_VERSION,
    LIVENESS_ALIVE,
    LIVENESS_DEAD,
    LIVENESS_UNKNOWN,
    validate_export,
)
from ..db import current_version, get_db
from ..db.schema import LATEST_VERSION


@click.command("export")
@click.option(
    "--area",
    required=True,
    type=click.Choice(["client", "server", "workspace"]),
    help="Area to export.",
)
@click.option(
    "--output",
    "output_path",
    default=None,
    type=click.Path(dir_okay=False, path_type=Path),
    help=(
        "Output file path.  Defaults to "
        ".workspace/orchestrate/export/{area}/current.json "
        "relative to the current directory."
    ),
)
@click.option("--validate/--no-validate", default=True, help="Validate output before writing.")
@click.option("--print", "print_output", is_flag=True, help="Print JSON to stdout.")
@click.pass_context
def cmd_export(
    ctx: click.Context,
    area: str,
    output_path: Path | None,
    validate: bool,
    print_output: bool,
) -> None:
    """Generate a normalized export snapshot for agent-tracker.

    Reads issue and attempt state from the SQLite database and writes
    a contract-compliant JSON file that the tracker can consume without
    accessing the database directly.
    """
    db_path = ctx.obj.get("db_path")
    conn = get_db(db_path)
    try:
        ver = current_version(conn)
        if ver == 0:
            raise click.ClickException("Database not initialised — run `orchctl init` first.")
        if ver < LATEST_VERSION:
            raise click.ClickException(
                f"Database schema is out of date (v{ver} < v{LATEST_VERSION}) "
                "— run `orchctl init` to migrate."
            )

        data = _build_export(conn, area)
    finally:
        conn.close()

    if validate:
        try:
            validate_export(data)
        except ValueError as exc:
            raise click.ClickException(f"Export validation failed: {exc}") from exc

    json_str = json.dumps(data, indent=2, ensure_ascii=False)

    if output_path is None:
        output_path = Path(EXPORT_PATH_TEMPLATE.format(area=area))

    _atomic_write(output_path, json_str)
    click.echo(f"export [{area}]: wrote {output_path}")

    if print_output:
        click.echo(json_str)


# ---------------------------------------------------------------------------
# Build export
# ---------------------------------------------------------------------------

def _build_export(conn: sqlite3.Connection, area: str) -> dict:
    now = time.time()

    issues = _read_issues(conn, area)
    attempts = _read_active_attempts(conn, area)
    attempt_map = {a["issue_id"]: a for a in attempts}

    issue_rows: list[dict] = []
    for row in issues:
        issue_id = row["id"]
        number = row["number"]
        state = row["state"]
        dep_type = row["dependency_type"]

        attempt = attempt_map.get(issue_id)
        attempt_id = attempt["attempt_id"] if attempt else None
        pid = attempt["pid"] if attempt else None
        started_at = attempt["started_at"] if attempt else None
        liveness = _check_liveness(pid, started_at) if pid else LIVENESS_UNKNOWN

        issue_rows.append({
            "number": number,
            "area": area,
            "state": state,
            "dependency_type": dep_type,
            "attempt_id": attempt_id,
            "pid": pid,
            "started_at": started_at,
            "liveness": liveness,
        })

    # Counts
    state_counts: dict[str, int] = {}
    for row in issues:
        state_counts[row["state"]] = state_counts.get(row["state"], 0) + 1

    n_total = len(issues)
    n_done = state_counts.get("completed", 0)
    n_failed = state_counts.get("failed-terminal", 0)
    n_pending = state_counts.get("pending", 0)
    n_dispatched = state_counts.get("dispatched", 0)

    batch_rows = [{
        "area": area,
        "n_total": n_total,
        "n_done": n_done,
        "n_failed": n_failed,
        "n_pending": n_pending,
        "n_dispatched": n_dispatched,
    }] if n_total > 0 else []

    # active_workers: dispatched issues with a running attempt
    active_workers: list[dict] = []
    for issue_row in issue_rows:
        if issue_row["state"] == "dispatched" and issue_row["attempt_id"]:
            active_workers.append({
                "attempt_id": issue_row["attempt_id"],
                "issue_number": issue_row["number"],
                "area": area,
                "pid": issue_row["pid"],
                "alive": issue_row["liveness"] == LIVENESS_ALIVE,
                "started_at": issue_row["started_at"],
            })

    return {
        "schema_version": EXPORT_SCHEMA_VERSION,
        "generated_at": now,
        "area": area,
        "issues": issue_rows,
        "batches": batch_rows,
        "active_workers": active_workers,
        "diagnostics": [],
    }


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _read_issues(conn: sqlite3.Connection, area: str) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT id, number, state, dependency_type FROM issues WHERE area = ?",
        (area,),
    ).fetchall()


def _read_active_attempts(conn: sqlite3.Connection, area: str) -> list[sqlite3.Row]:
    """Return running attempts for issues belonging to *area*."""
    return conn.execute(
        """
        SELECT a.attempt_id, a.issue_id, a.pid, a.started_at
        FROM attempts a
        JOIN issues i ON i.id = a.issue_id
        WHERE i.area = ? AND a.status = 'running'
        """,
        (area,),
    ).fetchall()


# ---------------------------------------------------------------------------
# Liveness
# ---------------------------------------------------------------------------

def _check_liveness(pid: int | None, started_at: str | None) -> str:
    """Return LIVENESS_ALIVE/DEAD/UNKNOWN for a PID.

    Uses /proc (Linux) for a lightweight check without psutil dependency.
    started_at is unused in this basic check; a future revision can
    compare against /proc/{pid}/stat for PID-reuse detection.
    """
    if not pid:
        return LIVENESS_UNKNOWN
    try:
        os.kill(pid, 0)
        return LIVENESS_ALIVE
    except ProcessLookupError:
        return LIVENESS_DEAD
    except PermissionError:
        # Process exists but we don't own it — still alive.
        return LIVENESS_ALIVE
    except OSError:
        return LIVENESS_UNKNOWN


# ---------------------------------------------------------------------------
# File I/O
# ---------------------------------------------------------------------------

def _atomic_write(path: Path, data: str) -> None:
    """Write *data* to *path* atomically (tmp + rename)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(data)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
