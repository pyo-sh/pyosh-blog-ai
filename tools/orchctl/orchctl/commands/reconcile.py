"""orchctl reconcile — gated reconciliation pass."""

import os
import sqlite3

import click

from ..db import acquire, current_version, get_db, has_active_attempt, release, renew
from ..db.schema import LATEST_VERSION


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
        ver = current_version(conn)
        if ver == 0:
            raise click.ClickException("Database not initialised — run `orchctl init` first.")
        if ver < LATEST_VERSION:
            raise click.ClickException(
                f"Database schema is out of date (v{ver} < v{LATEST_VERSION}) "
                "— run `orchctl init` to migrate."
            )

        pid = os.getpid()
        if not acquire(conn, area, pid):
            click.echo(f"reconcile [{area}]: lease held by another process — skipping.")
            return

        try:
            _run_pass(conn, area, pid, dry_run)
        finally:
            release(conn, area, pid)
    finally:
        conn.close()


def _run_pass(conn: sqlite3.Connection, area: str, pid: int, dry_run: bool) -> None:
    """Execute one reconciliation pass under the area lease."""
    pending = conn.execute(
        "SELECT id, number FROM issues WHERE area = ? AND state = 'pending'",
        (area,),
    ).fetchall()

    if not pending:
        click.echo(f"reconcile [{area}]: no pending issues.")
        return

    for issue in pending:
        if not renew(conn, area, pid):
            click.echo(f"reconcile [{area}]: lease lost mid-pass — aborting.", err=True)
            return
        issue_id = issue["id"]
        number = issue["number"]
        if has_active_attempt(conn, issue_id):
            click.echo(f"reconcile [{area}]: issue #{number} already has an active attempt — skipping.")
            continue
        click.echo(f"reconcile [{area}]: issue #{number} ready to dispatch{' (dry-run)' if dry_run else ''}.")
        if not dry_run:
            pass  # TODO: dispatch issue #number
