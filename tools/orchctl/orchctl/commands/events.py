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

        # Each filter is a (predicate_literal, value) pair so the WHERE
        # structure is always composed from fixed string constants and user
        # values are bound via parameters — never interpolated into SQL.
        filters: list[tuple[str, object]] = []
        if area:
            filters.append(("area = ?", area))
        if event_type:
            filters.append(("event_type = ?", event_type))

        where = ("WHERE " + " AND ".join(p for p, _ in filters)) if filters else ""
        params: list[object] = [v for _, v in filters] + [limit]
        rows = conn.execute(
            f"SELECT id, area, issue_id, event_type, payload, created_at "  # noqa: S608
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
