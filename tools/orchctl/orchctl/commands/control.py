"""orchctl control commands — pause, resume, drain, stop, cancel-attempt, requeue, cutover, rollback."""

from __future__ import annotations

import os
from pathlib import Path

import click

from ..db import get_config, get_db, set_config
from ..db.schema import LATEST_VERSION
from ..state_machine import apply_issue_transition, apply_issue_transition_tx


# ---------------------------------------------------------------------------
# Sentinel helpers (single-writer guarantee)
# ---------------------------------------------------------------------------

_SENTINEL_NAME = ".orchctl-active"


def _sentinel_path(area: str) -> Path:
    """Return the path of the per-area orchctl-active sentinel file.

    Resolves the monorepo root from the MONOREPO_ROOT environment variable
    (set by monorepo-helpers.sh). Falls back to cwd so that tests and ad-hoc
    invocations from the monorepo root still work.

    The shell guard in orchestrate-helpers.sh anchors to $MONOREPO_ROOT
    identically, so Python and bash always agree on the sentinel location.
    """
    root = Path(os.environ.get("MONOREPO_ROOT", "."))
    return root / ".workspace" / "orchestrate" / area / _SENTINEL_NAME


def _sentinel_exists(area: str) -> bool:
    return _sentinel_path(area).exists()


def _create_sentinel(area: str) -> None:
    path = _sentinel_path(area)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"orchctl-active: {area}\n"
        f"pid: {os.getpid()}\n"
        "# This file signals that orchctl has taken over for this area.\n"
        "# Remove via: orchctl control rollback <area>\n",
        encoding="utf-8",
    )


def _remove_sentinel(area: str) -> bool:
    path = _sentinel_path(area)
    if path.exists():
        path.unlink()
        return True
    return False


def _legacy_mode_key(area: str) -> str:
    return f"{area}.legacy_mode"


# ---------------------------------------------------------------------------
# Group
# ---------------------------------------------------------------------------


@click.group("control")
def cmd_control() -> None:
    """Operational control: pause, resume, drain, stop, cancel-attempt, requeue."""


# ---------------------------------------------------------------------------
# Area-scoped pause
# ---------------------------------------------------------------------------


def _pause_key(area: str) -> str:
    return f"{area}.paused"


@cmd_control.command("pause")
@click.argument("area")
@click.pass_context
def cmd_pause(ctx: click.Context, area: str) -> None:
    """Pause new dispatches for AREA (running workers are not interrupted)."""
    conn = get_db(ctx.obj.get("db_path"))
    try:
        _require_ready(conn)
        set_config(conn, _pause_key(area), "true")
        click.echo(f"control [{area}]: paused — no new dispatches until 'control resume {area}'.")
    finally:
        conn.close()


@cmd_control.command("resume")
@click.argument("area")
@click.pass_context
def cmd_resume(ctx: click.Context, area: str) -> None:
    """Resume dispatches for AREA."""
    conn = get_db(ctx.obj.get("db_path"))
    try:
        _require_ready(conn)
        set_config(conn, _pause_key(area), "false")
        click.echo(f"control [{area}]: resumed.")
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Global drain
# ---------------------------------------------------------------------------


@cmd_control.command("drain")
@click.pass_context
def cmd_drain(ctx: click.Context) -> None:
    """Enable drain mode globally (no new dispatches; running workers finish)."""
    conn = get_db(ctx.obj.get("db_path"))
    try:
        _require_ready(conn)
        set_config(conn, "drain_mode", "true")
        click.echo("control: drain mode enabled — no new dispatches globally.")
    finally:
        conn.close()


@cmd_control.command("undrain")
@click.pass_context
def cmd_undrain(ctx: click.Context) -> None:
    """Disable drain mode globally (resume normal dispatches)."""
    conn = get_db(ctx.obj.get("db_path"))
    try:
        _require_ready(conn)
        set_config(conn, "drain_mode", "false")
        click.echo("control: drain mode disabled — dispatches will resume on next reconcile.")
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Stop all dispatched for an area
# ---------------------------------------------------------------------------


