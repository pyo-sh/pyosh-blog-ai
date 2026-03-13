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
    get_config_json,
    get_db,
    has_active_attempt,
    release,
    renew,
)
from ..db.schema import LATEST_VERSION
from ..github import AREA_REPOS, GitHubError, GitHubIssue, list_open_issues
from ..models import ISSUE_TRANSITIONS, IssueState, TERMINAL_ISSUE_STATES
from ..state_machine import apply_issue_transition, apply_issue_transition_tx


@click.command("reconcile")
@click.option(
    "--area",
    required=True,
    type=click.Choice(["client", "server", "workspace"]),
    help="Area to reconcile.",
)
@click.option("--dry-run", is_flag=True, help="Print actions without executing.")
@click.pass_context
def cmd_reconcile(ctx: click.Context, area: str, dry_run: bool) -> None:
    """Run one idempotent reconciliation pass for an area.

    Observe → Diff → Act:
      1. Acquire area lease (scheduler-overlap safety).
      2. Observe: read issue/attempt state + config from DB.
      3. Diff: determine actions needed (dispatch, mark-complete, unblock, cleanup).
      4. Act: execute actions under admission control.
      5. Release lease.

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

        pid = os.getpid()
        if not acquire(conn, area, pid):
            click.echo(f"reconcile [{area}]: lease held by another process — skipping.")
            return

        try:
            _run_pass(conn, area, pid, dry_run)
        finally:
            release(conn, area, pid)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Reconcile pass
# ---------------------------------------------------------------------------

def _run_pass(
    conn: sqlite3.Connection,
    area: str,
    pid: int,
    dry_run: bool,
    dispatch_fn: Callable[[str, int, int, str], None] | None = None,
    gh_list_fn: Callable[..., list[GitHubIssue]] | None = None,
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
        gh_list_fn: Optional override for the GitHub issue list call.
            Signature matches ``list_open_issues``.  Used in tests to inject
            a fake issue list without hitting the network.
    """
    issues_by_state = _observe_issues(conn, area)
    config = _observe_config(conn)

    if not _discovery_pass(conn, area, pid, dry_run, config, gh_list_fn):
        return
    # Re-read after discovery so newly-enqueued issues appear in pending.
    issues_by_state = _observe_issues(conn, area)
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
        "SELECT id, number, state, dependency_type FROM issues WHERE area = ?",
        (area,),
    ).fetchall()
    by_state: dict[str, list[sqlite3.Row]] = defaultdict(list)
    for row in rows:
        by_state[row["state"]].append(row)
    return dict(by_state)


def _observe_config(conn: sqlite3.Connection) -> dict:
    """Read relevant config keys from the DB."""
    return {
        "max_concurrent": get_config_int(conn, "max_concurrent", default=4),
        "max_open_pr": get_config_int(conn, "max_open_pr", default=2),
        "drain_mode": get_config_bool(conn, "drain_mode", default=False),
        "discovery_enabled": get_config_bool(conn, "discovery_enabled", default=False),
        "scope_include_labels": get_config_json(conn, "scope_include_labels", default=[]),
        "scope_exclude_labels": get_config_json(conn, "scope_exclude_labels", default=[]),
        "scope_milestone": get_config(conn, "scope_milestone", default=""),
        "scope_allow_unassigned": get_config_bool(conn, "scope_allow_unassigned", default=True),
    }


# ---------------------------------------------------------------------------
# Discovery pass
# ---------------------------------------------------------------------------

# Derived from ISSUE_TRANSITIONS: terminal states with a -> pending outgoing edge.
# Computed at import time so it stays automatically in sync with models.py.
_REOPEN_STATES: frozenset[str] = frozenset(
    s.value
    for s, targets in ISSUE_TRANSITIONS.items()
    if s in TERMINAL_ISSUE_STATES and IssueState.PENDING in targets
)


def _discovery_pass(
    conn: sqlite3.Connection,
    area: str,
    pid: int,
    dry_run: bool,
    config: dict,
    gh_list_fn: Callable[..., list[GitHubIssue]] | None = None,
) -> bool:
    """Query GitHub for open issues and enqueue new or re-opened ones.

    Skipped when ``discovery_enabled`` is False.

    Returns True on success, False if the lease was lost (caller should abort).
    """
    if not config["discovery_enabled"]:
        return True

    repo = AREA_REPOS.get(area)
    if not repo:
        click.echo(
            f"reconcile [{area}]: discovery skipped — no GitHub repo mapping.",
            err=True,
        )
        return True

    _list_fn = gh_list_fn or list_open_issues
    try:
        gh_issues = _list_fn(
            repo,
            include_labels=config["scope_include_labels"],
            exclude_labels=config["scope_exclude_labels"],
            milestone=config["scope_milestone"],
            allow_unassigned=config["scope_allow_unassigned"],
        )
    except GitHubError as exc:
        click.echo(f"reconcile [{area}]: discovery error — {exc}", err=True)
        return True  # non-fatal; continue with existing queue

    # Renew lease every 50 issues rather than on every iteration to limit
    # lease-table write churn when processing large backlogs.
    _RENEW_EVERY = 50
    for idx, gh_issue in enumerate(gh_issues):
        if idx % _RENEW_EVERY == 0 and not renew(conn, area, pid):
            click.echo(
                f"reconcile [{area}]: lease lost during discovery — aborting.",
                err=True,
            )
            return False
        _enqueue_or_reopen(conn, area, gh_issue.number, dry_run)

    return True


def _enqueue_or_reopen(
    conn: sqlite3.Connection,
    area: str,
    number: int,
    dry_run: bool,
) -> None:
    """Insert a new issue as pending, or re-enqueue a reopened terminal issue."""
    row = conn.execute(
        "SELECT id, state FROM issues WHERE area = ? AND number = ?",
        (area, number),
    ).fetchone()

    if row is None:
        click.echo(
            f"reconcile [{area}]: discovered issue #{number}"
            f" → enqueueing as pending{' (dry-run)' if dry_run else ''}."
        )
        if not dry_run:
            conn.execute(
                "INSERT INTO issues (area, number, state) VALUES (?, ?, 'pending')",
                (area, number),
            )
            conn.commit()
        return

    state = row["state"]
    if state in _REOPEN_STATES:
        click.echo(
            f"reconcile [{area}]: issue #{number} reopened (was {state})"
            f" → re-enqueueing as pending{' (dry-run)' if dry_run else ''}."
        )
        if not dry_run:
            apply_issue_transition(conn, row["id"], "pending")


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
      1. Drain mode: no new dispatches when enabled.
      2. maxConcurrent: per-area limit on issues in 'dispatched' state.
      3. maxOpenPR: global limit on issues in 'dispatched' state across all areas.
         Enforced atomically inside _record_dispatch to prevent TOCTOU races
         when multiple area reconcilers run concurrently.
      4. Per-issue: skip if an active attempt already exists.
    """
    if config["drain_mode"]:
        click.echo(f"reconcile [{area}]: drain mode active — no new dispatches.")
        return

    max_concurrent = config["max_concurrent"]
    max_open_pr = config["max_open_pr"]

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
