"""orchctl import-state — import legacy batch.state.json into SQLite."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import click

from ..db import current_version, get_db, set_config
from ..db.schema import LATEST_VERSION
from ..models import IssueState


# ---------------------------------------------------------------------------
# Legacy state → orchctl state mapping
# ---------------------------------------------------------------------------

_LEGACY_STATE_MAP: dict[str, str] = {
    "pending": IssueState.PENDING.value,
    # dispatched = batch interrupted mid-run; re-queue as pending
    "dispatched": IssueState.PENDING.value,
    "completed": IssueState.COMPLETED.value,
    # legacy names for terminal failure
    "failed": IssueState.FAILED_TERMINAL.value,
    "failed-terminal": IssueState.FAILED_TERMINAL.value,
    "needs-human": IssueState.NEEDS_HUMAN.value,
    # needs-spec has no direct orchctl equivalent; treat as needs-human
    "needs-spec": IssueState.NEEDS_HUMAN.value,
    "blocked": IssueState.BLOCKED.value,
    "blocked-external": IssueState.BLOCKED_EXTERNAL.value,
    "blocked-failed-dependency": IssueState.BLOCKED_FAILED_DEP.value,
    # legacy name used before renaming
    "skipped_dep_failed": IssueState.BLOCKED_FAILED_DEP.value,
    "cancelled": IssueState.CANCELLED.value,
    # cycle-isolated has no orchctl equivalent; treat as cancelled
    "cycle-isolated": IssueState.CANCELLED.value,
}

# States that are treated as "already terminal / done" and reported at import
_WARN_REMAP_STATES = {"dispatched", "needs-spec", "cycle-isolated"}


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------


@click.command("import-state")
@click.option(
    "--area",
    required=True,
    type=click.Choice(["client", "server", "workspace"]),
    help="Area whose legacy state is being imported.",
)
@click.option(
    "--state-file",
    "state_file",
    default=None,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help=(
        "Path to batch.state.json.  Defaults to "
        ".workspace/orchestrate/<area>/batch.state.json "
        "relative to the current directory."
    ),
)
@click.option(
    "--overwrite",
    is_flag=True,
    default=False,
    help="Replace the state of issues that already exist in the DB.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Print what would be imported without writing to the DB.",
)
@click.pass_context
def cmd_import_state(
    ctx: click.Context,
    area: str,
    state_file: Path | None,
    overwrite: bool,
    dry_run: bool,
) -> None:
    """Import legacy batch.state.json into the orchctl SQLite database.

    State mapping applied during import:

    \b
      pending              → pending
      dispatched           → pending  (interrupted; re-queued)
      completed            → completed
      failed / failed-terminal → failed-terminal
      needs-human / needs-spec → needs-human
      blocked              → blocked
      blocked-external     → blocked-external
      blocked-failed-dependency / skipped_dep_failed → blocked-failed-dependency
      cancelled / cycle-isolated → cancelled

    Issues that already exist in the DB are skipped unless --overwrite is given.

    After a successful import, run:
        orchctl control cutover <area>
    to activate orchctl and disable the legacy shell orchestrator.
    """
    db_path = ctx.obj.get("db_path")

    if state_file is None:
        state_file = Path(f".workspace/orchestrate/{area}/batch.state.json")

    if not state_file.exists():
        raise click.ClickException(
            f"State file not found: {state_file}\n"
            "Pass --state-file to specify an alternate path."
        )

    # Parse the legacy state file.
    try:
        raw = json.loads(state_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise click.ClickException(f"Invalid JSON in state file: {exc}") from exc

    issues, status_map, dag_types = _parse_legacy_state(raw, area)

    if dry_run:
        click.echo(f"[dry-run] Would import {len(issues)} issue(s) from {state_file}")
        for number, state in status_map.items():
            dep_type = dag_types.get(number, "none")
            click.echo(f"  #{number}: {_legacy_state_label(state)} → {_LEGACY_STATE_MAP.get(state, '?')} (dep={dep_type})")
        return

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

        imported, skipped, updated = _import_issues(
            conn, area, issues, status_map, dag_types, overwrite
        )
    finally:
        conn.close()

    click.echo(
        f"import-state [{area}]: {imported} imported, {updated} updated, {skipped} skipped."
    )
    if imported + updated > 0:
        click.echo(
            "\nNext step: orchctl control cutover "
            f"{area}"
            "\n  Activates orchctl and blocks the legacy shell orchestrator."
        )


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


def _parse_legacy_state(
    raw: dict,
    area: str,
) -> tuple[list[int], dict[int, str], dict[int, str]]:
    """Extract issues, per-issue state, and dep types from batch.state.json.

    Returns:
        issues     — list of issue numbers (int)
        status_map — {issue_number: legacy_state_string}
        dag_types  — {issue_number: "none"|"soft"|"hard"}
    """
    issues_raw = raw.get("issues", [])
    if not isinstance(issues_raw, list):
        raise click.ClickException("batch.state.json: 'issues' must be a JSON array.")

    issues: list[int] = []
    for n in issues_raw:
        try:
            issues.append(int(n))
        except (TypeError, ValueError):
            raise click.ClickException(
                f"batch.state.json: non-integer issue number: {n!r}"
            )

    status_raw: dict = raw.get("status", {})
    status_map: dict[int, str] = {}
    for n in issues:
        state = status_raw.get(str(n), "pending")
        if state not in _LEGACY_STATE_MAP:
            click.echo(
                f"  [WARN] Unknown state {state!r} for #{n} — mapping to 'pending'",
                err=True,
            )
            state = "pending"
        status_map[n] = state

    # Dependency type: an issue has a dependency_type if it has at least one dep
    # in the DAG. The dominant type across all its deps is recorded.
    dag: dict = raw.get("dag", {})          # {"N": [deps...]}
    dag_types_raw: dict = raw.get("dagTypes", {})  # {"N": {"dep": "hard"|"soft"}}

    dag_types: dict[int, str] = {}
    for n in issues:
        deps = dag.get(str(n), [])
        if not deps:
            dag_types[n] = "none"
            continue
        # If any dep is "hard" (or unspecified), the issue gets dep_type "hard".
        issue_dtypes = dag_types_raw.get(str(n), {})
        all_soft = all(
            issue_dtypes.get(str(d), "hard") == "soft" for d in deps
        )
        dag_types[n] = "soft" if all_soft else "hard"

    return issues, status_map, dag_types


def _legacy_state_label(state: str) -> str:
    """Add a remap warning suffix for states that are lossy."""
    if state in _WARN_REMAP_STATES:
        return f"{state} (remapped)"
    return state


# ---------------------------------------------------------------------------
# DB write
# ---------------------------------------------------------------------------


def _import_issues(
    conn,
    area: str,
    issues: list[int],
    status_map: dict[int, str],
    dag_types: dict[int, str],
    overwrite: bool,
) -> tuple[int, int, int]:
    """Insert/update issues in the DB.

    Returns (imported, skipped, updated) counts.
    """
    imported = skipped = updated = 0

    with conn:
        for number in issues:
            legacy_state = status_map.get(number, "pending")
            target_state = _LEGACY_STATE_MAP.get(legacy_state, IssueState.PENDING.value)
            dep_type = dag_types.get(number, "none")

            existing = conn.execute(
                "SELECT id, state FROM issues WHERE area = ? AND number = ?",
                (area, number),
            ).fetchone()

            if existing is None:
                conn.execute(
                    """
                    INSERT INTO issues (area, number, state, dependency_type)
                    VALUES (?, ?, ?, ?)
                    """,
                    (area, number, target_state, dep_type),
                )
                imported += 1
                if legacy_state in _WARN_REMAP_STATES:
                    click.echo(
                        f"  [WARN] #{number}: legacy state '{legacy_state}' "
                        f"remapped to '{target_state}'",
                        err=True,
                    )
            elif overwrite:
                conn.execute(
                    """
                    UPDATE issues SET state = ?, dependency_type = ?
                    WHERE area = ? AND number = ?
                    """,
                    (target_state, dep_type, area, number),
                )
                updated += 1
            else:
                skipped += 1

    return imported, skipped, updated
