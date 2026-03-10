import json
import sys
from typing import Optional

from .command_runner import run


def _repo(area: str) -> str:
    """Map area to GitHub repo."""
    repos = {
        "client": "pyo-sh/pyosh-blog-fe",
        "server": "pyo-sh/pyosh-blog-be",
        "workspace": "pyo-sh/pyosh-blog-ai",
    }
    if area not in repos:
        raise ValueError(f"Unknown area: {area}")
    return repos[area]


def check_review_exists(area: str, pr: int, last_review_id: int = 0) -> Optional[int]:
    """Returns review_id if a qualifying review is found, None otherwise.

    Raises RuntimeError on gh CLI error.
    A qualifying review has id > last_review_id and body starting with '## Review Summary'.
    """
    repo = _repo(area)
    result = run(
        ["gh", "api", f"repos/{repo}/pulls/{pr}/reviews", "--paginate"],
        timeout=30,
    )
    if result.rc != 0:
        raise RuntimeError(
            f"[github_client] gh api error for PR #{pr} in {repo}: {result.stderr}"
        )

    reviews = []
    if result.stdout.strip():
        try:
            parsed = json.loads(result.stdout)
            if isinstance(parsed, list):
                reviews = parsed
            else:
                reviews = []
        except json.JSONDecodeError:
            # paginate may return concatenated JSON objects
            for line in result.stdout.strip().splitlines():
                if line.strip():
                    try:
                        part = json.loads(line)
                        if isinstance(part, list):
                            reviews.extend(part)
                    except json.JSONDecodeError:
                        pass

    candidates = [
        r for r in reviews
        if r.get("id", 0) > last_review_id
        and isinstance(r.get("body"), str)
        and r["body"].startswith("## Review Summary")
    ]
    if not candidates:
        return None
    return candidates[-1]["id"]


def fetch_review(area: str, pr: int, review_id: int) -> dict:
    """Returns {"state": ..., "body": ...}. Raises on error."""
    repo = _repo(area)
    result = run(
        [
            "gh", "api",
            f"repos/{repo}/pulls/{pr}/reviews/{review_id}",
            "--jq", "{state: .state, body: .body}",
        ],
        timeout=30,
    )
    if result.rc != 0:
        raise RuntimeError(
            f"[github_client] gh api error fetching review {review_id} "
            f"for PR #{pr}: {result.stderr}"
        )
    return json.loads(result.stdout)


def fetch_review_comments(area: str, pr: int, review_id: int) -> list:
    """Returns list of {path, line, side, body}. Returns [] on error (non-fatal)."""
    repo = _repo(area)
    result = run(
        [
            "gh", "api",
            f"repos/{repo}/pulls/{pr}/reviews/{review_id}/comments",
            "--paginate",
        ],
        timeout=30,
    )
    if result.rc != 0:
        print(
            f"[github_client] warning: failed to fetch review comments for "
            f"PR #{pr} review {review_id}: {result.stderr}",
            file=sys.stderr,
        )
        return []

    raw = json.loads(result.stdout) if result.stdout.strip() else []
    if not isinstance(raw, list):
        return []
    return [
        {
            "path": c.get("path"),
            "line": c.get("original_line") or c.get("line"),
            "side": c.get("side"),
            "body": c.get("body"),
        }
        for c in raw
    ]


def check_new_commits(area: str, pr: int, last_commit_sha: str) -> Optional[str]:
    """Returns new SHA if different from last_commit_sha, None if same.

    Raises RuntimeError on gh CLI error.
    """
    repo = _repo(area)
    result = run(
        [
            "gh", "pr", "view", str(pr),
            "-R", repo,
            "--json", "headRefOid",
            "--jq", ".headRefOid",
        ],
        timeout=30,
    )
    if result.rc != 0:
        raise RuntimeError(
            f"[github_client] gh error checking head SHA for PR #{pr}: {result.stderr}"
        )
    sha = result.stdout.strip()
    if sha and sha != "null" and sha != last_commit_sha:
        return sha
    return None


def get_pr_state(area: str, pr: int) -> str:
    """Returns 'MERGED', 'CLOSED', 'OPEN', etc."""
    repo = _repo(area)
    result = run(
        [
            "gh", "pr", "view", str(pr),
            "-R", repo,
            "--json", "state",
            "--jq", ".state",
        ],
        timeout=30,
    )
    if result.rc != 0:
        raise RuntimeError(
            f"[github_client] gh error getting PR state for #{pr}: {result.stderr}"
        )
    return result.stdout.strip()


def merge_pr_squash(area: str, pr: int, repo_dir: str) -> None:
    """Merge PR with squash and delete branch."""
    repo = _repo(area)
    result = run(
        ["gh", "pr", "merge", str(pr), "-R", repo, "--squash", "--delete-branch"],
        cwd=repo_dir,
        timeout=120,
    )
    if result.rc != 0:
        raise RuntimeError(
            f"[github_client] gh pr merge failed for PR #{pr}: {result.stderr}"
        )


def post_review_comment(area: str, pr: int, body_file: str) -> None:
    """Post a review comment to a PR using a file for the body."""
    repo = _repo(area)
    result = run(
        [
            "gh", "pr", "review", str(pr),
            "-R", repo,
            "--comment",
            "--body-file", body_file,
        ],
        timeout=30,
    )
    if result.rc != 0:
        raise RuntimeError(
            f"[github_client] failed to post review comment for PR #{pr}: {result.stderr}"
        )


def post_pr_comment(area: str, pr: int, body_file: str) -> None:
    """Post a general comment to a PR using a file for the body."""
    repo = _repo(area)
    result = run(
        ["gh", "pr", "comment", str(pr), "-R", repo, "--body-file", body_file],
        timeout=30,
    )
    if result.rc != 0:
        raise RuntimeError(
            f"[github_client] failed to post PR comment for PR #{pr}: {result.stderr}"
        )


def get_pr_base_ref(area: str, pr: int) -> str:
    """Returns the base branch name for the PR (defaults to 'main' on error)."""
    repo = _repo(area)
    result = run(
        [
            "gh", "pr", "view", str(pr),
            "-R", repo,
            "--json", "baseRefName",
            "--jq", ".baseRefName",
        ],
        timeout=30,
    )
    if result.rc != 0:
        return "main"
    return result.stdout.strip() or "main"
