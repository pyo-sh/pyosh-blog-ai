"""orchctl reconcile — idempotent observe/diff/act reconciliation pass."""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Callable

import click

from ..db import (
    acquire,
    count_dispatched,
    current_version,
    get_config,
    get_config_bool,
    get_config_float,
    get_config_int,
    get_config_json,
    get_db,
    has_active_attempt,
    release,
    renew,
)
from ..db.schema import LATEST_VERSION
from ..github import (
    AREA_REPOS,
    GitHubError,
    GitHubIssue,
    create_issue,
    fetch_ci_logs,
    get_pr_branch,
    list_open_issues,
    post_issue_comment,
)
from ..failure_classifier import classify, next_action_for_class, record_failure_class
from ..models import (
    ISSUE_TRANSITIONS,
    DependencyType,
    FailureClass,
    IssueState,
    NextAction,
    TERMINAL_ISSUE_STATES,
)
from ..policy import apply_policy, find_policy_file, load_policy
from ..heartbeat import check_stall
from ..state_machine import (
    apply_attempt_transition,
    apply_attempt_transition_tx,
    apply_issue_transition,
    apply_issue_transition_tx,
)


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
        owns_lease = acquire(conn, area, pid)
        if not owns_lease:
            overlap_ok = get_config_bool(conn, "scheduler_overlap", default=False)
            if not overlap_ok:
                click.echo(
                    f"reconcile [{area}]: lease held by another process"
                    " (scheduler_overlap=false) — skipping."
                )
                return
            click.echo(
                f"reconcile [{area}]: scheduler_overlap=true — continuing despite active lease."
            )

        try:
            _run_pass(conn, area, pid, dry_run, owns_lease=owns_lease)
        finally:
            if owns_lease:
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
    owns_lease: bool = True,
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
        owns_lease: True if this process holds the area lease. When False
            (scheduler_overlap=true, second reconciler), renew() calls are
            skipped to avoid mid-pass abort from a lease never acquired.
        gh_list_fn: Optional override for the GitHub issue list call.
            Signature matches ``list_open_issues``.  Used in tests to inject
            a fake issue list without hitting the network.
    """
    issues_by_state = _observe_issues(conn, area)
    config = _observe_config(conn, area)

    if not _discovery_pass(conn, area, pid, dry_run, config, gh_list_fn):
        return
    # Re-read after discovery so newly-enqueued issues appear in pending.
    issues_by_state = _observe_issues(conn, area)
    if not _mark_complete_pass(conn, area, pid, dry_run, issues_by_state, owns_lease):
        return
    if not _heartbeat_pass(conn, area, pid, dry_run, issues_by_state, owns_lease):
        return
    if not _unblock_pass(conn, area, pid, dry_run, issues_by_state, owns_lease):
        return
    _dispatch_pass(conn, area, pid, dry_run, issues_by_state, config, dispatch_fn, owns_lease)


# ---------------------------------------------------------------------------
# Observe helpers
# ---------------------------------------------------------------------------


def _observe_issues(
    conn: sqlite3.Connection, area: str
) -> dict[str, list[sqlite3.Row]]:
    """Return all issues for the area grouped by state."""
    rows = conn.execute(
        "SELECT id, number, state, dependency_type, retry_count, priority, created_at"
        " FROM issues WHERE area = ?",
        (area,),
    ).fetchall()
    by_state: dict[str, list[sqlite3.Row]] = defaultdict(list)
    for row in rows:
        by_state[row["state"]].append(row)
    return dict(by_state)


def _observe_config(conn: sqlite3.Connection, area: str) -> dict:
    """Read relevant config keys from the DB."""
    # max_open_pr is the stored config key for the global concurrent-dispatch cap.
    # Policy YAML accepts both 'global_max' and 'global_quota' as synonyms;
    # both write to max_open_pr so the single source of truth is preserved.
    global_quota = get_config_int(conn, "max_open_pr", default=2)
    return {
        "max_concurrent": get_config_int(conn, "max_concurrent", default=4),
        "global_quota": global_quota,
        "max_open_pr": global_quota,  # legacy alias kept for callers
        "drain_mode": get_config_bool(conn, "drain_mode", default=False),
        "area_paused": get_config_bool(conn, f"{area}.paused", default=False),
        "repo_allowlist": get_config(conn, "repo_allowlist", default=""),
        "area_repo": get_config(conn, f"{area}.repo", default=""),
        "max_concurrent_repair": get_config_int(conn, "max_concurrent_repair", default=1),
        "discovery_enabled": get_config_bool(conn, "discovery_enabled", default=False),
        "scope_include_labels": get_config_json(conn, "scope_include_labels", default=[]),
        "scope_exclude_labels": get_config_json(conn, "scope_exclude_labels", default=[]),
        "scope_milestone": get_config(conn, "scope_milestone", default=""),
        "scope_allow_unassigned": get_config_bool(conn, "scope_allow_unassigned", default=True),
        "scheduling_priority_weight": get_config_float(conn, "scheduling_priority_weight", default=1.0),
        "scheduling_age_weight": get_config_float(conn, "scheduling_age_weight", default=0.1),
        "scheduling_retry_weight": get_config_float(conn, "scheduling_retry_weight", default=1.0),
        "max_awaiting_merge": get_config_int(conn, "max_awaiting_merge", default=0),
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
        _enqueue_or_reopen(conn, area, gh_issue.number, dry_run, priority=gh_issue.priority)

    return True


def _enqueue_or_reopen(
    conn: sqlite3.Connection,
    area: str,
    number: int,
    dry_run: bool,
    priority: int = 0,
) -> None:
    """Insert a new issue as pending, or re-enqueue a reopened terminal issue."""
    row = conn.execute(
        "SELECT id, state FROM issues WHERE area = ? AND number = ?",
        (area, number),
    ).fetchone()

    if row is None:
        click.echo(
            f"reconcile [{area}]: discovered issue #{number}"
            f" (priority={priority})"
            f" → enqueueing as pending{' (dry-run)' if dry_run else ''}."
        )
        if not dry_run:
            conn.execute(
                "INSERT INTO issues (area, number, state, priority) VALUES (?, ?, 'pending', ?)",
                (area, number, priority),
            )
            conn.commit()
        return

    state = row["state"]
    if state in _REOPEN_STATES:
        click.echo(
            f"reconcile [{area}]: issue #{number} reopened (was {state})"
            f" (priority={priority})"
            f" → re-enqueueing as pending{' (dry-run)' if dry_run else ''}."
        )
        if not dry_run:
            conn.execute(
                "UPDATE issues SET priority = ? WHERE id = ?",
                (priority, row["id"]),
            )
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
    owns_lease: bool = True,
) -> bool:
    """Transition dispatched issues based on attempt outcome.

    Successful attempts move to completed.  Failed/timed-out attempts are
    classified into one of 10 FailureClass values; the resulting NextAction
    determines the new issue state:
      - retry / repair: re-enqueue as pending (if retry budget allows)
      - escalate:       needs-human
      - pause:          blocked-external

    Returns True on success, False if the lease was lost (caller should abort).
    """
    dispatched = issues_by_state.get("dispatched", [])
    for issue in dispatched:
        if owns_lease and not renew(conn, area, pid):
            click.echo(f"reconcile [{area}]: lease lost mid-pass — aborting.", err=True)
            return False

        issue_id = issue["id"]
        number = issue["number"]
        retry_count = issue["retry_count"]

        latest = conn.execute(
            """
            SELECT attempt_id, status, terminal_json FROM attempts
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
            attempt_id = latest["attempt_id"]
            terminal_json = latest["terminal_json"]

            # classify() is pure — call it once for both dry-run output and DB writes.
            failure_class = classify(status, terminal_json)
            next_action = next_action_for_class(failure_class)
            if not dry_run:
                record_failure_class(conn, issue_id, attempt_id, failure_class)

            new_state = _next_action_to_state(
                conn, area, issue_id, number, retry_count, failure_class, next_action,
                dry_run, terminal_json=terminal_json,
                pid=pid, owns_lease=owns_lease,
            )
            click.echo(
                f"reconcile [{area}]: issue #{number} attempt {status}"
                f" (class={failure_class.value}, next={next_action.value})"
                f" → {new_state}{' (dry-run)' if dry_run else ''}."
            )
            if not dry_run:
                apply_issue_transition(conn, issue_id, new_state)

    return True


