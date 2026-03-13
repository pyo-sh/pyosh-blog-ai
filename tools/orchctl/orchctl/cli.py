"""orchctl CLI entry point."""

from pathlib import Path

import click

from .commands.apply_policy import cmd_apply_policy
from .commands.control import cmd_control
from .commands.doctor import cmd_doctor
from .commands.events import cmd_events
from .commands.export import cmd_export
from .commands.import_state import cmd_import_state
from .commands.init import cmd_init
from .commands.merge_gate import cmd_merge_gate
from .commands.notify import cmd_notify
from .commands.reconcile import cmd_reconcile
from .commands.reconcile_all import cmd_reconcile_all
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
cli.add_command(cmd_reconcile_all)
cli.add_command(cmd_status)
cli.add_command(cmd_doctor)
cli.add_command(cmd_control)
cli.add_command(cmd_merge_gate)
cli.add_command(cmd_apply_policy)
cli.add_command(cmd_export)
cli.add_command(cmd_import_state)
cli.add_command(cmd_events)
cli.add_command(cmd_notify)