@cmd_control.command("stop")
@click.argument("area")
@click.option("--confirm", is_flag=True, required=True, help="Confirm stopping all dispatched issues.")
@click.pass_context
def cmd_stop(ctx: click.Context, area: str, confirm: bool) -> None:
    """Cancel all dispatched issues for AREA (requires --confirm)."""
    conn = get_db(ctx.obj.get("db_path"))
    try:
        _require_ready(conn)
        rows = conn.execute(
            "SELECT id, number FROM issues WHERE area = ? AND state = 'dispatched'",
            (area,),
        ).fetchall()
        if not rows:
            click.echo(f"control [{area}]: no dispatched issues to stop.")
            return
        # Cancel all in one transaction so partial failure leaves no mixed state.
        try:
            for row in rows:
                apply_issue_transition_tx(conn, row["id"], "cancelled")
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        for row in rows:
            click.echo(f"control [{area}]: issue #{row['number']} → cancelled.")
        click.echo(f"control [{area}]: stopped {len(rows)} issue(s).")
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Cancel a single attempt
# ---------------------------------------------------------------------------


@cmd_control.command("cancel-attempt")
@click.option("--area", required=True, help="Area of the issue.")
@click.option("--issue", "issue_number", required=True, type=int, help="Issue number.")
@click.pass_context
def cmd_cancel_attempt(ctx: click.Context, area: str, issue_number: int) -> None:
    """Cancel the active attempt for AREA issue ISSUE_NUMBER."""
    conn = get_db(ctx.obj.get("db_path"))
    try:
        _require_ready(conn)
        issue_row = conn.execute(
            "SELECT id, state FROM issues WHERE area = ? AND number = ?",
            (area, issue_number),
        ).fetchone()
        if issue_row is None:
            raise click.ClickException(
                f"Issue #{issue_number} not found in area '{area}'."
            )
        if issue_row["state"] != "dispatched":
            raise click.ClickException(
                f"Issue #{issue_number} is in state '{issue_row['state']}', not 'dispatched'."
            )
        # Batch attempt update and issue transition in one transaction.
        try:
            conn.execute(
                "UPDATE attempts SET status = 'failed' WHERE issue_id = ? AND status = 'running'",
                (issue_row["id"],),
            )
            apply_issue_transition_tx(conn, issue_row["id"], "cancelled")
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        click.echo(f"control [{area}]: issue #{issue_number} attempt cancelled.")
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Requeue a failed/cancelled issue
# ---------------------------------------------------------------------------


@cmd_control.command("requeue")
@click.option("--area", required=True, help="Area of the issue.")
@click.option("--issue", "issue_number", required=True, type=int, help="Issue number.")
@click.pass_context
def cmd_requeue(ctx: click.Context, area: str, issue_number: int) -> None:
    """Requeue a failed, cancelled, or needs-human issue back to pending."""
    conn = get_db(ctx.obj.get("db_path"))
    try:
        _require_ready(conn)
        issue_row = conn.execute(
            "SELECT id, state FROM issues WHERE area = ? AND number = ?",
            (area, issue_number),
        ).fetchone()
        if issue_row is None:
            raise click.ClickException(
                f"Issue #{issue_number} not found in area '{area}'."
            )
        state = issue_row["state"]
        _REQUEUEABLE = {"failed-terminal", "cancelled", "needs-human", "blocked-failed-dependency"}
        if state not in _REQUEUEABLE:
            raise click.ClickException(
                f"Issue #{issue_number} is in state '{state}'; "
                f"requeue requires one of: {', '.join(sorted(_REQUEUEABLE))}."
            )
        apply_issue_transition(conn, issue_row["id"], "pending")
        click.echo(f"control [{area}]: issue #{issue_number} requeued → pending.")
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Cutover: legacy shell → orchctl
# ---------------------------------------------------------------------------


