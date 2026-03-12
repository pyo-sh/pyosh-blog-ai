import argparse
import json
import sys
from pathlib import Path

_AREA_CHOICES = ["client", "server", "workspace"]


def _get_monorepo_root() -> Path:
    from .paths import find_monorepo_root
    return find_monorepo_root()


def cmd_run(args) -> int:
    """Dispatch review for an issue (acquires/releases lease automatically)."""
    monorepo_root = _get_monorepo_root()
    from .review_runner import dispatch_review
    from .lease import lease_acquire, lease_release, LeaseConflictError

    owner = args.owner
    try:
        acquired = lease_acquire(args.issue, args.area, monorepo_root, owner=owner)
    except LeaseConflictError as e:
        print(str(e), file=sys.stderr)
        return 1

    # Release condition: acquired=True (we created the lease), OR acquired=False
    # AND rc != 3 (we are a resume/retry — the original holder crashed, not still running).
    # rc=3 means dispatch_review() found another active process and bailed out;
    # in that case we must NOT release since the active process still holds the lease.
    # rc=None means dispatch_review() raised an exception — we are done, release.
    rc = None
    try:
        rc = dispatch_review(
            issue=args.issue,
            area=args.area,
            pr=args.pr,
            monorepo_root=monorepo_root,
            tool=args.tool,
            model=args.model or "",
        )
        return rc
    finally:
        if acquired or rc != 3:
            lease_release(args.issue, args.area, monorepo_root, owner=owner)


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
        state = state_read(args.issue, args.area, monorepo_root)
        print(json.dumps(state.to_dict(), indent=2))
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
    from .lease import lease_check_owner, LeaseConflictError

    # Only the current lease owner (or a free slot) may clean up.
    owner = args.owner
    if not lease_check_owner(args.issue, args.area, monorepo_root, owner):
        from .lease import lease_read
        current = lease_read(args.issue, args.area, monorepo_root)
        print(
            f"[cleanup] issue #{args.issue} area={args.area} lease is held by "
            f"'{current.get('owner')}', not '{owner}' — refusing cleanup",
            file=sys.stderr,
        )
        return 1

    try:
        cleanup(args.issue, args.area, args.branch, args.pr, monorepo_root)
        # Release lease after successful cleanup
        from .lease import lease_release
        lease_release(args.issue, args.area, monorepo_root, owner=owner)
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


def cmd_init(args) -> int:
    """Create pipeline directories for an area. Optionally create initial state file."""
    monorepo_root = _get_monorepo_root()
    from .paths import pipeline_init, area_repo_dir, pipeline_worktree_path
    from .state_store import state_exists, state_write
    from .models import PipelineState, PipelineStep, Paths

    try:
        pipeline_init(args.area, monorepo_root)
        if args.issue is not None and not state_exists(args.issue, args.area, monorepo_root):
            state = PipelineState(
                issue=args.issue,
                area=args.area,
                step=PipelineStep.BUILD,
                paths=Paths(
                    skill_cwd=str(monorepo_root),
                    repo_dir=str(area_repo_dir(args.area, monorepo_root)),
                    worktree_dir=str(pipeline_worktree_path(args.issue, args.area, monorepo_root)),
                ),
            )
            state_write(args.issue, args.area, monorepo_root, state)
        return 0
    except Exception as e:
        print(str(e), file=sys.stderr)
        return 1


def cmd_state_update(args) -> int:
    """Update specific fields in pipeline state."""
    monorepo_root = _get_monorepo_root()
    from .state_store import state_exists, state_update

    if not state_exists(args.issue, args.area, monorepo_root):
        print(
            f"No state found for issue #{args.issue} area={args.area}",
            file=sys.stderr,
        )
        return 1

    updates = {}
    if args.step is not None:
        updates["step"] = args.step
    if args.last_review_id is not None:
        updates["lastReviewId"] = args.last_review_id
    if args.last_commit_sha is not None:
        updates["lastCommitSha"] = args.last_commit_sha
    if args.skip_review is not None:
        updates["skipReview"] = args.skip_review
    if args.review_resolve_round is not None:
        updates["reviewResolveRound"] = args.review_resolve_round
    if args.pr is not None:
        updates["pr"] = args.pr
    if args.branch is not None:
        updates["branch"] = args.branch

    if not updates:
        print("No fields to update", file=sys.stderr)
        return 2

    try:
        state_update(args.issue, args.area, monorepo_root, updates)
        return 0
    except Exception as e:
        print(str(e), file=sys.stderr)
        return 2


