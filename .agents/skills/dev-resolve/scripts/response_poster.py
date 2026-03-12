#!/usr/bin/env python3
"""Post a response comment to a PR."""
import argparse, json, subprocess, sys
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description="Post a response comment to a PR.")
    p.add_argument("--repo", required=True)
    p.add_argument("--pr", required=True, type=int)
    p.add_argument("--body-file", required=True)
    p.add_argument("--cleanup", action="store_true", help="Delete body file after posting")
    args = p.parse_args()

    body_path = Path(args.body_file)
    if not body_path.exists():
        print(f"Body file not found: {args.body_file}", file=sys.stderr)
        sys.exit(1)

    subprocess.run(
        ["gh", "pr", "comment", str(args.pr), "-R", args.repo,
         "--body-file", args.body_file],
        check=True,
    )

    if args.cleanup:
        body_path.unlink(missing_ok=True)

    json.dump({"posted": True}, sys.stdout)


if __name__ == "__main__":
    main()
