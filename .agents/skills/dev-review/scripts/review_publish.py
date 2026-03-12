#!/usr/bin/env python3
"""Contract-driven review publisher for dev-review skill.

Validates review JSON against schema, checks for contamination,
renders markdown, and optionally publishes to GitHub.

Usage:
    python review_publish.py --input review.json --mode dry-run
    python review_publish.py --input review.json --mode publish --repo owner/repo --pr 123
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------

_VALID_VERDICTS = ("approve", "request_changes", "comment")
_VALID_SEVERITIES = {"P0", "P1", "P2", "P3", "info"}
_ALLOWED_ISSUE_KEYS = {"severity", "path", "line", "title", "body", "suggested_fix"}
_ALLOWED_TOP_KEYS = {"verdict", "summary", "issues"}


def validate_payload(payload: dict) -> list[str]:
    """Validate payload against review JSON schema contract. Returns error list."""
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["payload is not a JSON object"]

    verdict = payload.get("verdict")
    if verdict not in _VALID_VERDICTS:
        errors.append(f"invalid verdict: {verdict!r}")

    summary = payload.get("summary")
    if not isinstance(summary, str):
        errors.append("summary missing or not a string")
    elif len(summary) > 2000:
        errors.append(f"summary exceeds 2000 chars ({len(summary)})")

    issues = payload.get("issues")
    if not isinstance(issues, list):
        errors.append("issues missing or not an array")
        return errors
    if len(issues) > 50:
        errors.append(f"too many issues ({len(issues)}, max 50)")

    for i, item in enumerate(issues):
        if not isinstance(item, dict):
            errors.append(f"issues[{i}] is not an object")
            continue
        if item.get("severity") not in _VALID_SEVERITIES:
            errors.append(f"issues[{i}].severity invalid: {item.get('severity')!r}")
        for req in ("title", "body"):
            if not isinstance(item.get(req), str):
                errors.append(f"issues[{i}].{req} missing or not a string")
        if isinstance(item.get("title"), str) and len(item["title"]) > 200:
            errors.append(f"issues[{i}].title exceeds 200 chars")
        if isinstance(item.get("body"), str) and len(item["body"]) > 2000:
            errors.append(f"issues[{i}].body exceeds 2000 chars")
        if isinstance(item.get("suggested_fix"), str) and len(item["suggested_fix"]) > 2000:
            errors.append(f"issues[{i}].suggested_fix exceeds 2000 chars")
        if isinstance(item.get("path"), str) and len(item["path"]) > 500:
            errors.append(f"issues[{i}].path exceeds 500 chars")
        if "line" in item:
            if not isinstance(item["line"], int):
                errors.append(f"issues[{i}].line is not an integer")
            elif item["line"] < 1:
                errors.append(f"issues[{i}].line must be >= 1")
        extra = set(item.keys()) - _ALLOWED_ISSUE_KEYS
        if extra:
            errors.append(f"issues[{i}] has unknown keys: {sorted(extra)}")

    extra_top = set(payload.keys()) - _ALLOWED_TOP_KEYS
    if extra_top:
        errors.append(f"payload has unknown keys: {sorted(extra_top)}")

    return errors


# ---------------------------------------------------------------------------
# Contamination check
# ---------------------------------------------------------------------------

# Patterns that should never appear in legitimate review text.
# Each is (substring, short description).
_CONTAMINATION_PATTERNS: list[tuple[str, str]] = [
    # Skill frontmatter / section headers
    ("---\nname: dev-review", "skill frontmatter"),
    ("---\nname: dev-pipeline", "skill frontmatter"),
    ("## Runtime contract when invoked by dev-pipeline", "skill section header"),
    # Pipeline env var names
    ("PIPELINE_MONOREPO_ROOT", "pipeline env var"),
    ("PIPELINE_REPO_DIR", "pipeline env var"),
    ("PIPELINE_WORKTREE_DIR", "pipeline env var"),
    # CLI flags indicating transcript leak
    ("--dangerously-skip-permissions", "CLI flag"),
    ("--dangerously-bypass-approvals", "CLI flag"),
    ("--no-session-persistence", "CLI flag"),
    # System prompt markers
    ("<system-reminder>", "system prompt tag"),
    ("</system-reminder>", "system prompt tag"),
]


def check_contamination(payload: dict) -> list[str]:
    """Check all string fields for contamination. Returns list of findings."""
    findings: list[str] = []

    def _check(value: str, field: str) -> None:
        for pattern, desc in _CONTAMINATION_PATTERNS:
            if pattern in value:
                findings.append(f"{field}: {desc}")

    if isinstance(payload.get("summary"), str):
        _check(payload["summary"], "summary")

    for i, item in enumerate(payload.get("issues", [])):
        if not isinstance(item, dict):
            continue
        for key in ("title", "body", "suggested_fix"):
            val = item.get(key)
            if isinstance(val, str):
                _check(val, f"issues[{i}].{key}")

    return findings


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------

_SEV_TO_SECTION = {
    "P0": "Critical",
    "P1": "Critical",
    "P2": "Warning",
    "P3": "Suggestion",
    "info": "Info",
}

_SEV_TO_TAG = {
    "P0": "CRITICAL",
    "P1": "CRITICAL",
    "P2": "WARNING",
    "P3": "SUGGESTION",
    "info": "INFO",
}


def render_markdown(payload: dict) -> str:
    """Render validated review JSON into GitHub PR review markdown."""
    issues = payload.get("issues", [])

    counts = {"CRITICAL": 0, "WARNING": 0, "SUGGESTION": 0, "INFO": 0}
    for item in issues:
        tag = _SEV_TO_TAG.get(item["severity"], "SUGGESTION")
        if tag in counts:
            counts[tag] += 1

    lines = [
        "## Review Summary",
        "",
        "| Severity | Count |",
        "|----------|-------|",
        f"| [CRITICAL] | {counts['CRITICAL']} |",
        f"| [WARNING] | {counts['WARNING']} |",
        f"| [SUGGESTION] | {counts['SUGGESTION']} |",
        f"| [INFO] | {counts['INFO']} |",
        "",
        payload.get("summary", ""),
        "",
    ]

    # Group by section, merge P0+P1 into Critical
    grouped: dict[str, list[dict]] = {}
    for item in issues:
        section = _SEV_TO_SECTION.get(item["severity"], "Info")
        grouped.setdefault(section, []).append(item)

    for section_name in ("Critical", "Warning", "Suggestion", "Info"):
        section_items = grouped.get(section_name, [])
        if not section_items:
            continue
        lines.append(f"### {section_name}")
        for n, item in enumerate(section_items, 1):
            path = item.get("path", "")
            line_no = item.get("line")
            loc = ""
            if path:
                loc = f"`{path}" + (f":{line_no}" if line_no else "") + "` - "
            lines.append(f"{n}. {loc}{item['title']}")
            lines.append(item["body"])
            if item.get("suggested_fix"):
                lines.append("")
                lines.append("**Suggested fix:**")
                lines.append(item["suggested_fix"])
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


# ---------------------------------------------------------------------------
# GitHub publish
# ---------------------------------------------------------------------------

_VERDICT_TO_ACTION = {
    "approve": "--approve",
    "request_changes": "--request-changes",
    "comment": "--comment",
}


def _is_pr_author(repo: str, pr: int) -> bool:
    """Return True if the current gh-authenticated user is the PR author."""
    try:
        me = subprocess.run(
            ["gh", "api", "user", "--jq", ".login"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        author = subprocess.run(
            ["gh", "pr", "view", str(pr), "-R", repo, "--json", "author", "--jq", ".author.login"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        return bool(me and author and me == author)
    except subprocess.CalledProcessError:
        return False


def publish_to_github(repo: str, pr: int, body: str, verdict: str) -> int:
    """Post review to GitHub via gh CLI. Returns exit code."""
    action = _VERDICT_TO_ACTION[verdict]
    fd, tmp_path = tempfile.mkstemp(suffix=".md", prefix="review-")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(body)
        result = subprocess.run(
            ["gh", "pr", "review", str(pr), "-R", repo,
             "--body-file", tmp_path, action],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            print(f"gh pr review failed: {result.stderr.strip()}", file=sys.stderr)
        return result.returncode
    finally:
        os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate and publish review JSON to GitHub.",
    )
    parser.add_argument("--input", required=True, help="Path to review.json")
    parser.add_argument(
        "--mode", choices=["dry-run", "publish"], default="publish",
        help="publish (default): post to GitHub; dry-run: local only",
    )
    parser.add_argument("--repo", help="GitHub repo (owner/repo), required for publish")
    parser.add_argument("--pr", type=int, help="PR number, required for publish")
    parser.add_argument(
        "--output-dir",
        help="Directory for rendered markdown (default: input file directory)",
    )
    args = parser.parse_args(argv)

    if args.mode == "publish" and (not args.repo or not args.pr):
        parser.error("--repo and --pr are required for publish mode")

    # 1. Load
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"error: input file not found: {input_path}", file=sys.stderr)
        return 1

    try:
        payload = json.loads(input_path.read_text())
    except json.JSONDecodeError as e:
        print(f"error: invalid JSON: {e}", file=sys.stderr)
        return 1

    # 2. Validate
    errors = validate_payload(payload)
    if errors:
        print("schema validation failed:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    # 3. Contamination check
    findings = check_contamination(payload)
    if findings:
        print("contamination detected - publish blocked:", file=sys.stderr)
        for finding in findings:
            print(f"  - {finding}", file=sys.stderr)
        return 1

    # 4. Render
    rendered = render_markdown(payload)

    # 5. Write artifacts
    out_dir = Path(args.output_dir) if args.output_dir else input_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / "review.md"
    md_path.write_text(rendered)
    print(f"rendered: {md_path}", file=sys.stderr)

    # 6. Publish or dry-run
    if args.mode == "dry-run":
        print(rendered)
        return 0

    effective_verdict = payload["verdict"]
    if effective_verdict != "comment" and _is_pr_author(args.repo, args.pr):
        print(
            f"reviewer is PR author - downgrading verdict from {effective_verdict!r} to 'comment'",
            file=sys.stderr,
        )
        effective_verdict = "comment"

    rc = publish_to_github(args.repo, args.pr, rendered, effective_verdict)
    if rc == 0:
        print(f"published review to {args.repo}#{args.pr}", file=sys.stderr)
    return rc


if __name__ == "__main__":
    sys.exit(main())