def cmd_stage_retry(args) -> int:
    """Increment stage retry counter, optionally append recovery log."""
    monorepo_root = _get_monorepo_root()
    from .state_store import recovery_log_append, stage_retry, state_exists

    if not state_exists(args.issue, args.area, monorepo_root):
        print(
            f"No state found for issue #{args.issue} area={args.area}",
            file=sys.stderr,
        )
        return 2

    if args.error and args.action and args.result:
        recovery_log_append(
            args.issue, args.area, monorepo_root,
            args.stage, args.error, args.action, args.result,
        )

    allowed = stage_retry(args.issue, args.area, monorepo_root, args.stage)
    if allowed:
        return 0
    else:
        return 1


def cmd_check_review(args) -> int:
    """Check GitHub for an existing actionable review."""
    from .github_client import check_review_exists

    try:
        review_id = check_review_exists(
            args.area, args.pr, args.last_review_id,
        )
        if review_id is not None:
            print(review_id)
            return 0
        return 1
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 2


def cmd_sync_state(args) -> int:
    """Sync state fields from GitHub/git (resume self-healing)."""
    monorepo_root = _get_monorepo_root()
    from .state_store import state_exists, state_update, state_read
    from .github_client import check_review_exists, get_pr_head_sha

    if not state_exists(args.issue, args.area, monorepo_root):
        print(
            f"No state found for issue #{args.issue} area={args.area}",
            file=sys.stderr,
        )
        return 1

    state = state_read(args.issue, args.area, monorepo_root)
    updates = {}

    if state.pr:
        # Sync PR head SHA from GitHub
        try:
            sha = get_pr_head_sha(args.area, state.pr)
            if sha and sha != state.last_commit_sha:
                updates["lastCommitSha"] = sha
                print(f"[sync-state] lastCommitSha: {state.last_commit_sha!r} -> {sha!r}")
        except Exception as e:
            print(f"[sync-state] warning: could not fetch PR head SHA: {e}", file=sys.stderr)

        # Sync latest review ID from GitHub (bidirectional).
        # Pass last_review_id=0 to get the actual max matching review ID.
        # When None (no actionable reviews), treat actual_max=0 so a corrupt
        # high watermark (e.g., 9999) is reset and future reviews are not skipped.
        try:
            review_id = check_review_exists(args.area, state.pr, 0)
            actual_max = review_id if review_id is not None else 0
            if actual_max != state.last_review_id:
                updates["lastReviewId"] = actual_max
                print(f"[sync-state] lastReviewId: {state.last_review_id} -> {actual_max}")
        except Exception as e:
            print(f"[sync-state] warning: could not fetch review ID: {e}", file=sys.stderr)

    if updates:
        try:
            state_update(args.issue, args.area, monorepo_root, updates)
        except Exception as e:
            print(str(e), file=sys.stderr)
            return 1
        print(f"[sync-state] updated {list(updates.keys())}")
    else:
        print("[sync-state] no updates needed")

    return 0


def cmd_acquire_lease(args) -> int:
    """Acquire issue lease before pipeline operations."""
    monorepo_root = _get_monorepo_root()
    from .lease import lease_acquire, LeaseConflictError

    try:
        lease_acquire(
            args.issue, args.area, monorepo_root,
            owner=args.owner,
            batch_id=args.batch_id or "",
        )
        return 0
    except LeaseConflictError as e:
        print(str(e), file=sys.stderr)
        return 1
    except Exception as e:
        print(str(e), file=sys.stderr)
        return 2


