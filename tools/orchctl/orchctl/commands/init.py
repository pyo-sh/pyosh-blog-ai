"""orchctl init — initialize the database."""

import click

from ..db import init_db


@click.command("init")
@click.pass_context
def cmd_init(ctx: click.Context) -> None:
    """Initialize the orchctl database and apply schema migrations."""
    db_path = ctx.obj.get("db_path")
    conn, version = init_db(db_path)
    conn.close()
    click.echo(f"Database initialized (schema v{version}).")
