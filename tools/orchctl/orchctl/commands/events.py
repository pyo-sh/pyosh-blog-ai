"""orchctl events — view the event log."""

from __future__ import annotations

import json

import click

from ..db import current_version, get_db


@click.group("events")
def cmd_events() -> None:
    """Manage and query the event log."""


@cmd_events.command("list")
@click.option("--area", default=None, help="Filter by area.")
@click.option("--type", "event_type", default=None, help="Filter by event type.")
@click.option("--limit", default=50, show_default=True, help="Maximum rows to return.")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
@click.pass_context
def cmd_events_list(
    ctx: click.Context,
    area: str | None,
    event_type: str | None,
    limit: int,
    as_json: bool,
) -> None:
    """List recent events from the event log."""
    db_path = ctx.obj.get("db_path")
    conn = get_db(db_path)
    try:
        if current_version(conn) == 0:
            raise click.ClickException("Database not initialised — run `orchctl init` first.")

        conditions: list[str] = []
        params: list[object] = []
        if area:
            conditions.append("area = ?")
            params.append(area)
        if event_type:
            conditions.append("event_type = ?")
            params.append(event_type)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        params.append(limit)
        rows = conn.execute(
            f"SELECT id, area, issue_id, event_type, payload, created_at "
            f"FROM events {where} ORDER BY id DESC LIMIT ?",
            params,
        ).fetchall()
    finally:
        conn.close()

    events = [dict(r) for r in rows]

    if as_json:
        click.echo(json.dumps(events, indent=2))
    else:
        if not events:
            click.echo("No events found.")
            return
        for ev in events:
            prefix = f"[{ev['created_at']}] #{ev['id']} {ev['event_type']}"
            area_tag = f" area={ev['area']}" if ev["area"] else ""
            issue_tag = f" issue_id={ev['issue_id']}" if ev["issue_id"] else ""
            click.echo(f"{prefix}{area_tag}{issue_tag}")