def cmd_release_lease(args) -> int:
    """Release issue lease after pipeline operations."""
    monorepo_root = _get_monorepo_root()
    from .lease import lease_release

    lease_release(args.issue, args.area, monorepo_root, owner=args.owner)
    return 0


def cmd_check_lease(args) -> int:
    """Print current lease owner. Exit 0 if held by expected owner or free, 1 if conflict."""
    monorepo_root = _get_monorepo_root()
    from .lease import lease_read

    current = lease_read(args.issue, args.area, monorepo_root)
    if current is None:
        print("(no lease)")
        return 0
    print(json.dumps(current, indent=2))
    if args.expected_owner and current.get("owner") != args.expected_owner:
        return 1
    return 0


def cmd_step(args) -> int:
    """Execute a pipeline step and output action:data: routing result."""
    monorepo_root = _get_monorepo_root()
    from .steps import (
        step_build_setup,
        step_build_finalize,
        step_review_dispatch,
        step_review_wait,
        step_review_process,
        step_resolve_setup,
        step_resolve_finalize,
        step_merge,
        step_log_finalize,
    )

    name = args.name
    phase = getattr(args, "phase", None)

    dispatch = {
        ("build", "setup"): lambda: step_build_setup(args.issue, args.area, monorepo_root),
        ("build", "finalize"): lambda: step_build_finalize(args.issue, args.area, monorepo_root),
        ("review-dispatch", None): lambda: step_review_dispatch(
            args.issue, args.area, monorepo_root, tool=args.tool,
        ),
        ("review-wait", None): lambda: step_review_wait(args.issue, args.area, monorepo_root),
        ("review-process", None): lambda: step_review_process(
            args.issue, args.area, monorepo_root, review_id=args.review_id,
        ),
        ("resolve", "setup"): lambda: step_resolve_setup(args.issue, args.area, monorepo_root),
        ("resolve", "finalize"): lambda: step_resolve_finalize(args.issue, args.area, monorepo_root),
        ("merge", None): lambda: step_merge(args.issue, args.area, monorepo_root),
        ("log", "finalize"): lambda: step_log_finalize(args.issue, args.area, monorepo_root),
    }
    fn = dispatch.get((name, phase))
    if fn is None:
        print(f"Unknown step/phase: {name}/{phase}", file=sys.stderr)
        return 2

    try:
        result = fn()
        print(f"action:{result.action}")
        print(f"data:{json.dumps(result.data)}")
        if result.message:
            print(result.message, file=sys.stderr)
        return 0
    except Exception as e:
        print("action:error")
        print(f"data:{json.dumps({'error': str(e)})}")
        print(f"[step:{name}] {e}", file=sys.stderr)
        return 1