def _next_action_to_state(
    conn: sqlite3.Connection,
    area: str,
    issue_id: int,
    number: int,
    retry_count: int,
    failure_class: FailureClass,
    next_action: NextAction,
    dry_run: bool = False,
    *,
    terminal_json: str | None = None,
    pid: int = 0,
    owns_lease: bool = False,
) -> str:
    """Map next_action to an IssueState string, enforcing per-class retry budgets."""
    if next_action in (NextAction.RETRY, NextAction.REPAIR):
        budget_by_class = get_config_json(conn, "retry_budget_by_class", default={})
        raw_budget = budget_by_class.get(failure_class.value, budget_by_class.get("default", 1))
        try:
            budget = int(raw_budget)
        except (TypeError, ValueError):
            budget = 1
        if retry_count < budget:
            if not dry_run:
                conn.execute(
                    "UPDATE issues SET retry_count = retry_count + 1 WHERE id = ?",
                    (issue_id,),
                )
                _post_retry_comment(area, number, retry_count + 1, budget, failure_class)
                # CI repair playbook: collect logs and post repair context.
                # Called here (within-budget branch) so the comment is only sent
                # when a repair attempt will actually be re-queued, not on the
                # final exhausted failure.
                if failure_class == FailureClass.DETERMINISTIC_TEST_FAILURE:
                    _run_ci_repair_playbook(
                        conn, area, number, terminal_json,
                        pid=pid, owns_lease=owns_lease,
                    )
                if failure_class == FailureClass.GIT_CONFLICT:
                    _run_git_rebase_playbook(
                        conn, area, number, terminal_json,
                        pid=pid, owns_lease=owns_lease,
                    )
            click.echo(
                f"reconcile [{area}]: issue #{number}"
                f" retry {retry_count + 1}/{budget} scheduled{' (dry-run)' if dry_run else ''}."
            )
            return IssueState.PENDING.value
        click.echo(
            f"reconcile [{area}]: issue #{number}"
            f" retry budget exhausted ({retry_count}/{budget}) — escalating to needs-human"
            f"{' (dry-run)' if dry_run else ''}."
        )
        if not dry_run:
            _post_budget_exhausted_comment(area, number, retry_count, budget, failure_class)
            # CI repair playbook: create blocker issue on repeated test failure.
            if failure_class == FailureClass.DETERMINISTIC_TEST_FAILURE:
                _create_ci_blocker_issue(conn, area, issue_id, number, retry_count, terminal_json)
            # Git conflict playbook: create blocker issue on exhausted rebase budget.
            if failure_class == FailureClass.GIT_CONFLICT:
                _create_git_rebase_blocker_issue(conn, area, issue_id, number, retry_count, terminal_json)
        return IssueState.NEEDS_HUMAN.value

    if next_action == NextAction.PAUSE:
        return IssueState.BLOCKED_EXTERNAL.value

    # ESCALATE (default)
    return IssueState.NEEDS_HUMAN.value


