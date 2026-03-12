#!/usr/bin/env python3
"""Remove worktree and delete local branch."""
import argparse, json, subprocess, sys


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo-dir", required=True)
    p.add_argument("--worktree", required=True)
    p.add_argument("--branch", required=True)
    args = p.parse_args()

    subprocess.run(["git", "-C", args.repo_dir, "worktree", "remove", args.worktree], check=True)
    subprocess.run(["git", "-C", args.repo_dir, "branch", "-d", args.branch], check=False)
    json.dump({"removed": True}, sys.stdout)


if __name__ == "__main__":
    main()
