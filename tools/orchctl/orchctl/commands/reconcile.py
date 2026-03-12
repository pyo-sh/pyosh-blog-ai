"""orchctl reconcile — gated reconciliation pass."""

import os

import click

from ..db import acquire, cleanup_stale, current_version, get_db, has_active_attempt, release


@click.command("reconcile")
@click.option("--area", required=True, help="Area to reconcile (client/server/workspace).")
@click.option("--dry-run", is_flag=True, help="Print actions without executing.")
@click.pass_context
def cmd_reconcile(ctx: click.Context, area: str, dry_run: bool) -> None:
    """Run one reconciliation pass for an area.

    Acquires the area lease before processing.  Concurrent calls for the same
    area will exit immediately if the lease is already held.
    """
    db_path = ctx.obj.get("db_path")
    conn = get_db(db_path)
    try:
        if current_version(conn) == 0:
            raise click.ClickException("Database not initialised — run `orchctl init` first.")

        pid = os.getpid()
        if not acquire(conn, area, pid):
            click.echo(f"reconcile [{area}]: lease held by another process — skipping.")
            return

        try:
            _run_pass(conn, area, dry_run)
        finally:
            release(conn, area, pid)
    finally:
        conn.close()


def _run_pass(conn, area: str, dry_run: bool) -> None:
    """Execute one reconciliation pass under the area lease."""
    cleanup_stale(conn)

    pending = conn.execute(
        "SELECT id, number FROM issues WHERE area = ? AND state = 'pending'",
        (area,),
    ).fetchall()

    if not pending:
        click.echo(f"reconcile [{area}]: no pending issues.")
        return

    for issue in pending:
        issue_id = issue["id"]
        number = issue["number"]
        if has_active_attempt(conn, issue_id):
            click.echo(f"reconcile [{area}]: issue #{number} already has an active attempt — skipping.")
            continue
        click.echo(f"reconcile [{area}]: issue #{number} ready to dispatch{' (dry-run)' if dry_run else ''}.")
