import argparse
import json
import sys
import traceback

from .command_runner import run


def _output(data: dict) -> None:
    print(json.dumps(data))


def _check_diff(root: str) -> dict:
    """Check if docs branch has commits ahead of main."""
    run(["git", "-C", root, "fetch", "origin", "main", "docs"])
    result = run(
        ["git", "-C", root, "log", "origin/main..origin/docs", "--oneline"],
        check=False,
    )
    lines = [l for l in result.stdout.strip().splitlines() if l]
    return {"count": len(lines), "commits": lines}


def _ensure_label(root: str) -> dict:
    """Ensure the 'docs' label exists on the repository."""
    run(
        ["gh", "label", "create", "docs", "--force"],
        cwd=root,
        check=False,
    )
    return {"ok": True}


def _create_pr(root: str, title: str, body: str) -> dict:
    """Create a PR from docs -> main."""
    cmd = [
        "gh", "pr", "create",
        "--base", "main",
        "--head", "docs",
        "--label", "docs",
        "--title", title,
    ]
    if body:
        cmd.extend(["--body", body])
    result = run(cmd, cwd=root)
    url = result.stdout.strip()
    # Extract PR number from URL
    pr = url.rstrip("/").split("/")[-1]
    return {"url": url, "pr": int(pr)}


def _squash_merge(root: str, pr: int) -> dict:
    """Squash-merge a PR (without deleting the branch)."""
    run(
        ["gh", "pr", "merge", str(pr), "--squash", "--delete-branch=false"],
        cwd=root,
    )
    return {"merged": True, "pr": pr}


def _sync_branch(root: str) -> dict:
    """Reset docs branch to origin/main after squash merge."""
    run(["git", "-C", root, "fetch", "origin", "main"])
    # Update local docs to match origin/main
    run(["git", "-C", root, "branch", "-f", "docs", "origin/main"])
    run(["git", "-C", root, "push", "--force-with-lease", "origin", "docs"])
    return {"synced": True}


def main():
    parser = argparse.ArgumentParser(prog="dev_archive")
    sub = parser.add_subparsers(dest="command")

    # check-diff
    p = sub.add_parser("check-diff")
    p.add_argument("--root", required=True)

    # ensure-label
    p = sub.add_parser("ensure-label")
    p.add_argument("--root", required=True)

    # create-pr
    p = sub.add_parser("create-pr")
    p.add_argument("--root", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--body", default="")

    # squash-merge
    p = sub.add_parser("squash-merge")
    p.add_argument("--root", required=True)
    p.add_argument("--pr", required=True, type=int)

    # sync-branch
    p = sub.add_parser("sync-branch")
    p.add_argument("--root", required=True)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        if args.command == "check-diff":
            _output(_check_diff(args.root))

        elif args.command == "ensure-label":
            _output(_ensure_label(args.root))

        elif args.command == "create-pr":
            _output(_create_pr(args.root, args.title, args.body))

        elif args.command == "squash-merge":
            _output(_squash_merge(args.root, args.pr))

        elif args.command == "sync-branch":
            _output(_sync_branch(args.root))

    except Exception:
        traceback.print_exc()
        sys.exit(1)