def _post_retry_comment(
    area: str,
    number: int,
    attempt_num: int,
    budget: int,
    failure_class: FailureClass,
) -> None:
    """Post a retry-scheduled comment to the GitHub issue. Non-fatal on error."""
    repo = AREA_REPOS.get(area)
    if not repo:
        return
    body = (
        f"**Auto-retry scheduled** (attempt {attempt_num}/{budget})\n\n"
        f"- Failure class: `{failure_class.value}`\n"
        f"- Remaining budget: {budget - attempt_num}"
    )
    post_issue_comment(repo, number, body)


def _post_budget_exhausted_comment(
    area: str,
    number: int,
    retry_count: int,
    budget: int,
    failure_class: FailureClass,
) -> None:
    """Post a budget-exhausted escalation comment to the GitHub issue. Non-fatal on error."""
    repo = AREA_REPOS.get(area)
    if not repo:
        return
    body = (
        f"**Retry budget exhausted** — escalating to `needs-human`\n\n"
        f"- Failure class: `{failure_class.value}`\n"
        f"- Attempts made: {retry_count}/{budget}\n\n"
        "Human review required."
    )
    post_issue_comment(repo, number, body)


# ---------------------------------------------------------------------------
# CI repair playbook helpers
# ---------------------------------------------------------------------------


def _run_ci_repair_playbook(
    conn: sqlite3.Connection,
    area: str,
    number: int,
    terminal_json: str | None,
    *,
    pid: int = 0,
    owns_lease: bool = False,
) -> None:
    """Collect CI logs and post a repair context comment on the issue.

    Called when a ``deterministic_test_failure`` attempt is about to be
    re-queued as a repair attempt.  Errors are non-fatal.

    Steps:
    1. Parse PR number from terminal_json.
    2. Resolve the PR's head branch via gh CLI.
    3. Renew the area lease before the log-fetch gh call (prevents expiry
       from the cumulative timeout of sequential gh subprocesses).
    4. Fetch the latest failed workflow run logs for that branch.
    5. Post a repair context comment with the log tail.
    """
    repo = AREA_REPOS.get(area)
    if not repo:
        return

    pr_number: int | None = None
    if terminal_json:
        try:
            tj = json.loads(terminal_json)
            raw_pr = tj.get("prNumber")
            if raw_pr and raw_pr != "null":
                pr_number = int(raw_pr)
        except (ValueError, TypeError, AttributeError):
            pass

    ci_logs: str | None = None
    if pr_number:
        branch = get_pr_branch(repo, pr_number)
        # Renew lease before the second blocking gh call (log fetch) so that
        # the cumulative timeout of get_pr_branch + fetch_ci_logs does not
        # push the total elapsed time past the lease TTL.
        if owns_lease and pid:
            renew(conn, area, pid)
        if branch:
            ci_logs = fetch_ci_logs(repo, branch)

    log_section = (
        f"\n\n**CI log tail:**\n```\n{ci_logs}\n```"
        if ci_logs
        else "\n\n*(CI logs unavailable — check the workflow run directly)*"
    )
    pr_ref = f" (PR #{pr_number})" if pr_number else ""
    body = (
        f"**CI repair attempt scheduled**{pr_ref}\n\n"
        f"- Failure class: `deterministic_test_failure`\n"
        f"- This repair worker will receive the CI failure context below."
        f"{log_section}"
    )
    try:
        post_issue_comment(repo, number, body)
    except Exception as exc:  # noqa: BLE001
        click.echo(f"reconcile [{area}]: repair comment failed (#{number}): {exc}", err=True)


