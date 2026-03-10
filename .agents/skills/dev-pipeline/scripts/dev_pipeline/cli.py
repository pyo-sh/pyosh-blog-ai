import argparse
import json
import sys
from pathlib import Path

_AREA_CHOICES = ["client", "server", "workspace"]


def _get_monorepo_root() -> Path:
    from .paths import find_monorepo_root
    return find_monorepo_root()


def cmd_run(args) -> int:
    """Dispatch review for an issue."""
    monorepo_root = _get_monorepo_root()
    from .review_runner import dispatch_review

    return dispatch_review(
        issue=args.issue,
        area=args.area,
        pr=args.pr,
        monorepo_root=monorepo_root,
        tool=args.tool,
        model=args.model or "",
    )


def cmd_list(args) -> int:
    monorepo_root = _get_monorepo_root()
    from .controller import list_pipelines

    pipelines = list_pipelines(monorepo_root)
    if not pipelines:
        print("No active pipelines")
        return 0
    for p in pipelines:
        print(f"Issue #{p['issue']} ({p['area']}): step={p['step']} pr=#{p['pr']}")
    return 0


def cmd_state(args) -> int:
    monorepo_root = _get_monorepo_root()
    from .state_store import state_read

    try:
        data = state_read(args.issue, args.area, monorepo_root)
        print(json.dumps(data, indent=2))
        return 0
    except FileNotFoundError:
        print(
            f"No state found for issue #{args.issue} area={args.area}",
            file=sys.stderr,
        )
        return 1


def cmd_merge(args) -> int:
    monorepo_root = _get_monorepo_root()
    from .controller import merge_pr

    try:
        merge_pr(args.issue, args.area, args.pr, args.branch, monorepo_root)
        return 0
    except Exception as e:
        print(str(e), file=sys.stderr)
        return 1


def cmd_cleanup(args) -> int:
    monorepo_root = _get_monorepo_root()
    from .controller import cleanup

    try:
        cleanup(args.issue, args.area, args.branch, args.pr, monorepo_root)
        return 0
    except Exception as e:
        print(str(e), file=sys.stderr)
        return 1


def cmd_escalation(args) -> int:
    monorepo_root = _get_monorepo_root()
    from .controller import format_escalation

    print(format_escalation(args.issue, args.area, args.stage, monorepo_root))
    return 0


def cmd_parse_review(args) -> int:
    """Parse review body from stdin and output counts as JSON."""
    from .review_normalizer import parse_review_body

    body = sys.stdin.read()
    try:
        counts = parse_review_body(body)
        print(
            json.dumps({
                "critical": counts.critical,
                "warning": counts.warning,
                "suggestion": counts.suggestion,
            })
        )
        return 0
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 1


def main():
    parser = argparse.ArgumentParser(
        prog="dev_pipeline",
        description="dev-pipeline Python CLI",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # run
    p_run = sub.add_parser("run", help="Dispatch review for an issue")
    p_run.add_argument("--issue", type=int, required=True)
    p_run.add_argument("--area", required=True, choices=_AREA_CHOICES)
    p_run.add_argument("--pr", type=int, required=True)
    p_run.add_argument("--tool", default="claude", choices=["claude", "codex"])
    p_run.add_argument("--model", default="")
    p_run.set_defaults(func=cmd_run)

    # list
    p_list = sub.add_parser("list", help="List active pipelines")
    p_list.set_defaults(func=cmd_list)

    # state
    p_state = sub.add_parser("state", help="Show pipeline state for an issue")
    p_state.add_argument("--issue", type=int, required=True)
    p_state.add_argument("--area", required=True, choices=_AREA_CHOICES)
    p_state.set_defaults(func=cmd_state)

    # merge
    p_merge = sub.add_parser("merge", help="Merge PR for an issue")
    p_merge.add_argument("--issue", type=int, required=True)
    p_merge.add_argument("--area", required=True, choices=_AREA_CHOICES)
    p_merge.add_argument("--pr", type=int, required=True)
    p_merge.add_argument("--branch", required=True)
    p_merge.set_defaults(func=cmd_merge)

    # cleanup
    p_cleanup = sub.add_parser("cleanup", help="Cleanup after pipeline completes")
    p_cleanup.add_argument("--issue", type=int, required=True)
    p_cleanup.add_argument("--area", required=True, choices=_AREA_CHOICES)
    p_cleanup.add_argument("--branch", required=True)
    p_cleanup.add_argument("--pr", type=int, default=0)
    p_cleanup.set_defaults(func=cmd_cleanup)

    # escalation
    p_esc = sub.add_parser("escalation", help="Format escalation message")
    p_esc.add_argument("--issue", type=int, required=True)
    p_esc.add_argument("--area", required=True, choices=_AREA_CHOICES)
    p_esc.add_argument("--stage", required=True)
    p_esc.set_defaults(func=cmd_escalation)

    # parse-review
    p_pr = sub.add_parser(
        "parse-review",
        help="Parse review body from stdin, output counts as JSON",
    )
    p_pr.set_defaults(func=cmd_parse_review)

    args = parser.parse_args()
    sys.exit(args.func(args))
