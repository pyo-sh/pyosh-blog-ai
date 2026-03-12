"""orchctl status — show current orchestrator state."""

import json

import click

from ..db import get_db
from ..db.migrate import _current_version


@click.command("status")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
@click.pass_context
def cmd_status(ctx: click.Context, as_json: bool) -> None:
    """Show issue counts and active attempt summary."""
    db_path = ctx.obj.get("db_path")
    conn = get_db(db_path)
    if _current_version(conn) == 0:
        raise click.ClickException("Database not initialised — run `orchctl init` first.")

    issue_counts: dict[str, int] = {}
    for row in conn.execute(
        "SELECT state, COUNT(*) AS cnt FROM issues GROUP BY state"
    ):
        issue_counts[row["state"]] = row["cnt"]

    active_attempts = [
        dict(row)
        for row in conn.execute(
            "SELECT attempt_id, status, started_at FROM attempts WHERE status = 'running'"
        )
    ]

    conn.close()

    data = {
        "issues": issue_counts,
        "active_attempts": active_attempts,
    }

    if as_json:
        click.echo(json.dumps(data, indent=2))
    else:
        total = sum(issue_counts.values())
        click.echo(f"Issues: {total} total")
        for state, cnt in sorted(issue_counts.items()):
            click.echo(f"  {state}: {cnt}")
        click.echo(f"Active attempts: {len(active_attempts)}")
        for attempt in active_attempts:
            click.echo(f"  {attempt['attempt_id']}  started={attempt['started_at']}")
