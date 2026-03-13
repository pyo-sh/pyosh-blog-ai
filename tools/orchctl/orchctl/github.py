"""GitHub API client for orchctl using the gh CLI."""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field

import click

# Mirrors .agents/references/monorepo-layout.md — update both when adding areas.
AREA_REPOS: dict[str, str] = {
    "client": "pyo-sh/pyosh-blog-fe",
    "server": "pyo-sh/pyosh-blog-be",
    "workspace": "pyo-sh/pyosh-blog-ai",
}

# Default timeout for gh CLI calls (seconds).  Chosen to be well within a
# typical lease TTL (60 s) so a stalled gh process does not hold the lease
# until it expires.
_GH_TIMEOUT = 30


# Regex to extract the fenced ```orchestrator ... ``` block from an issue body.
_ORCH_BLOCK_RE = re.compile(
    r"```orchestrator\s*\n(.*?)\n```",
    re.DOTALL | re.IGNORECASE,
)

# Regex to match a `priority: <int>` line inside the orchestrator block.
_PRIORITY_LINE_RE = re.compile(r"^\s*priority\s*:\s*(\d+)\s*$", re.MULTILINE)


@dataclass
class GitHubIssue:
    number: int
    title: str
    labels: list[str] = field(default_factory=list)
    milestone: str = ""
    assignees: list[str] = field(default_factory=list)
    body: str = ""
    priority: int = 0


class GitHubError(Exception):
    """Raised when the gh CLI call fails."""


def list_open_issues(
    repo: str,
    *,
    include_labels: list[str] | None = None,
    exclude_labels: list[str] | None = None,
    milestone: str = "",
    allow_unassigned: bool = True,
    limit: int = 500,
) -> list[GitHubIssue]:
    """List open GitHub issues for *repo* matching the scope config.

    Fetches all open issues via ``gh issue list``, then applies include/exclude
    label filters and the unassigned gate in Python (OR semantics for
    include_labels).

    Args:
        repo: GitHub repo in ``owner/name`` form.
        include_labels: If non-empty, only issues that have at least one of
            these labels are returned.
        exclude_labels: Issues carrying any of these labels are excluded.
        milestone: If non-empty, only issues in this milestone are returned.
        allow_unassigned: When False, issues with no assignees are excluded.
        limit: Maximum number of issues to fetch from GitHub (default 500).

    Raises:
        GitHubError: When the ``gh`` subprocess exits non-zero or times out.
    """
    # Note on filter asymmetry: the milestone filter is pushed down to the
    # gh CLI (--milestone) because gh supports it natively as an exact match.
    # Label filters (include/exclude) are applied in Python to achieve OR
    # semantics — the gh CLI only supports AND when --label is repeated.
    cmd = [
        "gh", "issue", "list",
        "-R", repo,
        "--state", "open",
        # body is required to parse `priority:` from the fenced orchestrator block.
        # Kept on every reconcile so that reopened issues pick up priority changes.
        "--json", "number,title,labels,milestone,assignees,body",
        "--limit", str(limit),
    ]
    if milestone:
        cmd += ["--milestone", milestone]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=_GH_TIMEOUT)
    except subprocess.TimeoutExpired as exc:
        raise GitHubError(f"gh issue list timed out after {exc.timeout}s") from exc

    if result.returncode != 0:
        raise GitHubError(f"gh issue list failed: {result.stderr.strip()}")

    raw: list[dict] = json.loads(result.stdout or "[]")

    if len(raw) >= limit:
        click.echo(
            f"github: hit issue limit ({limit}) for {repo} — some issues may be missed.",
            err=True,
        )

    issues = [_parse_issue(item) for item in raw]

    return _apply_scope_filters(
        issues,
        include_labels=include_labels or [],
        exclude_labels=exclude_labels or [],
        allow_unassigned=allow_unassigned,
    )


def post_issue_comment(repo: str, issue_number: int, body: str) -> None:
    """Post a comment to a GitHub issue via the gh CLI.

    Errors are logged but do not raise — a comment failure must never abort
    a reconcile pass.

    Args:
        repo: GitHub repo in ``owner/name`` form.
        issue_number: The GitHub issue number.
        body: Markdown comment body.
    """
    cmd = [
        "gh", "issue", "comment", str(issue_number),
        "-R", repo,
        "--body", body,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=_GH_TIMEOUT)
        if result.returncode != 0:
            click.echo(
                f"github: issue comment failed (#{issue_number}): {result.stderr.strip()}",
                err=True,
            )
    except subprocess.TimeoutExpired:
        click.echo(
            f"github: issue comment timed out (#{issue_number}) after {_GH_TIMEOUT}s",
            err=True,
        )
    except Exception as exc:  # noqa: BLE001
        click.echo(
            f"github: issue comment error (#{issue_number}): {exc}",
            err=True,
        )


