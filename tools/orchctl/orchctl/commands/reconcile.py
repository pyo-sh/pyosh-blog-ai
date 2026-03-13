"""orchctl reconcile — idempotent observe/diff/act reconciliation pass."""

from __future__ import annotations

import os
import sqlite3
import uuid
from collections import defaultdict
from typing import Callable

import click

from ..db import (
    acquire,
    count_dispatched,
    current_version,
    get_config,
    get_config_bool,
    get_config_int,
    get_db,
    has_active_attempt,
    release,
    renew,
)
from ..db.schema import LATEST_VERSION
from ..policy import apply_policy, find_policy_file, load_policy
from ..state_machine import apply_issue_transition, apply_issue_transition_tx


@click.command("reconcile")
@click.option(
    "--area",
    required=True,
    type=click.Choice(["client", "server", "workspace"]),
    help="Area to reconcile.",
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
def cmd_reconcile(
    ctx: click.Context, area: str, dry_run: bool, policy_file: str | None
) -> None:
    """Run one idempotent reconciliation pass for an area.

    Observe → Diff → Act:
      1. Load policy.yaml if present (syncs config from file).
      2. Acquire area lease (scheduler-overlap safety).
      3. Observe: read issue/attempt state + config from DB.
      4. Diff: determine actions needed (dispatch, mark-complete, unblock, cleanup).
      5. Act: execute actions under admission control.
      6. Release lease.

    Safe to call from systemd timer or cron — concurrent invocations for the
    same area exit immediately if the lease is already held.
    """
    db_path = ctx.obj.get("db_path")
    conn = get_db(db_path)
    try:
        ver = current_version(conn)
        if ver == 0:
            raise click.ClickException("Database not initialised — run `orchctl init` first.")
        if ver < LATEST_VERSION:
            raise click.ClickException(
                f"Database schema is out of date (v{ver} < v{LATEST_VERSION}) "
                "— run `orchctl init` to migrate."
            )

        # Load policy.yaml on every reconcile pass so changes take effect immediately.
        _load_policy_if_present(conn, area, policy_file, dry_run)

        pid = os.getpid()
        if not acquire(conn, area, pid):
            overlap_ok = get_config_bool(conn, "scheduler_overlap", default=False)
            if not overlap_ok:
                click.echo(
                    f"reconcile [{area}]: lease held by another process"
                    " (scheduler_overlap=false) — skipping."
                )
            else:
                click.echo(f"reconcile [{area}]: lease held by another process — skipping.")
            return

        try:
            _run_pass(conn, area, pid, dry_run)
        finally:
            release(conn, area, pid)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Policy loading
# ---------------------------------------------------------------------------


def _load_policy_if_present(
    conn: sqlite3.Connection,
    area: str,
    policy_file: str | None,
    dry_run: bool,
) -> None:
    """Attempt to load policy.yaml and sync to DB config."""
    from pathlib import Path

    path = Path(policy_file) if policy_file else find_policy_file()
    if path is None:
        return
    try:
        policy = load_policy(path)
        changed = apply_policy(conn, policy) if not dry_run else []
        if changed:
            click.echo(
                f"reconcile [{area}]: policy '{path}' applied"
                f" — {len(changed)} config key(s) updated."
            )
    except Exception as exc:  # noqa: BLE001 — policy errors must not abort reconcile
        click.echo(
            f"reconcile [{area}]: warning — could not load policy '{path}': {exc}",
            err=True,
        )


# ---------------------------------------------------------------------------
# Reconcile pass
# ---------------------------------------------------------------------------


def _run_pass(
    conn: sqlite3.Connection,
    area: str,
    pid: int,
    dry_run: bool,
    dispatch_fn: Callable[[str, int, int, str], None] | None = None,
) -> None:
    """Execute one full reconciliation pass under the area lease.

    Each sub-pass returns True on success or False if the lease was lost.
    On lease loss, subsequent sub-passes are skipped.

    Args:
        conn: Open SQLite connection.
        area: Area being reconciled.
        pid: PID of the current process (lease holder).
        dry_run: If True, log actions without modifying state.
        dispatch_fn: Optional callback invoked when an issue is dispatched.
            Signature: (area, issue_id, issue_number, attempt_id) -> None.
            Used in tests to observe or replace the actual launch logic.
    """
    issues_by_state = _observe_issues(conn, area)
    config = _observe_config(conn, area)

    if not _mark_complete_pass(conn, area, pid, dry_run, issues_by_state):
        return
    if not _unblock_pass(conn, area, pid, dry_run, issues_by_state):
        return
    _dispatch_pass(conn, area, pid, dry_run, issues_by_state, config, dispatch_fn)


# ---------------------------------------------------------------------------
# Observe helpers
# ---------------------------------------------------------------------------


def _observe_issues(
    conn: sqlite3.Connection, area: str
) -> dict[str, list[sqlite3.Row]]:
    """Return all issues for the area grouped by state."""
    rows = conn.execute(
        "SELECT id, number, state, dependency_type, retry_count FROM issues WHERE area = ?",
        (area,),
    ).fetchall()
    by_state: dict[str, list[sqlite3.Row]] = defaultdict(list)
    for row in rows:
        by_state[row["state"]].append(row)
    return dict(by_state)


def _observe_config(conn: sqlite3.Connection, area: str) -> dict:
    """Read relevant config keys from the DB."""
    return {
        "max_concurrent": get_config_int(conn, "max_concurrent", default=4),
        "max_open_pr": get_config_int(conn, "max_open_pr", default=2),
        "drain_mode": get_config_bool(conn, "drain_mode", default=False),
        "area_paused": get_config_bool(conn, f"{area}.paused", default=False),
        "repo_allowlist": get_config(conn, "repo_allowlist", default=""),
        "area_repo": get_config(conn, f"{area}.repo", default=""),
        "max_concurrent_repair": get_config_int(conn, "max_concurrent_repair", default=1),
    }


# ---------------------------------------------------------------------------
# Mark-complete pass
# ---------------------------------------------------------------------------


def _mark_complete_pass(
    conn: sqlite3.Connection,
    area: str,
    pid: int,
    dry_run: bool,
    issues_by_state: dict,
) -> bool:
    """Transition dispatched issues to completed/failed-terminal based on attempt status.

    Returns True on success, False if the lease was lost (caller should abort).
    """
    dispatched = issues_by_state.get("dispatched", [])
    for issue in dispatched:
        if not renew(conn, area, pid):
            click.echo(f"reconcile [{area}]: lease lost mid-pass — aborting.", err=True)
            return False

        issue_id = issue["id"]
        number = issue["number"]

        latest = conn.execute(
            """
            SELECT status FROM attempts
            WHERE issue_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (issue_id,),
        ).fetchone()

        if latest is None:
            continue

        status = latest["status"]
        if status == "completed":
            click.echo(
                f"reconcile [{area}]: issue #{number} attempt completed"
                f" → marking completed{' (dry-run)' if dry_run else ''}."
            )
            if not dry_run:
                apply_issue_transition(conn, issue_id, "completed")
        elif status in ("failed", "timed-out"):
            click.echo(
                f"reconcile [{area}]: issue #{number} attempt {status}"
                f" → marking failed-terminal{' (dry-run)' if dry_run else ''}."
            )
            if not dry_run:
                apply_issue_transition(conn, issue_id, "failed-terminal")

    return True


# ---------------------------------------------------------------------------
# Unblock pass
# ---------------------------------------------------------------------------


def _unblock_pass(
    conn: sqlite3.Connection,
    area: str,
    pid: int,
    dry_run: bool,
    issues_by_state: dict,
) -> bool:
    """Transition blocked issues to pending when their dependencies are done.

    Issues with dependency_type='none' are unblocked immediately (no deps to
    check).  Issues with soft or hard deps require a dedicated deps table for
    cross-area resolution, which is deferred to a future PR.

    Returns True on success, False if the lease was lost (caller should abort).
    """
    blocked = issues_by_state.get("blocked", [])
    for issue in blocked:
        if not renew(conn, area, pid):
            click.echo(f"reconcile [{area}]: lease lost mid-pass — aborting.", err=True)
            return False

        number = issue["number"]
        dep_type = issue["dependency_type"]

        if dep_type == "none":
            click.echo(
                f"reconcile [{area}]: issue #{number} blocked with no deps"
                f" → unblocking{' (dry-run)' if dry_run else ''}."
            )
            if not dry_run:
                apply_issue_transition(conn, issue["id"], "pending")
        else:
            click.echo(
                f"reconcile [{area}]: issue #{number} blocked"
                f" (dependency check deferred — requires deps table)."
            )

    return True


# ---------------------------------------------------------------------------
# Dispatch pass (admission control)
# ---------------------------------------------------------------------------


def _dispatch_pass(
    conn: sqlite3.Connection,
    area: str,
    pid: int,
    dry_run: bool,
    issues_by_state: dict,
    config: dict,
    dispatch_fn: Callable[[str, int, int, str], None] | None = None,
) -> None:
    """Dispatch pending issues subject to admission control.

    Admission gates (first failure stops dispatch for remaining issues):
      1. Drain mode: no new dispatches when enabled globally.
      2. Area pause: no new dispatches when area is paused.
      3. Repo allowlist guardrail: area repo must be in the allowlist.
      4. maxConcurrent: per-area limit on issues in 'dispatched' state.
      5. maxOpenPR: global limit on issues in 'dispatched' state across all areas.
         Enforced atomically inside _record_dispatch to prevent TOCTOU races
         when multiple area reconcilers run concurrently.
      6. maxConcurrentRepair: cap on concurrently dispatched retry attempts.
      7. Per-issue: skip if an active attempt already exists.
    """
    if config["drain_mode"]:
        click.echo(f"reconcile [{area}]: drain mode active — no new dispatches.")
        return

    if config["area_paused"]:
        click.echo(f"reconcile [{area}]: area is paused — no new dispatches.")
        return

    # Repo allowlist guardrail: if configured, area repo must be in the list.
    repo_allowlist_raw = config["repo_allowlist"]
    if repo_allowlist_raw:
        allowed_repos = {r.strip() for r in repo_allowlist_raw.split(",") if r.strip()}
        area_repo = config["area_repo"].strip()
        if area_repo and area_repo not in allowed_repos:
            click.echo(
                f"reconcile [{area}]: guardrail — repo '{area_repo}' not in allowlist"
                " — no dispatches."
            )
            return

    max_concurrent = config["max_concurrent"]
    max_open_pr = config["max_open_pr"]
    max_repair = config["max_concurrent_repair"]

    pending = issues_by_state.get("pending", [])
    if not pending:
        click.echo(f"reconcile [{area}]: no pending issues.")
        return

    for issue in pending:
        if not renew(conn, area, pid):
            click.echo(f"reconcile [{area}]: lease lost mid-pass — aborting.", err=True)
            return

        # Optimistic pre-checks (for fast exit and user feedback).
        # The maxOpenPR cap is also enforced atomically inside _record_dispatch.
        active_area = count_dispatched(conn, area)
        if active_area >= max_concurrent:
            click.echo(
                f"reconcile [{area}]: maxConcurrent={max_concurrent} reached"
                " — no more dispatches."
            )
            return

        active_global = count_dispatched(conn, None)
        if active_global >= max_open_pr:
            click.echo(
                f"reconcile [{area}]: maxOpenPR={max_open_pr} reached"
                " — no more dispatches."
            )
            return

        # maxConcurrentRepair: limit simultaneously dispatched retry attempts.
        retry_count = issue["retry_count"] if "retry_count" in issue.keys() else 0
        if retry_count > 0:
            active_repairs = _count_active_repairs(conn, area)
            if active_repairs >= max_repair:
                click.echo(
                    f"reconcile [{area}]: issue #{issue['number']} is a repair attempt"
                    f" (retry_count={retry_count}); maxConcurrentRepair={max_repair} reached"
                    " — skipping."
                )
                continue

        issue_id = issue["id"]
        number = issue["number"]

        if has_active_attempt(conn, issue_id):
            click.echo(
                f"reconcile [{area}]: issue #{number} already has an active attempt"
                " — skipping."
            )
            continue

        attempt_id = f"issue-{number}-a{uuid.uuid4().hex[:8]}"
        click.echo(
            f"reconcile [{area}]: issue #{number} ready to dispatch"
            f"{' (dry-run)' if dry_run else ''}."
        )
        if not dry_run:
            dispatched = _record_dispatch(conn, issue_id, attempt_id, max_open_pr)
            if not dispatched:
                # A concurrent reconciler filled the global cap between our
                # optimistic check and the atomic insert.
                click.echo(
                    f"reconcile [{area}]: maxOpenPR={max_open_pr} reached"
                    " — global cap enforced concurrently, stopping."
                )
                return
            if dispatch_fn is not None:
                dispatch_fn(area, issue_id, number, attempt_id)


def _count_active_repairs(conn: sqlite3.Connection, area: str) -> int:
    """Count dispatched issues in the area that have retry_count > 0."""
    row = conn.execute(
        "SELECT COUNT(*) FROM issues WHERE area = ? AND state = 'dispatched' AND retry_count > 0",
        (area,),
    ).fetchone()
    return row[0]


def _record_dispatch(
    conn: sqlite3.Connection, issue_id: int, attempt_id: str, max_open_pr: int
) -> bool:
    """Create a running attempt and transition the issue to 'dispatched' atomically.

    The attempt INSERT is conditional on the global dispatched count being below
    max_open_pr.  SQLite serializes writers, so this check-and-insert is
    race-free: a concurrent reconciler's INSERT will either precede or follow
    this one — never interleave — ensuring the cap is never silently exceeded.

    The issue state transition uses apply_issue_transition_tx (no intermediate
    commit) so both the attempt INSERT and the state UPDATE are committed
    together, preventing a crash from leaving the issue stuck in 'pending' with
    a dangling 'running' attempt.

    Returns True if the dispatch was recorded, False if the global cap was
    already reached by a concurrent reconciler.
    """
    cur = conn.execute(
        """
        INSERT INTO attempts (attempt_id, issue_id, status)
        SELECT ?, ?, 'running'
        WHERE (SELECT COUNT(*) FROM issues WHERE state = 'dispatched') < ?
        """,
        (attempt_id, issue_id, max_open_pr),
    )
    if cur.rowcount == 0:
        return False
    try:
        apply_issue_transition_tx(conn, issue_id, "dispatched")
    except Exception:
        conn.rollback()
        raise
    conn.commit()
    return True