def _create_ci_blocker_issue(
    conn: sqlite3.Connection,
    area: str,
    issue_id: int,
    number: int,
    retry_count: int,
    terminal_json: str | None,
) -> None:
    """Create a blocker GitHub issue after repeated deterministic test failures.

    The blocker issue includes the failure history, CI log links from all
    attempts, and a reference to the original issue.  Non-fatal on error.
    """
    repo = AREA_REPOS.get(area)
    if not repo:
        return

    # Collect failure history from the DB (terminal attempts only).
    attempt_rows = conn.execute(
        """
        SELECT attempt_id, status, terminal_json, created_at
        FROM attempts
        WHERE issue_id = ?
          AND status IN ('failed', 'timed-out')
        ORDER BY created_at ASC
        """,
        (issue_id,),
    ).fetchall()

    history_lines: list[str] = []
    for i, row in enumerate(attempt_rows, 1):
        try:
            tj = json.loads(row["terminal_json"] or "{}")
        except (ValueError, TypeError):
            tj = {}
        pr = tj.get("prNumber")
        reason = tj.get("reason", row["status"])
        pr_ref = f" · PR #{pr}" if pr and pr != "null" else ""
        history_lines.append(
            f"{i}. `{row['status']}`{pr_ref} — {reason} _(at {row['created_at']})_"
        )

    history_md = "\n".join(history_lines) if history_lines else "_No attempt records found._"

    body = (
        f"## CI repair blocker: #{number}\n\n"
        f"Automated repair attempts for #{number} failed {retry_count + 1} time(s).\n"
        f"Human review required.\n\n"
        f"### Failure history\n\n"
        f"{history_md}\n\n"
        f"### Context\n\n"
        f"- Original issue: #{number}\n"
        f"- Area: `{area}`\n"
        f"- Failure class: `deterministic_test_failure`\n"
        f"- Total repair attempts: {retry_count + 1}\n\n"
        f"### Next steps\n\n"
        f"1. Review the CI logs linked above.\n"
        f"2. Fix the root cause in #{number} and reopen it, or close this blocker if resolved.\n"
        f"3. Requeue the original issue: `orchctl control requeue --area {area} --issue {number}`\n"
    )

    # NOTE: the 'blocker' label must exist in the target GitHub repo.
    # If it is absent, gh issue create exits non-zero, create_issue returns
    # None, and the failure is logged to stderr.  Create the label once via:
    #   gh label create blocker -R <owner/repo> --color e11d48
    blocker_number = create_issue(
        repo,
        title=f"[blocker] CI repair failed for #{number}",
        body=body,
        labels=["blocker"],
    )
    if blocker_number:
        click.echo(
            f"reconcile [{area}]: issue #{number} blocker issue created: #{blocker_number}."
        )
        try:
            post_issue_comment(
                repo,
                number,
                f"**Blocker issue created:** #{blocker_number}\n\n"
                f"Repair attempts exhausted after {retry_count + 1} tries. "
                f"See #{blocker_number} for failure history and next steps.",
            )
        except Exception as exc:  # noqa: BLE001
            click.echo(
                f"reconcile [{area}]: blocker comment failed (#{number}): {exc}", err=True
            )
    else:
        click.echo(
            f"reconcile [{area}]: issue #{number} blocker issue creation failed.",
            err=True,
        )


# ---------------------------------------------------------------------------
# Git conflict rebase playbook helpers
# ---------------------------------------------------------------------------


