"""orchctl reconcile-all — run a reconciliation pass for every area in sequence."""

from __future__ import annotations

import os
import sqlite3

import click

from ..db import (
    acquire,
    current_version,
    get_config_bool,
    get_db,
    release,
)
from ..db.schema import LATEST_VERSION
from ..github import AREA_REPOS
from .reconcile import _load_policy_if_present, _run_pass

_ALL_AREAS: tuple[str, ...] = tuple(AREA_REPOS.keys())


@click.command("reconcile-all")
@click.option(
    "--areas",
    default=",".join(_ALL_AREAS),
    show_default=True,
    help="Comma-separated list of areas to reconcile (default: all known areas).",
)
@click.option("--dry-run", is_flag=True, help="Print actions without executing.")
@click.option(
    "--policy-file",
    "policy_file",
    default=None,
    type=click.Path(exists=True, dir_okay=False),
    help="Override policy YAML file path (default: auto-detect).",
)
@click.pass_context
def cmd_reconcile_all(
    ctx: click.Context,
    areas: str,
    dry_run: bool,
    policy_file: str | None,
) -> None:
    """Run one reconciliation pass for each area, sharing a single DB connection.

    Areas are reconciled sequentially.  Each area acquires its own per-area
    lease before running and releases it afterward.  The global quota
    (global_quota config key) is enforced atomically across all areas because
    all dispatches go through the same SQLite connection, which serializes
    writers.

    Safe to call from a cron job or systemd timer.  Concurrent invocations are
    protected by per-area leases: if an area lease is already held, that area
    is skipped for this run (same behaviour as reconcile --area).

    Use --areas to reconcile a subset:
      orchctl reconcile-all --areas client,server
    """
    area_list = [a.strip() for a in areas.split(",") if a.strip()]
    if not area_list:
        raise click.ClickException("--areas must name at least one area.")

    db_path = ctx.obj.get("db_path")
    conn = get_db(db_path)
    try:
        ver = current_version(conn)
        if ver == 0:
            raise click.ClickException(
                "Database not initialised — run `orchctl init` first."
            )
        if ver < LATEST_VERSION:
            raise click.ClickException(
                f"Database schema is out of date (v{ver} < v{LATEST_VERSION})"
                " — run `orchctl init` to migrate."
            )

        for area in area_list:
            _reconcile_area(conn, area, dry_run, policy_file)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Per-area reconcile helper
# ---------------------------------------------------------------------------


def _reconcile_area(
    conn: sqlite3.Connection,
    area: str,
    dry_run: bool,
    policy_file: str | None,
) -> None:
    """Run one reconciliation pass for *area* under its own lease."""
    # Load policy before acquiring the lease so the pass sees fresh config.
    _load_policy_if_present(conn, area, policy_file, dry_run)

    pid = os.getpid()
    owns_lease = acquire(conn, area, pid)
    if not owns_lease:
        overlap_ok = get_config_bool(conn, "scheduler_overlap", default=False)
        if not overlap_ok:
            click.echo(
                f"reconcile-all [{area}]: lease held by another process"
                " (scheduler_overlap=false) — skipping."
            )
            return
        click.echo(
            f"reconcile-all [{area}]: scheduler_overlap=true"
            " — continuing despite active lease."
        )

    try:
        click.echo(f"reconcile-all [{area}]: starting pass.")
        _run_pass(conn, area, pid, dry_run, owns_lease=owns_lease)
        click.echo(f"reconcile-all [{area}]: pass complete.")
    finally:
        if owns_lease:
            release(conn, area, pid)
