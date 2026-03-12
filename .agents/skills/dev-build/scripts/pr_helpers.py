#!/usr/bin/env python3
"""Push branch and create PR."""
import argparse, json, subprocess, sys


def cmd_push(args):
    subprocess.run(["git", "-C", args.worktree, "push", "-u", "origin", args.branch], check=True, capture_output=True)
    json.dump({"pushed": True, "branch": args.branch}, sys.stdout)


def cmd_create(args):
    result = subprocess.run(
        ["gh", "pr", "create", "-R", args.repo, "--title", args.title, "--body-file", args.body_file],
        capture_output=True, text=True, check=True, cwd=args.worktree,
    )
    lines = [l for l in result.stdout.splitlines() if l.strip()]
    url = lines[-1].strip()
    number = int(url.rstrip("/").split("/")[-1])
    json.dump({"number": number, "url": url}, sys.stdout)


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="command")

    pp = sub.add_parser("push")
    pp.add_argument("--worktree", required=True)
    pp.add_argument("--branch", required=True)

    pc = sub.add_parser("create")
    pc.add_argument("--worktree", required=True)
    pc.add_argument("--repo", required=True)
    pc.add_argument("--title", required=True)
    pc.add_argument("--body-file", required=True)

    args = p.parse_args()
    {"push": cmd_push, "create": cmd_create}[args.command](args)


if __name__ == "__main__":
    main()
