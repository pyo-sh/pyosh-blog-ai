"""orchctl control commands — pause, resume, drain, stop, cancel-attempt, requeue."""

from __future__ import annotations

import click

from ..db import get_db, get_config_bool, set_config
from ..db.schema import LATEST_VERSION
from ..state_machine import apply_issue_transition, apply_issue_transition_tx


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
