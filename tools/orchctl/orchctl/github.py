"""GitHub API client for orchctl using the gh CLI."""

from __future__ import annotations

import json
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


@dataclass
class GitHubIssue:
    number: int
    title: str
    labels: list[str] = field(default_factory=list)
    milestone: str = ""
    assignees: list[str] = field(default_factory=list)


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
        "--json", "number,title,labels,milestone,assignees",
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


def _parse_issue(item: dict) -> GitHubIssue:
    ms = item.get("milestone") or {}
    return GitHubIssue(
        number=item["number"],
        title=item.get("title", ""),
        labels=[lb["name"] for lb in item.get("labels", [])],
        milestone=ms.get("title", "") if ms else "",
        assignees=[a["login"] for a in item.get("assignees", [])],
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
