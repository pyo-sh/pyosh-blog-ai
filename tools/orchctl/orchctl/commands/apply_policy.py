"""orchctl apply-policy — load policy.yaml into the DB config table."""

from __future__ import annotations

from pathlib import Path

import click

from ..db import get_db
from ..db.schema import LATEST_VERSION
from ..policy import apply_policy, find_policy_file, load_policy


@click.command("apply-policy")
@click.option(
    "--policy-file",
    "policy_file",
    default=None,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help=(
        "Path to the policy YAML file. "
        "Defaults to .workspace/orchestrate/policy.yaml or $ORCHCTL_POLICY."
    ),
)
@click.pass_context
def cmd_apply_policy(ctx: click.Context, policy_file: Path | None) -> None:
    """Apply policy.yaml settings to the orchctl DB config.

    Settings are written to the config table and take effect on the next
    reconcile pass.  Keys not present in the policy file are left unchanged.
    """
    conn = get_db(ctx.obj.get("db_path"))
    try:
        from ..db.migrate import current_version

        ver = current_version(conn)
        if ver == 0:
            raise click.ClickException(
                "Database not initialised — run `orchctl init` first."
            )
        if ver < LATEST_VERSION:
            raise click.ClickException(
                f"Database schema is out of date (v{ver} < v{LATEST_VERSION}) "
                "— run `orchctl init` to migrate."
            )

        path = policy_file or find_policy_file()
        if path is None:
            raise click.ClickException(
                "No policy file found. "
                "Create .workspace/orchestrate/policy.yaml or pass --policy-file."
            )

        policy = load_policy(path)
        changed = apply_policy(conn, policy)

        if changed:
            click.echo(f"apply-policy: applied '{path}' — {len(changed)} key(s) updated:")
            for key in changed:
                click.echo(f"  {key}")
        else:
            click.echo(f"apply-policy: '{path}' — no changes (all config already up to date).")
    finally:
        conn.close()
