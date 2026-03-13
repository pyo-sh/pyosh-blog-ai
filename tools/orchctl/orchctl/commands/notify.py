"""orchctl notify — webhook configuration and test delivery."""

from __future__ import annotations

import json

import click

from ..db import current_version, get_config, get_config_bool, get_config_json, get_db, set_config
from ..events import dispatch_webhook


@click.group("notify")
def cmd_notify() -> None:
    """Configure and test webhook notifications."""


@cmd_notify.command("status")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
@click.pass_context
def cmd_notify_status(ctx: click.Context, as_json: bool) -> None:
    """Show current webhook configuration."""
    db_path = ctx.obj.get("db_path")
    conn = get_db(db_path)
    try:
        if current_version(conn) == 0:
            raise click.ClickException("Database not initialised — run `orchctl init` first.")

        url = get_config(conn, "webhook_url", default="")
        enabled = get_config_bool(conn, "webhook_enabled", default=False)
        events: list[str] = get_config_json(conn, "webhook_events", default=[])  # type: ignore[assignment]
    finally:
        conn.close()

    data = {
        "webhook_url": url,
        "webhook_enabled": enabled,
        "webhook_events": events,
    }

    if as_json:
        click.echo(json.dumps(data, indent=2))
    else:
        status = "enabled" if enabled else "disabled"
        click.echo(f"Webhook: {status}")
        click.echo(f"  URL:    {url or '(not set)'}")
        events_display = ", ".join(events) if events else "(all)"
        click.echo(f"  Events: {events_display}")


@cmd_notify.command("set")
@click.option("--url", default=None, help="Webhook URL (HTTP or HTTPS).")
@click.option("--enable/--disable", default=None, help="Enable or disable the webhook.")
@click.option(
    "--events",
    default=None,
    help=(
        "Comma-separated list of event types to forward. "
        "Use 'all' to forward all events."
    ),
)
@click.pass_context
def cmd_notify_set(
    ctx: click.Context,
    url: str | None,
    enable: bool | None,
    events: str | None,
) -> None:
    """Update webhook configuration."""
    db_path = ctx.obj.get("db_path")
    conn = get_db(db_path)
    try:
        if current_version(conn) == 0:
            raise click.ClickException("Database not initialised — run `orchctl init` first.")

        if url is not None:
            set_config(conn, "webhook_url", url)
            click.echo(f"webhook_url set to: {url or '(cleared)'}")

        if enable is not None:
            set_config(conn, "webhook_enabled", "true" if enable else "false")
            click.echo(f"webhook_enabled set to: {enable}")

        if events is not None:
            if events.lower() == "all":
                event_list: list[str] = []
            else:
                event_list = [e.strip() for e in events.split(",") if e.strip()]
            set_config(conn, "webhook_events", json.dumps(event_list))
            display = ", ".join(event_list) if event_list else "(all)"
            click.echo(f"webhook_events set to: {display}")
    finally:
        conn.close()


@cmd_notify.command("test")
@click.option(
    "--url",
    default=None,
    help="Target URL. Defaults to the configured webhook_url.",
)
@click.pass_context
def cmd_notify_test(ctx: click.Context, url: str | None) -> None:
    """Send a test notification to the configured (or given) webhook URL."""
    db_path = ctx.obj.get("db_path")
    conn = get_db(db_path)
    try:
        if current_version(conn) == 0:
            raise click.ClickException("Database not initialised — run `orchctl init` first.")

        target = url or get_config(conn, "webhook_url", default="")
    finally:
        conn.close()

    if not target:
        raise click.ClickException(
            "No webhook URL configured. "
            "Set one with `orchctl notify set --url <url>` or pass --url."
        )

    payload = json.dumps(
        {"event_type": "test", "area": None, "data": {"message": "orchctl test notification"}},
        ensure_ascii=False,
    )
    ok, detail = dispatch_webhook(target, payload)
    if ok:
        click.echo(f"Delivered: HTTP {detail}")
    else:
        raise click.ClickException(f"Delivery failed: {detail}")