def cmd_check_commits(args) -> int:
    """Check GitHub for new commits on a PR."""
    from .github_client import check_new_commits

    try:
        new_sha = check_new_commits(args.area, args.pr, args.last_commit_sha)
        if new_sha is not None:
            print(new_sha)
            return 0
        return 1
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 2


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
    p_run.add_argument("--owner", default="pipeline", choices=["manual", "pipeline", "orchestrator"],
                       help="Lease owner for this dispatch (default: pipeline)")
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
    p_cleanup.add_argument("--owner", default="pipeline", choices=["manual", "pipeline", "orchestrator"],
                           help="Lease owner asserting cleanup rights (default: pipeline)")
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

    # init
    p_init = sub.add_parser("init", help="Create pipeline directories for an area")
    p_init.add_argument("--area", required=True, choices=_AREA_CHOICES)
    p_init.add_argument("--issue", type=int, default=None,
                        help="Create initial state file for this issue")
    p_init.set_defaults(func=cmd_init)

    # state-update
    p_su = sub.add_parser("state-update", help="Update fields in pipeline state")
    p_su.add_argument("--issue", type=int, required=True)
    p_su.add_argument("--area", required=True, choices=_AREA_CHOICES)
    p_su.add_argument("--step")
    p_su.add_argument("--last-review-id", type=int)
    p_su.add_argument("--last-commit-sha")
    p_su.add_argument("--skip-review", type=lambda v: v.lower() in ("true", "1", "yes"))
    p_su.add_argument("--review-resolve-round", type=int)
    p_su.add_argument("--pr", type=int)
    p_su.add_argument("--branch")
    p_su.set_defaults(func=cmd_state_update)

    # stage-retry
    p_sr = sub.add_parser("stage-retry", help="Increment stage retry counter")
    p_sr.add_argument("--issue", type=int, required=True)
    p_sr.add_argument("--area", required=True, choices=_AREA_CHOICES)
    p_sr.add_argument("--stage", required=True)
    p_sr.add_argument("--error", default="")
    p_sr.add_argument("--action", default="")
    p_sr.add_argument("--result", default="")
    p_sr.set_defaults(func=cmd_stage_retry)

    # check-review
    p_cr = sub.add_parser("check-review", help="Check for existing actionable review")
    p_cr.add_argument("--area", required=True, choices=_AREA_CHOICES)
    p_cr.add_argument("--pr", type=int, required=True)
    p_cr.add_argument("--last-review-id", type=int, default=0)
    p_cr.set_defaults(func=cmd_check_review)

    # check-commits
    p_cc = sub.add_parser("check-commits", help="Check for new commits on a PR")
    p_cc.add_argument("--area", required=True, choices=_AREA_CHOICES)
    p_cc.add_argument("--pr", type=int, required=True)
    p_cc.add_argument("--last-commit-sha", required=True)
    p_cc.set_defaults(func=cmd_check_commits)

    # sync-state
    p_ss = sub.add_parser("sync-state", help="Sync state from GitHub/git (resume self-healing)")
    p_ss.add_argument("--issue", type=int, required=True)
    p_ss.add_argument("--area", required=True, choices=_AREA_CHOICES)
    p_ss.set_defaults(func=cmd_sync_state)

    # acquire-lease
    p_al = sub.add_parser("acquire-lease", help="Acquire issue lease before pipeline operations")
    p_al.add_argument("--issue", type=int, required=True)
    p_al.add_argument("--area", required=True, choices=_AREA_CHOICES)
    p_al.add_argument("--owner", required=True, choices=["manual", "pipeline", "orchestrator"])
    p_al.add_argument("--batch-id", default="")
    p_al.set_defaults(func=cmd_acquire_lease)

    # release-lease
    p_rl = sub.add_parser("release-lease", help="Release issue lease after pipeline operations")
    p_rl.add_argument("--issue", type=int, required=True)
    p_rl.add_argument("--area", required=True, choices=_AREA_CHOICES)
    p_rl.add_argument("--owner", required=True, choices=["manual", "pipeline", "orchestrator"])
    p_rl.set_defaults(func=cmd_release_lease)

    # step
    _STEP_CHOICES = [
        "build", "review-dispatch", "review-wait", "review-process",
        "resolve", "merge", "log",
    ]
    p_step = sub.add_parser("step", help="Execute a pipeline step")
    p_step.add_argument("name", choices=_STEP_CHOICES)
    p_step.add_argument("--issue", type=int, required=True)
    p_step.add_argument("--area", required=True, choices=_AREA_CHOICES)
    p_step.add_argument("--phase", choices=["setup", "finalize"])
    p_step.add_argument("--review-id", type=int, default=0)
    p_step.add_argument("--tool", default="claude")
    p_step.set_defaults(func=cmd_step)

    # check-lease
    p_cl = sub.add_parser("check-lease", help="Print current lease owner for an issue")
    p_cl.add_argument("--issue", type=int, required=True)
    p_cl.add_argument("--area", required=True, choices=_AREA_CHOICES)
    p_cl.add_argument("--expected-owner", default="")
    p_cl.set_defaults(func=cmd_check_lease)

    args = parser.parse_args()
    sys.exit(args.func(args))
