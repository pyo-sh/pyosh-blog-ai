"""orchctl merge-gate — evaluate PR merge eligibility for an issue.

Checks (all must pass for merge to be allowed):
  1. checks_pass     — all required CI checks have passed (from terminal.json)
  2. sha_match       — PR head SHA matches the pipeline's last commit SHA
  3. no_conflict     — PR has no merge conflicts (MERGEABLE state)
  4. no_blocking_labels — no forbidden labels on the issue/PR
  5. branch_protection  — target branch must NOT be in protected_branches
                          (blocks auto-merge to main / release branches;
                          also fails when merge_enabled=false)

Input:  latest completed attempt's terminal_json for the issue.
Output: per-check pass/fail + overall eligibility.
"""

from __future__ import annotations

import json
import sqlite3

import click

from ..db import get_config, get_config_bool, get_db
from ..db.schema import LATEST_VERSION


@click.command("merge-gate")
@click.option("--area", required=True, help="Area of the issue.")
@click.option("--issue", "issue_number", required=True, type=int, help="Issue number.")
@click.option("--json", "as_json", is_flag=True, help="Output result as JSON.")
@click.pass_context
def cmd_merge_gate(ctx: click.Context, area: str, issue_number: int, as_json: bool) -> None:
    """Evaluate merge gate for AREA issue ISSUE_NUMBER.

    Exits with code 0 if all checks pass, 1 if any check fails, 2 on error.
    """
    conn = get_db(ctx.obj.get("db_path"))
    try:
        ver = _check_version(conn)
        if ver is not None:
            raise click.ClickException(ver)

        result = evaluate_merge_gate(conn, area, issue_number)

        if as_json:
            click.echo(json.dumps(result, indent=2))
        else:
            _print_result(result, area, issue_number)

        if result["eligible"]:
            ctx.exit(0)
        else:
            ctx.exit(1)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Core evaluation (importable for tests)
# ---------------------------------------------------------------------------


def evaluate_merge_gate(
    conn: sqlite3.Connection,
    area: str,
    issue_number: int,
) -> dict:
    """Evaluate merge gate checks and return a result dict.

    Returns:
        {
          "eligible": bool,
          "checks": {
            "checks_pass":        True | False | None,
            "sha_match":          True | False | None,
            "no_conflict":        True | False | None,
            "no_blocking_labels": True | False | None,
            "branch_protection":  True | False | None,
          },
          "reason": str | None,   # first failing check name, or None if all pass
          "terminal_json": dict | None,
        }
    """
    checks: dict[str, bool | None] = {
        "checks_pass": None,
        "sha_match": None,
        "no_conflict": None,
        "no_blocking_labels": None,
        "branch_protection": None,
    }

    # Load issue + latest completed attempt
    issue_row = conn.execute(
        "SELECT id, state FROM issues WHERE area = ? AND number = ?",
        (area, issue_number),
    ).fetchone()
    if issue_row is None:
        return _result(checks, eligible=False, reason="issue_not_found", terminal=None)

    attempt_row = conn.execute(
        """
        SELECT terminal_json FROM attempts
        WHERE issue_id = ?
          AND status = 'completed'
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (issue_row["id"],),
    ).fetchone()

    terminal: dict | None = None
    if attempt_row and attempt_row["terminal_json"]:
        try:
            terminal = json.loads(attempt_row["terminal_json"])
        except json.JSONDecodeError:
            terminal = None

    # --- Check 1-4: from terminal.json mergeEligibilityChecks ---
    if terminal:
        eligibility_checks = terminal.get("mergeEligibilityChecks") or {}
        checks["checks_pass"] = eligibility_checks.get("checksPass")
        checks["sha_match"] = eligibility_checks.get("shaMatch")
        checks["no_conflict"] = eligibility_checks.get("noConflict")
        checks["no_blocking_labels"] = eligibility_checks.get("noBlockingLabels")

    # --- Check 5: branch protection ---
    # Short-circuit immediately when merge_enabled=false so the reason is
    # unambiguous ("merge_disabled"), not whichever check happens to be first.
    merge_enabled = get_config_bool(conn, "merge_enabled", default=False)
    if not merge_enabled:
        checks["branch_protection"] = False
        return _result(checks, eligible=False, reason="merge_disabled", terminal=terminal)

    protected_raw = get_config(conn, "protected_branches", default="main")
    protected = {b.strip() for b in protected_raw.split(",") if b.strip()}
    # The branch to be merged into is read from terminal.json if present.
    target_branch = (terminal or {}).get("targetBranch", "main")
    checks["branch_protection"] = target_branch not in protected

    # Overall eligibility: all checks must be explicitly True
    failing = [k for k, v in checks.items() if v is not True]
    eligible = len(failing) == 0
    reason = failing[0] if failing else None

    return _result(checks, eligible=eligible, reason=reason, terminal=terminal)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _result(
    checks: dict,
    eligible: bool,
    reason: str | None,
    terminal: dict | None,
) -> dict:
    return {
        "eligible": eligible,
        "checks": checks,
        "reason": reason,
        "terminal_json": terminal,
    }


def _check_version(conn: sqlite3.Connection) -> str | None:
    """Return an error message if the DB is not ready, else None."""
    from ..db.migrate import current_version

    ver = current_version(conn)
    if ver == 0:
        return "Database not initialised — run `orchctl init` first."
    if ver < LATEST_VERSION:
        return (
            f"Database schema is out of date (v{ver} < v{LATEST_VERSION}) "
            "— run `orchctl init` to migrate."
        )
    return None


def _print_result(result: dict, area: str, issue_number: int) -> None:
    status = "PASS" if result["eligible"] else "FAIL"
    click.echo(f"merge-gate [{area}] issue #{issue_number}: {status}")
    for check_name, value in result["checks"].items():
        icon = "✓" if value is True else ("✗" if value is False else "?")
        click.echo(f"  {icon} {check_name}: {value}")
    if not result["eligible"] and result["reason"]:
        click.echo(f"  → blocked by: {result['reason']}")
