import argparse
import json
import sys
import traceback


def _output(data: dict) -> None:
    print(json.dumps(data))


def main():
    parser = argparse.ArgumentParser(prog="dev_log")
    sub = parser.add_subparsers(dest="command")

    # ensure-branch
    p = sub.add_parser("ensure-branch")
    p.add_argument("--root", required=True)

    # create-worktree
    p = sub.add_parser("create-worktree")
    p.add_argument("--root", required=True)

    # next-seq
    p = sub.add_parser("next-seq")
    p.add_argument("--dir", required=True)
    p.add_argument("--type", required=True, choices=["findings", "decision"])

    # check-progress
    p = sub.add_parser("check-progress")
    p.add_argument("--dir", required=True)
    p.add_argument("--date", default=None)

    # commit
    p = sub.add_parser("commit")
    p.add_argument("--worktree", required=True)
    p.add_argument("--message", required=True)

    # merge-to-docs
    p = sub.add_parser("merge-to-docs")
    p.add_argument("--worktree", required=True)
    p.add_argument("--branch", required=True)
    p.add_argument("--root", required=True)

    # cleanup
    p = sub.add_parser("cleanup")
    p.add_argument("--worktree", required=True)
    p.add_argument("--branch", required=True)
    p.add_argument("--root", required=True)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        if args.command == "ensure-branch":
            from .worktree import ensure_docs_branch

            _output(ensure_docs_branch(args.root))

        elif args.command == "create-worktree":
            from .worktree import create_worktree

            _output(create_worktree(args.root))

        elif args.command == "next-seq":
            from .indexing import next_sequence

            _output(next_sequence(args.dir, args.type))

        elif args.command == "check-progress":
            from .indexing import check_progress

            _output(check_progress(args.dir, args.date))

        elif args.command == "commit":
            from .git_ops import add_docs, commit

            add_docs(args.worktree)
            sha = commit(args.worktree, args.message)
            _output({"sha": sha})

        elif args.command == "merge-to-docs":
            from .merge import merge_to_docs

            _output(merge_to_docs(args.worktree, args.branch, args.root))

        elif args.command == "cleanup":
            from .worktree import cleanup_worktree

            _output(cleanup_worktree(args.worktree, args.branch, args.root))

    except Exception:
        traceback.print_exc()
        sys.exit(1)
