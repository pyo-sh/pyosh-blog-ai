"""orchctl CLI entry point."""

from pathlib import Path

import click

from .commands.doctor import cmd_doctor
from .commands.export import cmd_export
from .commands.init import cmd_init
from .commands.reconcile import cmd_reconcile
from .commands.status import cmd_status


@click.group()
@click.option(
    "--db",
    "db_path",
    envvar="ORCHCTL_DB",
    default=None,
    type=click.Path(dir_okay=False, path_type=Path),
    help="Path to the SQLite database file.",
)
@click.version_option()
@click.pass_context
def cli(ctx: click.Context, db_path: Path | None) -> None:
    """orchctl — orchestrator controller for pyosh-blog."""
    ctx.ensure_object(dict)
    ctx.obj["db_path"] = db_path


cli.add_command(cmd_init)
cli.add_command(cmd_reconcile)
cli.add_command(cmd_status)
cli.add_command(cmd_doctor)
cli.add_command(cmd_export)
