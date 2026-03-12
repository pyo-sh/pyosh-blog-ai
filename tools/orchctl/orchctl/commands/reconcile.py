"""orchctl reconcile — placeholder reconciliation loop stub."""

import click


@click.command("reconcile")
@click.option("--dry-run", is_flag=True, help="Print actions without executing.")
@click.pass_context
def cmd_reconcile(ctx: click.Context, dry_run: bool) -> None:
    """Run one reconciliation pass (stub — full implementation in future issues)."""
    click.echo("reconcile: not yet implemented (Stage 2 follow-up issues).")
    if dry_run:
        click.echo("  (dry-run mode)")
