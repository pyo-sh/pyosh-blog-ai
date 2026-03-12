#!/usr/bin/env python3
"""Read PR review body and inline comments."""
import argparse, json, subprocess, sys


def main():
    p = argparse.ArgumentParser(description="Read PR review body and inline comments.")
    p.add_argument("--repo", required=True)
    p.add_argument("--pr", required=True, type=int)
    p.add_argument("--review-id", type=int, default=None)
    args = p.parse_args()

    # 1. PR metadata
    pr_result = subprocess.run(
        ["gh", "pr", "view", str(args.pr), "-R", args.repo,
         "--json", "title,state,body,reviews"],
        capture_output=True, text=True, check=True,
    )
    pr_data = json.loads(pr_result.stdout)

    # 2. Latest review or specified review-id
    reviews = pr_data.get("reviews", [])
    review_body = ""
    review_state = ""

    if args.review_id:
        r = subprocess.run(
            ["gh", "api", f"repos/{args.repo}/pulls/{args.pr}/reviews/{args.review_id}"],
            capture_output=True, text=True, check=True,
        )
        review = json.loads(r.stdout)
        review_body = review.get("body", "")
        review_state = review.get("state", "")
    elif reviews:
        latest = reviews[-1]
        review_body = latest.get("body", "")
        review_state = latest.get("state", "")

    # 3. Inline comments (if review-id specified)
    comments = []
    if args.review_id:
        try:
            c = subprocess.run(
                ["gh", "api",
                 f"repos/{args.repo}/pulls/{args.pr}/reviews/{args.review_id}/comments"],
                capture_output=True, text=True, check=True,
            )
            comments = json.loads(c.stdout)
        except Exception:
            pass  # non-fatal

    json.dump({
        "title": pr_data.get("title", ""),
        "state": review_state,
        "reviewBody": review_body,
        "comments": comments,
    }, sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    main()
