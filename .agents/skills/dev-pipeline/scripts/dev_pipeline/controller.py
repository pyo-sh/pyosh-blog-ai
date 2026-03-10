import json
import sys
from pathlib import Path
from typing import Optional

from .state_store import state_read


def format_escalation(issue: int, area: str, stage: str, monorepo_root: Path) -> str:
    """Return a multi-line escalation message for the given stage."""
    try:
        state = state_read(issue, area, monorepo_root)
    except Exception as e:
        return f"[pipeline] ESCALATION: stage {stage} failed. Unable to read state: {e}"

    transition_log = state.get("transitionLog", [])
    last_transition = "none"
    if transition_log:
        last = transition_log[-1]
        last_transition = f"{last.get('from')} -> {last.get('to')}"

    recovery = state.get("recoveryLog", [])
    recovery_lines = [
        f"  [{r.get('timestamp')}] {r.get('error')} -> {r.get('action')} -> {r.get('result')}"
        for r in recovery
        if r.get("stage") == stage
    ] or ["  (none)"]

    paths = state.get("paths", {})
    worktree = paths.get("worktreeDir", "N/A")
    repo = paths.get("repoDir", "N/A")

    lines = [
        f"[pipeline] ESCALATION: stage {stage} failed (max retries reached).",
        "",
        "Current state:",
        f"  step:         {state.get('step')}",
        f"  PR:           #{state.get('pr', 0)}",
        f"  branch:       {state.get('branch', '')}",
        f"  round:        {state.get('reviewResolveRound', 0)}/{state.get('maxReviewResolveRounds', 5)}",
        f"  review job:   {state.get('reviewJob', {}).get('status', 'n/a')} "
        f"(runId: {state.get('reviewJob', {}).get('runId', 'n/a')})",
        "",
        f"Last successful transition: {last_transition}",
        "",
        "Stage retry log:",
        *recovery_lines,
        "",
        f"Worktree: {worktree}",
        f"Repo:     {repo}",
        "",
        "Manual action:",
        f"  1. Inspect: git -C {worktree} status",
        f"  2. Resume:  /dev-pipeline {area} #{issue}",
    ]
    return "\n".join(lines)


def merge_pr(
    issue: int, area: str, pr: int, branch: str, monorepo_root: Path
) -> None:
    """Acquire lock, sync branch, merge PR via gh, release lock."""
    from .merge_lock import MergeLock
    from .git_ops import (
        fetch,
        merge_abort,
        merge_no_edit,
        push_safely,
        rebase,
        rebase_abort,
    )
    from .github_client import _repo, get_pr_state, merge_pr_squash
    from .paths import resolve_worktree_path

    repo = _repo(area)
    area_dirs = {
        "client": str(monorepo_root / "client"),
        "server": str(monorepo_root / "server"),
        "workspace": str(monorepo_root),
    }
    repo_dir = area_dirs.get(area, str(monorepo_root))
    worktree_dir = resolve_worktree_path(issue, area, monorepo_root)

    lock = MergeLock(area, issue, monorepo_root)
    with lock:
        if worktree_dir and worktree_dir.is_dir():
            wt = str(worktree_dir)
            # Clean up any in-progress operations
            merge_abort(wt)
            rebase_abort(wt)

            if not fetch(wt):
                raise RuntimeError(
                    f"[controller] git fetch failed in worktree {wt}"
                )

            if not rebase(wt, "origin/main"):
                rebase_abort(wt)
                if not merge_no_edit(wt, "origin/main"):
                    raise RuntimeError(
                        f"[controller] both rebase and merge failed in worktree {wt}"
                    )

            if not push_safely(wt):
                raise RuntimeError(
                    f"[controller] git push failed in worktree {wt}"
                )
        else:
            print(
                f"[controller] worktree missing for issue #{issue} area={area}; "
                "skipping branch sync",
                file=sys.stderr,
            )

        merge_pr_squash(area, pr, repo_dir)

        pr_state = get_pr_state(area, pr)
        if pr_state != "MERGED":
            raise RuntimeError(
                f"[controller] gh pr merge returned without MERGED state for PR #{pr}"
            )


def cleanup(
    issue: int, area: str, branch: str, pr: int, monorepo_root: Path
) -> None:
    """Remove artifacts, worktree, branch, and state file."""
    from .paths import (
        pipeline_err_path,
        pipeline_headless_meta_path,
        pipeline_log_path,
        pipeline_message_path,
        resolve_worktree_path,
    )
    from .git_ops import branch_delete, worktree_remove
    from .state_store import state_delete

    area_dirs = {
        "client": str(monorepo_root / "client"),
        "server": str(monorepo_root / "server"),
        "workspace": str(monorepo_root),
    }
    repo_dir = area_dirs.get(area, str(monorepo_root))

    for path in [
        pipeline_log_path(issue, area, "review", monorepo_root),
        pipeline_err_path(issue, area, "review", monorepo_root),
        pipeline_headless_meta_path(issue, area, "review", monorepo_root),
    ]:
        path.unlink(missing_ok=True)

    if pr:
        pipeline_message_path(area, pr, "response", monorepo_root).unlink(missing_ok=True)

    wt = resolve_worktree_path(issue, area, monorepo_root)
    if wt and wt.is_dir():
        worktree_remove(repo_dir, str(wt), force=True)

    branch_delete(repo_dir, branch)
    state_delete(issue, area, monorepo_root)


def list_pipelines(monorepo_root: Path) -> list:
    """Return list of active pipeline state summaries."""
    pipeline_dir = monorepo_root / ".workspace" / "pipeline"
    results = []
    if not pipeline_dir.is_dir():
        return results
    for f in pipeline_dir.glob("*/issue-*.state.json"):
        try:
            data = json.loads(f.read_text())
            results.append({
                "issue": data.get("issue"),
                "area": data.get("area"),
                "step": data.get("step"),
                "pr": data.get("pr", 0),
            })
        except Exception:
            pass
    return results