@cmd_control.command("cutover")
@click.argument("area", type=click.Choice(["client", "server", "workspace"]))
@click.option(
    "--skip-import-check",
    is_flag=True,
    default=False,
    help="Skip the check that at least one issue was imported for this area.",
)
@click.pass_context
def cmd_cutover(ctx: click.Context, area: str, skip_import_check: bool) -> None:
    """Activate orchctl for AREA and disable the legacy shell orchestrator.

    Pre-conditions (checked automatically unless --skip-import-check):

    \b
      1. At least one issue exists in the DB for this area (imported via
         'orchctl import-state').
      2. No dispatched issues in the DB (only catches non-import code paths;
         operators must drain the shell batch before running import-state).

    After cutover:

    \b
      - The legacy shell orchestrator will refuse to start for this area
        (checked via the .orchctl-active sentinel file).
      - orchctl reconcile is the only writer for this area.

    To undo: orchctl control rollback <area>
    """
    conn = get_db(ctx.obj.get("db_path"))
    try:
        _require_ready(conn)

        raw = get_config(conn, _legacy_mode_key(area), "true")
        if raw == "false":
            click.echo(f"control [{area}]: already cut over to orchctl.")
            if not _sentinel_exists(area):
                _create_sentinel(area)
                click.echo(f"control [{area}]: sentinel recreated at {_sentinel_path(area)}")
            return

        if not skip_import_check:
            count = conn.execute(
                "SELECT COUNT(*) FROM issues WHERE area = ?", (area,)
            ).fetchone()[0]
            if count == 0:
                raise click.ClickException(
                    f"No issues found in DB for area '{area}'.\n"
                    "Run 'orchctl import-state --area <area>' first, "
                    "or pass --skip-import-check to proceed anyway."
                )

        # Check for dispatched issues in the DB.
        # NOTE: after a normal 'import-state' run, no 'dispatched' rows exist
        # in the DB (legacy dispatched → pending during import).  This guard
        # only catches direct DB inserts made outside of the import path.
        # Operators are solely responsible for draining the shell batch
        # (waiting for it to finish) before running 'import-state'.
        dispatched = conn.execute(
            "SELECT number FROM issues WHERE area = ? AND state = 'dispatched'",
            (area,),
        ).fetchall()
        if dispatched:
            nums = ", ".join(f"#{r['number']}" for r in dispatched)
            raise click.ClickException(
                f"Issues still dispatched for area '{area}': {nums}.\n"
                "Cancel them with 'orchctl control stop <area> --confirm' "
                "before cutting over."
            )

        # Flip the flag and create the sentinel.
        set_config(conn, _legacy_mode_key(area), "false")
        _create_sentinel(area)
    finally:
        conn.close()

    click.echo(f"control [{area}]: cutover complete.")
    click.echo(f"  legacy_mode → false")
    click.echo(f"  sentinel    → {_sentinel_path(area)}")
    click.echo(
        f"\nThe legacy shell orchestrator will refuse to start for area '{area}'."
    )
    click.echo(f"To start orchestration: orchctl reconcile --area {area}")


# ---------------------------------------------------------------------------
# Rollback: orchctl → legacy shell
# ---------------------------------------------------------------------------


@cmd_control.command("rollback")
@click.argument("area", type=click.Choice(["client", "server", "workspace"]))
@click.option("--confirm", is_flag=True, required=True, help="Confirm rolling back to legacy mode.")
@click.pass_context
def cmd_rollback(ctx: click.Context, area: str, confirm: bool) -> None:
    """Roll back AREA to legacy shell orchestrator mode (requires --confirm).

    This reverses a previous 'control cutover':

    \b
      - Sets legacy_mode back to true for this area.
      - Removes the .orchctl-active sentinel so the shell orchestrator can start.

    orchctl will continue to function normally after rollback (existing issues
    remain in the DB), but new dispatches should go through the shell script.

    Recovery validation after rollback:

    \b
      1. orchctl doctor
      2. orchctl status
      3. Manually confirm active workers are healthy.
    """
    conn = get_db(ctx.obj.get("db_path"))
    try:
        _require_ready(conn)

        raw = get_config(conn, _legacy_mode_key(area), "true")
        if raw == "true":
            click.echo(f"control [{area}]: already in legacy mode (no cutover active).")
            return

        # Flip the flag back and remove the sentinel.
        set_config(conn, _legacy_mode_key(area), "true")
        removed = _remove_sentinel(area)
    finally:
        conn.close()

    click.echo(f"control [{area}]: rolled back to legacy mode.")
    click.echo(f"  legacy_mode → true")
    if removed:
        click.echo(f"  sentinel    → removed ({_sentinel_path(area)})")
    else:
        click.echo(f"  sentinel    → not found (already absent)")
    click.echo(
        f"\nThe legacy shell orchestrator may now start for area '{area}'."
    )
    click.echo("Run 'orchctl doctor' to verify state consistency.")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _require_ready(conn: object) -> None:
    """Raise ClickException if DB is not initialised or schema is outdated."""
    from ..db.migrate import current_version as cv

    ver = cv(conn)
    if ver == 0:
        raise click.ClickException(
            "Database not initialised — run `orchctl init` first."
        )
    if ver < LATEST_VERSION:
        raise click.ClickException(
            f"Database schema is out of date (v{ver} < v{LATEST_VERSION}) "
            "— run `orchctl init` to migrate."
        )