def fetch_ci_logs(repo: str, branch: str, max_lines: int = 100) -> str | None:
    """Fetch the tail of the most recent failed CI workflow run logs for *branch*.

    Uses ``gh run list`` to find the latest failed run on the branch, then
    ``gh run view --log-failed`` to retrieve the failed step output.

    Returns a trimmed log string (at most *max_lines* lines), or None if no
    failed run is found or the gh CLI call fails.  Errors are logged but do
    not raise — a log fetch failure must never abort a reconcile pass.

    Args:
        repo: GitHub repo in ``owner/name`` form.
        branch: Branch name to filter runs.
        max_lines: Maximum number of log lines to return (tail).
    """
    list_cmd = [
        "gh", "run", "list",
        "-R", repo,
        "--branch", branch,
        "--status", "failure",
        "--limit", "1",
        "--json", "databaseId",
    ]
    try:
        list_result = subprocess.run(
            list_cmd, capture_output=True, text=True, timeout=_GH_TIMEOUT
        )
    except subprocess.TimeoutExpired:
        click.echo(
            f"github: gh run list timed out for branch '{branch}'",
            err=True,
        )
        return None
    except Exception as exc:  # noqa: BLE001
        click.echo(f"github: gh run list error for branch '{branch}': {exc}", err=True)
        return None

    if list_result.returncode != 0:
        click.echo(
            f"github: gh run list failed for branch '{branch}': {list_result.stderr.strip()}",
            err=True,
        )
        return None

    runs: list[dict] = json.loads(list_result.stdout or "[]")
    if not runs:
        return None

    run_id = runs[0].get("databaseId")
    if not run_id:
        return None

    log_cmd = [
        "gh", "run", "view", str(run_id),
        "-R", repo,
        "--log-failed",
    ]
    try:
        log_result = subprocess.run(
            log_cmd, capture_output=True, text=True, timeout=_GH_TIMEOUT
        )
    except subprocess.TimeoutExpired:
        click.echo(
            f"github: gh run view --log-failed timed out for run {run_id}",
            err=True,
        )
        return None
    except Exception as exc:  # noqa: BLE001
        click.echo(f"github: gh run view error for run {run_id}: {exc}", err=True)
        return None

    if log_result.returncode != 0:
        click.echo(
            f"github: gh run view failed for run {run_id}: {log_result.stderr.strip()}",
            err=True,
        )
        return None

    raw_log = log_result.stdout or ""
    lines = raw_log.splitlines()
    if len(lines) > max_lines:
        lines = lines[-max_lines:]
    return "\n".join(lines)


def create_issue(
    repo: str,
    title: str,
    body: str,
    labels: list[str] | None = None,
) -> int | None:
    """Create a GitHub issue and return its number.

    Returns None on failure.  Errors are logged but do not raise — a creation
    failure must never abort a reconcile pass.

    Args:
        repo: GitHub repo in ``owner/name`` form.
        title: Issue title.
        body: Issue body (Markdown).
        labels: Optional list of label names to apply.
    """
    cmd = [
        "gh", "issue", "create",
        "-R", repo,
        "--title", title,
        "--body", body,
    ]
    for label in (labels or []):
        cmd += ["--label", label]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=_GH_TIMEOUT)
    except subprocess.TimeoutExpired:
        click.echo(f"github: gh issue create timed out for '{title}'", err=True)
        return None
    except Exception as exc:  # noqa: BLE001
        click.echo(f"github: gh issue create error for '{title}': {exc}", err=True)
        return None

    if result.returncode != 0:
        click.echo(
            f"github: gh issue create failed for '{title}': {result.stderr.strip()}",
            err=True,
        )
        return None

    # gh issue create prints the URL; extract the issue number from the tail.
    url = result.stdout.strip()
    try:
        return int(url.rstrip("/").rsplit("/", 1)[-1])
    except (ValueError, IndexError):
        click.echo(f"github: could not parse issue number from URL: {url}", err=True)
        return None


def get_pr_branch(repo: str, pr_number: int) -> str | None:
    """Return the head branch name for a PR.  Returns None on any error."""
    cmd = [
        "gh", "pr", "view", str(pr_number),
        "-R", repo,
        "--json", "headRefName",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=_GH_TIMEOUT)
    except subprocess.TimeoutExpired:
        click.echo(
            f"github: gh pr view timed out for PR #{pr_number}",
            err=True,
        )
        return None
    except Exception as exc:  # noqa: BLE001
        click.echo(f"github: gh pr view error for PR #{pr_number}: {exc}", err=True)
        return None

    if result.returncode != 0:
        click.echo(
            f"github: gh pr view failed for PR #{pr_number}: {result.stderr.strip()}",
            err=True,
        )
        return None

    try:
        return json.loads(result.stdout).get("headRefName")
    except (json.JSONDecodeError, AttributeError):
        return None


def parse_priority_from_body(body: str) -> int:
    """Extract the priority value from a fenced orchestrator block in an issue body.

    Looks for a ``priority: <int>`` line inside a fenced ``orchestrator`` block.
    Returns 0 if the block or line is absent, or if the value cannot be parsed.

    Only non-negative integers are supported via the fenced block (the regex
    matches ``\\d+``).  To assign a priority below 0, set the ``priority``
    column directly in the database.
    """
    block_match = _ORCH_BLOCK_RE.search(body)
    if not block_match:
        return 0
    priority_match = _PRIORITY_LINE_RE.search(block_match.group(1))
    if not priority_match:
        return 0
    try:
        return int(priority_match.group(1))
    except (ValueError, TypeError):
        return 0


def _parse_issue(item: dict) -> GitHubIssue:
    ms = item.get("milestone") or {}
    body = item.get("body", "") or ""
    return GitHubIssue(
        number=item["number"],
        title=item.get("title", ""),
        labels=[lb["name"] for lb in item.get("labels", [])],
        milestone=ms.get("title", "") if ms else "",
        assignees=[a["login"] for a in item.get("assignees", [])],
        body=body,
        priority=parse_priority_from_body(body),
    )


def _apply_scope_filters(
    issues: list[GitHubIssue],
    *,
    include_labels: list[str],
    exclude_labels: list[str],
    allow_unassigned: bool,
) -> list[GitHubIssue]:
    """Return issues that pass all scope filters."""
    result = []
    inc_set = set(include_labels)
    exc_set = set(exclude_labels)

    for issue in issues:
        label_set = set(issue.labels)

        if inc_set and not label_set & inc_set:
            continue

        if label_set & exc_set:
            continue

        if not allow_unassigned and not issue.assignees:
            continue

        result.append(issue)

    return result
