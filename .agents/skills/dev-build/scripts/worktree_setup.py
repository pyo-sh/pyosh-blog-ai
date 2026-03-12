#!/usr/bin/env python3
"""Create a worktree for dev-build. Handles fetch, rebase, worktree add."""
import argparse, json, subprocess, sys
from pathlib import Path

AREA_MAP = {
    "client":    {"subdir": "client",  "repo": "pyo-sh/pyosh-blog-fe"},
    "server":    {"subdir": "server",  "repo": "pyo-sh/pyosh-blog-be"},
    "workspace": {"subdir": "",        "repo": "pyo-sh/pyosh-blog-ai"},
}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--area", required=True, choices=AREA_MAP.keys())
    p.add_argument("--issue", required=True, type=int)
    p.add_argument("--type", required=True)  # feat, fix, docs, refactor, etc.
    p.add_argument("--desc", required=True)  # kebab-case description
    p.add_argument("--root", default="/workspace")
    args = p.parse_args()

    info = AREA_MAP[args.area]
    root = Path(args.root)
    repo_dir = root / info["subdir"] if info["subdir"] else root
    branch = f"{args.type}/issue-{args.issue}-{args.desc}"
    wt_path = root / ".workspace" / "worktrees" / args.area / f"issue-{args.issue}"

    # 1. fetch and fast-forward local main
    subprocess.run(["git", "-C", str(repo_dir), "fetch", "origin", "main"], check=True)

    # 2. worktree add from origin/main (avoids stale local main)
    wt_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "-C", str(repo_dir), "worktree", "add", "-b", branch, str(wt_path), "origin/main"],
        check=True,
    )

    json.dump(
        {"worktreePath": str(wt_path), "branch": branch, "repoDir": str(repo_dir), "repo": info["repo"]},
        sys.stdout,
    )


if __name__ == "__main__":
    main()