def _run_git_rebase_playbook(
    conn: sqlite3.Connection,
    area: str,
    number: int,
    terminal_json: str | None,
    *,
    pid: int = 0,
    owns_lease: bool = False,
) -> None:
    """Post a rebase-attempt context comment on the issue.

    Called when a ``git_conflict`` attempt is about to be re-queued as a
    rebase repair attempt.  Errors are non-fatal.

    Steps:
    1. Parse PR number from terminal_json.
    2. Resolve the PR's head branch via gh CLI.
    3. Renew the area lease before the second gh call (prevents expiry).
    4. Post a rebase-attempt context comment including the conflict reason
       and the branch to rebase, so the re-dispatched worker has full context.
    """
    repo = AREA_REPOS.get(area)
    if not repo:
        return

    pr_number: int | None = None
    conflict_reason: str | None = None
    if terminal_json:
        try:
            tj = json.loads(terminal_json)
            raw_pr = tj.get("prNumber")
            if raw_pr and raw_pr != "null":
                pr_number = int(raw_pr)
            conflict_reason = tj.get("reason") or None
        except (ValueError, TypeError, AttributeError):
            pass

    branch: str | None = None
    if pr_number:
        branch = get_pr_branch(repo, pr_number)
        if owns_lease and pid:
            renew(conn, area, pid)

    conflict_section = (
        f"\n\n**Conflict reason:** `{conflict_reason}`"
        if conflict_reason
        else "\n\n*(Conflict details unavailable — check the PR directly)*"
    )
    branch_section = (
        f"\n**Branch to rebase:** `{branch}`"
        if branch
        else ""
    )
    pr_ref = f" (PR #{pr_number})" if pr_number else ""
    body = (
        f"**Git rebase attempt scheduled**{pr_ref}\n\n"
        f"- Failure class: `git_conflict`\n"
        f"- The re-dispatched worker should fetch the latest base branch,"
        f" rebase the PR branch, resolve conflicts, and re-run tests."
        f"{conflict_section}"
        f"{branch_section}"
    )
    try:
        post_issue_comment(repo, number, body)
    except Exception as exc:  # noqa: BLE001
        click.echo(f"reconcile [{area}]: rebase comment failed (#{number}): {exc}", err=True)


def _create_git_rebase_blocker_issue(
    conn: sqlite3.Connection,
    area: str,
    issue_id: int,
    number: int,
    retry_count: int,
    terminal_json: str | None,
) -> None:
    """Create a blocker GitHub issue after repeated unresolvable git conflicts.

    The blocker issue includes the conflict history and a reference to the
    original issue.  Non-fatal on error.
    """
    repo = AREA_REPOS.get(area)
    if not repo:
        return

    attempt_rows = conn.execute(
        """
        SELECT attempt_id, status, terminal_json, created_at
        FROM attempts
        WHERE issue_id = ?
          AND status IN ('failed', 'timed-out')
        ORDER BY created_at ASC
        """,
        (issue_id,),
    ).fetchall()

    history_lines: list[str] = []
    for i, row in enumerate(attempt_rows, 1):
        try:
            tj = json.loads(row["terminal_json"] or "{}")
        except (ValueError, TypeError):
            tj = {}
        pr = tj.get("prNumber")
        reason = tj.get("reason", row["status"])
        pr_ref = f" · PR #{pr}" if pr and pr != "null" else ""
        history_lines.append(
            f"{i}. `{row['status']}`{pr_ref} — {reason} _(at {row['created_at']})_"
        )

    history_md = "\n".join(history_lines) if history_lines else "_No attempt records found._"

    body = (
        f"## Git conflict rebase blocker: #{number}\n\n"
        f"Automated rebase attempts for #{number} failed {retry_count + 1} time(s).\n"
        f"Human review required.\n\n"
        f"### Conflict history\n\n"
        f"{history_md}\n\n"
        f"### Context\n\n"
        f"- Original issue: #{number}\n"
        f"- Area: `{area}`\n"
        f"- Failure class: `git_conflict`\n"
        f"- Total rebase attempts: {retry_count + 1}\n\n"
        f"### Next steps\n\n"
        f"1. Manually rebase the PR branch against the latest base branch.\n"
        f"2. Resolve all merge conflicts and push the rebased branch.\n"
        f"3. Requeue the original issue: `orchctl control requeue --area {area} --issue {number}`\n"
        f"4. Close this blocker once resolved.\n"
    )

    blocker_number = create_issue(
        repo,
        title=f"[blocker] Git rebase failed for #{number}",
        body=body,
        labels=["blocker"],
    )
    if blocker_number:
        click.echo(
            f"reconcile [{area}]: issue #{number} git rebase blocker created: #{blocker_number}."
        )
        try:
            post_issue_comment(
                repo,
                number,
                f"**Blocker issue created:** #{blocker_number}\n\n"
                f"Rebase attempts exhausted after {retry_count + 1} tries. "
                f"See #{blocker_number} for conflict history and next steps.",
            )
        except Exception as exc:  # noqa: BLE001
            click.echo(
                f"reconcile [{area}]: rebase blocker comment failed (#{number}): {exc}", err=True
            )
    else:
        click.echo(
            f"reconcile [{area}]: issue #{number} git rebase blocker creation failed.",
            err=True,
        )


# ---------------------------------------------------------------------------
# Heartbeat pass
# ---------------------------------------------------------------------------


def _heartbeat_pass(
    conn: sqlite3.Connection,
    area: str,
    pid: int,
    dry_run: bool,
    issues_by_state: dict,
    owns_lease: bool = True,
) -> bool:
    """Collect multi-signal heartbeats for dispatched issues; stall detection.

    For each dispatched issue with a running attempt:
      1. Collect 4 signals: PR commit activity, pipeline state file mtime,
         worker log mtime, CPU jiffies delta.
      2. Record the snapshot in the heartbeats table.
      3. If 2 or more signals are absent, the attempt is marked 'timed-out'
         and the issue transitions to 'failed-terminal'.

    A single absent signal is ignored (transient network hiccup, brief I/O
    pause, pre-PR state).  Two or more absent signals indicate a genuine stall.

    Returns True on success, False if the lease was lost (caller should abort).
    """
    dispatched = issues_by_state.get("dispatched", [])
    if not dispatched:
        return True

    monorepo_root = os.environ.get("MONOREPO_ROOT", os.getcwd())

    for issue in dispatched:
        if owns_lease and not renew(conn, area, pid):
            click.echo(f"reconcile [{area}]: lease lost mid-pass — aborting.", err=True)
            return False

        issue_id = issue["id"]
        number = issue["number"]

        attempt = conn.execute(
            """
            SELECT attempt_id, pid FROM attempts
            WHERE issue_id = ? AND status = 'running'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (issue_id,),
        ).fetchone()

        if attempt is None:
            continue

        attempt_id = attempt["attempt_id"]
        worker_pid = attempt["pid"]

        if dry_run:
            click.echo(
                f"reconcile [{area}]: issue #{number} heartbeat check (dry-run)."
            )
            continue

        try:
            stalled, snapshot = check_stall(
                conn,
                area=area,
                issue_number=number,
                attempt_id=attempt_id,
                pid=worker_pid,
                monorepo_root=monorepo_root,
            )
        except Exception as exc:  # noqa: BLE001
            click.echo(
                f"reconcile [{area}]: issue #{number} heartbeat collection failed: {exc}",
                err=True,
            )
            continue

        click.echo(
            f"reconcile [{area}]: issue #{number} heartbeat:"
            f" pr_activity={snapshot.pr_activity},"
            f" state_mtime={snapshot.state_mtime},"
            f" log_mtime={snapshot.log_mtime},"
            f" cpu_delta={snapshot.cpu_delta}"
            f" (absent={snapshot.absent_count})"
        )

        if stalled:
            click.echo(
                f"reconcile [{area}]: issue #{number} stalled"
                f" ({snapshot.absent_count}/4 signals absent)"
                " → marking timed-out."
            )
            try:
                with conn:
                    apply_attempt_transition_tx(conn, attempt_id, "timed-out")
                    apply_issue_transition_tx(conn, issue_id, "failed-terminal")
            except Exception as exc:  # noqa: BLE001
                click.echo(
                    f"reconcile [{area}]: issue #{number} stall transition failed: {exc}",
                    err=True,
                )

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
    owns_lease: bool = True,
) -> bool:
    """Transition blocked issues to pending when their dependencies are done.

    For issues with dependency_type='none': unblocked immediately (no deps).
    For issues with hard/soft deps: the dependencies table is queried.
      Resolution uses per-edge dep_type stored in the dependencies table:
      - hard edge: dep must be 'completed'; any other terminal state fails the issue.
      - soft edge: dep must reach any terminal state; failure does not propagate.
    All edges must be terminal before any transition is made.
    Cross-area deps are resolved by looking up (dep_area, dep_number) in issues.
    If a dep is not yet in the DB (unknown), the issue stays blocked.

    Returns True on success, False if the lease was lost (caller should abort).
    """
    blocked = issues_by_state.get("blocked", [])
    for issue in blocked:
        if owns_lease and not renew(conn, area, pid):
            click.echo(f"reconcile [{area}]: lease lost mid-pass — aborting.", err=True)
            return False

        number = issue["number"]
        issue_id = issue["id"]
        # dep_type is only used as a none vs non-none gate here; for non-'none' issues
        # the per-edge dep_type stored in dependencies.dep_type drives resolution.
        dep_type = issue["dependency_type"]

        if dep_type == "none":
            click.echo(
                f"reconcile [{area}]: issue #{number} blocked with no deps"
                f" → unblocking{' (dry-run)' if dry_run else ''}."
            )
            if not dry_run:
                apply_issue_transition(conn, issue_id, "pending")
            continue

        # Resolve via dependencies table (supports cross-area deps).
        # dep_type per edge is read from dependencies.dep_type (not issue.dependency_type).
        dep_rows = conn.execute(
            """
            SELECT d.dep_area, d.dep_number, d.dep_type, i.state
            FROM dependencies d
            LEFT JOIN issues i ON i.area = d.dep_area AND i.number = d.dep_number
            WHERE d.issue_id = ?
            """,
            (issue_id,),
        ).fetchall()

        if not dep_rows:
            # Has a dep_type but no recorded deps — unblock optimistically.
            click.echo(
                f"reconcile [{area}]: issue #{number} has dep_type='{dep_type}'"
                f" but no dependency rows — unblocking{' (dry-run)' if dry_run else ''}."
            )
            if not dry_run:
                apply_issue_transition(conn, issue_id, "pending")
            continue

        unknown = [(r["dep_area"], r["dep_number"]) for r in dep_rows if r["state"] is None]
        if unknown:
            click.echo(
                f"reconcile [{area}]: issue #{number} waiting on unregistered deps:"
                f" {unknown} — keeping blocked."
            )
            continue

        # Per-edge resolution: each edge carries its own dep_type.
        new_state = _resolve_per_edge(dep_rows)

        if new_state == "blocked":
            click.echo(
                f"reconcile [{area}]: issue #{number} deps still running — keeping blocked."
            )
            continue

        click.echo(
            f"reconcile [{area}]: issue #{number} deps resolved"
            f" → {new_state}{' (dry-run)' if dry_run else ''}."
        )
        if not dry_run:
            apply_issue_transition(conn, issue_id, new_state)

    return True


def _resolve_per_edge(dep_rows: list) -> str:
    """Resolve blocked state using per-edge dep_type from the dependencies table.

    Each row must have 'state' (issue state string) and 'dep_type' ('hard'|'soft').
    Returns 'pending', 'blocked', or 'blocked-failed-dependency'.
    """
    terminal_values = {st.value for st in TERMINAL_ISSUE_STATES}

    if not all(r["state"] in terminal_values for r in dep_rows):
        return IssueState.BLOCKED.value

    if any(
        r["dep_type"] == DependencyType.HARD.value
        and r["state"] != IssueState.COMPLETED.value
        for r in dep_rows
    ):
        return IssueState.BLOCKED_FAILED_DEP.value

    return IssueState.PENDING.value


# ---------------------------------------------------------------------------
# Scheduling helpers
# ---------------------------------------------------------------------------


def _dispatch_score(
    row: sqlite3.Row,
    priority_weight: float,
    age_weight: float,
    retry_weight: float,
) -> float:
    """Compute the dispatch priority score for a pending issue.

    Higher score = dispatched sooner.

    Score = priority_weight * priority
          + age_weight * age_days
          - retry_weight * retry_count

    All three terms are additive so operators can zero-out any dimension by
    setting its weight to 0 in policy.yaml.
    """
    priority = row["priority"] or 0
    retry_count = row["retry_count"] or 0
    created_at_str = row["created_at"] or ""
    try:
        created_at = datetime.strptime(created_at_str, "%Y-%m-%d %H:%M:%S")
        now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
        age_days = (now_naive - created_at).total_seconds() / 86400.0
    except (ValueError, TypeError):
        age_days = 0.0
    return (
        priority_weight * priority
        + age_weight * age_days
        - retry_weight * retry_count
    )


def _sort_pending(
    pending: list[sqlite3.Row],
    priority_weight: float,
    age_weight: float,
    retry_weight: float,
) -> list[sqlite3.Row]:
    """Return *pending* sorted by dispatch score, highest first."""
    return sorted(
        pending,
        key=lambda row: _dispatch_score(row, priority_weight, age_weight, retry_weight),
        reverse=True,
    )


def _count_awaiting_merge(conn: sqlite3.Connection, area: str) -> int:
    """Count completed issues in *area* whose PRs have not yet been merged or rejected.

    Scoped to *area* for consistency with all other per-area admission controls
    (max_concurrent, max_open_pr, max_concurrent_repair).

    Uses ``(merge_state IS NULL OR merge_state NOT IN ('done', 'rejected'))``
    rather than a bare ``NOT IN`` to avoid SQL NULL semantics silently
    dropping rows where merge_state is NULL.
    """
    row = conn.execute(
        "SELECT COUNT(*) FROM issues"
        " WHERE state = 'completed'"
        " AND area = ?"
        " AND (merge_state IS NULL OR merge_state NOT IN ('done', 'rejected'))",
        (area,),
    ).fetchone()
    return row[0]


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
    owns_lease: bool = True,
) -> None:
    """Dispatch pending issues subject to admission control.

    Admission gates (first failure stops dispatch for remaining issues):
      1. Drain mode: no new dispatches when enabled globally.
      2. Area pause: no new dispatches when area is paused.
      3. Repo allowlist guardrail: area repo must be in the allowlist.
      4. maxConcurrent: per-area limit on issues in 'dispatched' state.
      5. globalQuota: global limit on issues in 'dispatched' state across all areas.
         Enforced atomically inside _record_dispatch to prevent TOCTOU races
         when multiple area reconcilers run concurrently.
      6. maxConcurrentRepair: cap on concurrently dispatched retry attempts.
      7. maxAwaitingMerge: stop new dispatches when too many completed issues
         still have unmerged PRs (0 = no limit).
      8. Per-issue: skip if an active attempt already exists.

    Pending issues are sorted by dispatch score before the loop so that
    high-priority issues are dispatched first within each admission window.
    """
    if config["drain_mode"]:
        click.echo(f"reconcile [{area}]: drain mode active — no new dispatches.")
        return

    if config["area_paused"]:
        click.echo(f"reconcile [{area}]: area is paused — no new dispatches.")
        return

    # Repo allowlist guardrail: if configured, area repo must be set and in the list.
    # Fails closed: if the allowlist is non-empty and the area's repo is not configured,
    # dispatch is refused rather than silently permitted.
    repo_allowlist_raw = config["repo_allowlist"]
    if repo_allowlist_raw:
        allowed_repos = {r.strip() for r in repo_allowlist_raw.split(",") if r.strip()}
        area_repo = config["area_repo"].strip()
        if not area_repo:
            click.echo(
                f"reconcile [{area}]: guardrail — repo_allowlist is set"
                f" but {area}.repo is not configured — no dispatches."
            )
            return
        if area_repo not in allowed_repos:
            click.echo(
                f"reconcile [{area}]: guardrail — repo '{area_repo}' not in allowlist"
                " — no dispatches."
            )
            return

    max_concurrent = config["max_concurrent"]
    global_quota = config["global_quota"]
    max_repair = config["max_concurrent_repair"]
    max_awaiting = config["max_awaiting_merge"]

    pending = issues_by_state.get("pending", [])
    if not pending:
        click.echo(f"reconcile [{area}]: no pending issues.")
        return

    # maxAwaitingMerge: gate on unmerged completed PRs (0 = disabled).
    if max_awaiting > 0:
        awaiting = _count_awaiting_merge(conn, area)
        if awaiting >= max_awaiting:
            click.echo(
                f"reconcile [{area}]: maxAwaitingMerge={max_awaiting} reached"
                f" ({awaiting} unmerged PRs) — no new dispatches."
            )
            return

    # Sort pending issues by composite score before dispatch.
    pending = _sort_pending(
        pending,
        priority_weight=config["scheduling_priority_weight"],
        age_weight=config["scheduling_age_weight"],
        retry_weight=config["scheduling_retry_weight"],
    )

    # Pre-compute active repair count once; incremented locally after each dispatch
    # to avoid N DB round-trips for N retry candidates.
    active_repairs = _count_active_repairs(conn, area)

    for issue in pending:
        if owns_lease and not renew(conn, area, pid):
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
        if active_global >= global_quota:
            click.echo(
                f"reconcile [{area}]: globalQuota={global_quota} reached"
                " (config key: max_open_pr) — no more dispatches."
            )
            return

        # maxConcurrentRepair: limit simultaneously dispatched retry attempts.
        retry_count = issue["retry_count"]
        if retry_count > 0 and active_repairs >= max_repair:
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
            dispatched = _record_dispatch(conn, issue_id, attempt_id, global_quota)
            if not dispatched:
                # A concurrent reconciler filled the global cap between our
                # optimistic check and the atomic insert.
                click.echo(
                    f"reconcile [{area}]: globalQuota={global_quota} reached"
                    " — global cap enforced concurrently, stopping."
                )
                return
            if retry_count > 0:
                active_repairs += 1
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
    conn: sqlite3.Connection, issue_id: int, attempt_id: str, global_quota: int
) -> bool:
    """Create a running attempt and transition the issue to 'dispatched' atomically.

    The attempt INSERT is conditional on the global dispatched count being below
    global_quota.  SQLite serializes writers, so this check-and-insert is
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
        (attempt_id, issue_id, global_quota),
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
