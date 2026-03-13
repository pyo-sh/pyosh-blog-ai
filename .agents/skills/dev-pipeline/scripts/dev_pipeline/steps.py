"""High-level step functions for the dev-pipeline state machine.

Each function encapsulates one pipeline step's logic (area mapping, state I/O,
GitHub/Git calls, idempotency) and returns a StepResult that the SKILL.md
caller uses for routing.

Signature convention:
    step_*(issue, area, monorepo_root, **kwargs) -> StepResult
"""

import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .command_runner import run as run_cmd
from .controller import MergeConflictError, cleanup, cleanup_worktree, cleanup_state, merge_pr
from .git_ops import (
    add_all,
    commit,
    fetch,
    fetch_prune,
    has_staged_changes,
    is_clean,
    merge_no_edit,
    push_safely,
    rebase,
    rev_parse_head,
)
from .github_client import (
    check_new_commits,
    check_review_exists,
    fetch_review,
    fetch_review_comments,
    get_pr_state,
)
from .models import PipelineState, PipelineStep, ReviewJobStatus, Paths
from .paths import (
    area_repo_dir,
    area_repo_name,
    pipeline_init,
    pipeline_worktree_path,
)
from .review_normalizer import parse_review_body
from .state_store import (
    log_transition,
    stage_retry,
    state_exists,
    state_read,
    state_update,
    state_write,
)


@dataclass
class StepResult:
    action: str
    data: dict = field(default_factory=dict)
    message: str = ""


# ---------------------------------------------------------------------------
# All failed_* statuses that warrant codex -> claude fallback
# ---------------------------------------------------------------------------
_FAILED_STATUSES = frozenset({
    ReviewJobStatus.FAILED,
    ReviewJobStatus.FAILED_PARSE,
    ReviewJobStatus.FAILED_AUTH,
    ReviewJobStatus.FAILED_PUBLISH,
    ReviewJobStatus.FAILED_POSTCONDITION,
    ReviewJobStatus.FAILED_DISPATCH,
})


# ---------------------------------------------------------------------------
# 1. build
# ---------------------------------------------------------------------------

def step_build_setup(issue: int, area: str, monorepo_root: Path) -> StepResult:
    """Pre-/dev-build setup: init dirs, sync origin/main, create initial state."""
    pipeline_init(area, monorepo_root)

    repo_dir = area_repo_dir(area, monorepo_root)
    repo_name = area_repo_name(area)
    wt_path = pipeline_worktree_path(issue, area, monorepo_root)

    fetch(str(repo_dir))
    if not rebase(str(repo_dir), "origin/main"):
        merge_no_edit(str(repo_dir), "origin/main")

    if not state_exists(issue, area, monorepo_root):
        state = PipelineState(
            issue=issue,
            area=area,
            step=PipelineStep.BUILD,
            paths=Paths(
                skill_cwd=str(monorepo_root),
                repo_dir=str(repo_dir),
                worktree_dir=str(wt_path),
            ),
        )
        state_write(issue, area, monorepo_root, state)

    return StepResult(
        action="ready",
        data={
            "repoDir": str(repo_dir),
            "repo": repo_name,
            "worktreePath": str(wt_path),
        },
        message=f"[step:build:setup] area={area} repo={repo_name} ready for /dev-build",
    )


def step_build_finalize(issue: int, area: str, monorepo_root: Path) -> StepResult:
    """Post-/dev-build: read PR/branch/SHA from worktree, update state."""
    wt_path = pipeline_worktree_path(issue, area, monorepo_root)
    repo_name = area_repo_name(area)

    branch_result = run_cmd(
        ["git", "-C", str(wt_path), "rev-parse", "--abbrev-ref", "HEAD"],
        timeout=10,
    )
    branch = branch_result.stdout.strip()

    sha = rev_parse_head(str(wt_path))
    if not sha:
        return StepResult(
            action="error",
            data={"error": "could not read HEAD from worktree"},
        )

    pr_result = run_cmd(
        [
            "gh", "pr", "list", "-R", repo_name, "--head", branch,
            "--json", "number", "--jq", ".[0].number",
        ],
        timeout=30,
    )
    pr_str = pr_result.stdout.strip()
    if not pr_str:
        return StepResult(
            action="error",
            data={"error": f"no PR found for branch {branch}"},
        )
    pr = int(pr_str)

    state_update(issue, area, monorepo_root, {
        "pr": pr,
        "branch": branch,
        "lastCommitSha": sha,
        "step": "review_dispatch",
    })
    log_transition(issue, area, monorepo_root, "build", "review_dispatch", "build complete")

    return StepResult(
        action="continue",
        data={"pr": pr, "branch": branch, "lastCommitSha": sha},
        message=f"[step:build:finalize] PR=#{pr} branch={branch}",
    )


# ---------------------------------------------------------------------------
# 2a. review_dispatch
# ---------------------------------------------------------------------------

def step_review_dispatch(
    issue: int, area: str, monorepo_root: Path, tool: str = "claude", model: str = "",
) -> StepResult:
    """Check for existing review; if none, prepare for background dispatch."""
    state = state_read(issue, area, monorepo_root)
    pr = state.pr
    last_review_id = state.last_review_id

    try:
        review_id = check_review_exists(area, pr, last_review_id)
    except RuntimeError as e:
        return StepResult(
            action="error",
            data={"error": str(e)},
            message=f"[step:review_dispatch] gh API error: {e}",
        )

    if review_id is not None:
        return StepResult(
            action="found",
            data={"reviewId": review_id, "pr": pr},
            message=f"[step:review_dispatch] existing review found: {review_id}",
        )

    state_update(issue, area, monorepo_root, {
        "step": "review_wait",
        "stageRetries": {"review_dispatch": 0},
    })
    log_transition(
        issue, area, monorepo_root,
        "review_dispatch", "review_wait", f"dispatching with {tool}",
    )

    return StepResult(
        action="dispatch",
        data={"pr": pr, "tool": tool, "model": model, "issue": issue, "area": area},
        message=f"[step:review_dispatch] ready to dispatch with tool={tool}",
    )


# ---------------------------------------------------------------------------
# 2b. review_wait
# ---------------------------------------------------------------------------

def step_review_wait(issue: int, area: str, monorepo_root: Path) -> StepResult:
    """Resume after task-notification: check GitHub for review, handle failures."""
    state = state_read(issue, area, monorepo_root)
    pr = state.pr
    last_review_id = state.last_review_id
    job = state.review_job

    try:
        review_id = check_review_exists(area, pr, last_review_id)
    except RuntimeError as e:
        return StepResult(
            action="error",
            data={"error": str(e)},
            message=f"[step:review_wait] gh API error: {e}",
        )

    if review_id is not None:
        return StepResult(
            action="review",
            data={"reviewId": review_id, "pr": pr},
            message=f"[step:review_wait] review found: {review_id}",
        )

    # No review found - branch on job status

    # failed_postcondition: AI ran but didn't post review. Retry once regardless of tool.
    # Uses a dedicated "review_postcondition" key so the Bug D dispatch reset
    # (which clears "review_dispatch" counter) does not interfere with this budget.
    if job.status == ReviewJobStatus.FAILED_POSTCONDITION:
        can_retry = stage_retry(issue, area, monorepo_root, "review_postcondition")
        if can_retry:
            state_update(issue, area, monorepo_root, {"step": "review_dispatch"})
            return StepResult(
                action="retry",
                data={"tool": job.tool, "reason": "postcondition failed, retrying"},
            )
        # retries exhausted - fall through to existing _FAILED_STATUSES logic

    if job.status in _FAILED_STATUSES:
        if job.tool == "codex":
            can_retry = stage_retry(issue, area, monorepo_root, "review_dispatch")
            if can_retry:
                state_update(issue, area, monorepo_root, {"step": "review_dispatch"})
                return StepResult(
                    action="retry",
                    data={
                        "tool": "claude",
                        "reason": f"codex {job.status.value}, falling back to claude",
                    },
                )
        # claude failed or retries exhausted -> escalate
        return StepResult(
            action="escalate",
            data={
                "reason": (
                    f"review job {job.status.value} (tool={job.tool}), "
                    "retries exhausted"
                ),
            },
            message=f"[step:review_wait] escalate: {job.status.value}",
        )

    # Review job still in progress - caller should poll again
    if job.status == ReviewJobStatus.RUNNING:
        return StepResult(
            action="pending",
            data={"reason": "review job still running"},
            message="[step:review_wait] pending: review job still running",
        )

    # Other status (success but no review posted, etc.)
    return StepResult(
        action="escalate",
        data={"reason": f"job status={job.status.value} but no review on GitHub"},
    )


# ---------------------------------------------------------------------------
# 3. review_process
# ---------------------------------------------------------------------------

def step_review_process(
    issue: int, area: str, monorepo_root: Path, review_id: int,
) -> StepResult:
    """Fetch and parse review, decide next action based on severity counts."""
    state = state_read(issue, area, monorepo_root)
    pr = state.pr

    try:
        review = fetch_review(area, pr, review_id)
    except RuntimeError as e:
        return StepResult(action="escalate", data={"reason": f"fetch review failed: {e}"})

    review_state = review.get("state", "").upper()
    if review_state in ("PENDING", "DISMISSED"):
        return StepResult(
            action="escalate",
            data={"reason": f"review is {review_state}"},
        )

    body = review.get("body", "")
    try:
        counts = parse_review_body(body)
    except (ValueError, Exception) as e:
        return StepResult(action="escalate", data={"reason": f"parse failed: {e}"})

    # Reset retry counters on successful review receipt
    state_update(issue, area, monorepo_root, {
        "lastReviewId": review_id,
        "stageRetries": {
            "review_dispatch": 0,
            "review_wait": 0,
            "review_process": 0,
        },
    })

    counts_dict = {
        "critical": counts.critical,
        "warning": counts.warning,
        "suggestion": counts.suggestion,
    }
    round_num = state.review_resolve_round
    max_rounds = state.max_review_resolve_rounds

    if counts.critical > 0 or counts.warning > 0:
        if round_num >= max_rounds:
            state_update(issue, area, monorepo_root, {
                "roundLimitReachedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            })
            return StepResult(
                action="round_limit",
                data={
                    "counts": counts_dict,
                    "round": round_num,
                    "maxRound": max_rounds,
                },
            )
        state_update(issue, area, monorepo_root, {
            "step": "resolve",
            "reviewResolveRound": round_num + 1,
        })
        return StepResult(
            action="resolve",
            data={
                "counts": counts_dict,
                "round": round_num + 1,
                "reviewId": review_id,
            },
        )

    if counts.suggestion > 0:
        if round_num >= max_rounds:
            return StepResult(action="clean", data={"counts": counts_dict})
        return StepResult(
            action="suggestion_only",
            data={
                "counts": counts_dict,
                "round": round_num + 1,
                "reviewId": review_id,
                "reviewBody": body,
            },
        )

    # All counts 0 -> clean
    return StepResult(action="clean", data={"counts": counts_dict})


# ---------------------------------------------------------------------------
# 3b. suggestion_decide
# ---------------------------------------------------------------------------

def step_suggestion_decide(
    issue: int, area: str, monorepo_root: Path, decision: str,
) -> StepResult:
    """Apply AI's suggestion_only decision: merge, resolve-skip, or resolve-review.

    Called after step_review_process returns action=suggestion_only and the AI
    decides how to handle suggestions.

    Args:
        decision: one of "merge", "resolve-skip", "resolve-review"
    """
    state = state_read(issue, area, monorepo_root)
    round_num = state.review_resolve_round

    if decision == "merge":
        state_update(issue, area, monorepo_root, {
            "step": "merge",
            "reviewResolveRound": round_num + 1,
        })
        log_transition(
            issue, area, monorepo_root,
            "review_process", "merge", "suggestion_only -> merge (skip resolve)",
        )
        return StepResult(action="merge", data={"round": round_num + 1})

    if decision == "resolve-skip":
        state_update(issue, area, monorepo_root, {
            "step": "resolve",
            "skipReview": True,
            "reviewResolveRound": round_num + 1,
        })
        log_transition(
            issue, area, monorepo_root,
            "review_process", "resolve", "suggestion_only -> resolve (skipReview)",
        )
        return StepResult(action="resolve", data={"round": round_num + 1})

    if decision == "resolve-review":
        state_update(issue, area, monorepo_root, {
            "step": "resolve",
            "skipReview": False,
            "reviewResolveRound": round_num + 1,
        })
        log_transition(
            issue, area, monorepo_root,
            "review_process", "resolve", "suggestion_only -> resolve (re-review)",
        )
        return StepResult(action="resolve", data={"round": round_num + 1})

    return StepResult(
        action="error",
        data={"error": f"invalid decision: {decision}"},
    )


# ---------------------------------------------------------------------------
# 4. resolve (setup + finalize)
# ---------------------------------------------------------------------------

def step_resolve_setup(issue: int, area: str, monorepo_root: Path) -> StepResult:
    """Recovery check + fetch review body and inline comments for resolve."""
    state = state_read(issue, area, monorepo_root)
    wt = pipeline_worktree_path(issue, area, monorepo_root)
    pr = state.pr
    review_id = state.last_review_id

    if not wt.exists():
        return StepResult(action="escalate", data={"reason": "worktree not found"})

    local_head = rev_parse_head(str(wt))
    if not local_head:
        return StepResult(
            action="escalate",
            data={"reason": "worktree corrupt - cannot read HEAD"},
        )

    dirty = not is_clean(str(wt))
    last_sha = state.last_commit_sha

    if local_head != last_sha:
        if dirty:
            return StepResult(
                action="recovery",
                data={
                    "reason": "HEAD mismatch + dirty tree",
                    "localHead": local_head,
                    "stateSha": last_sha,
                },
            )
        return StepResult(
            action="recovery",
            data={
                "reason": "HEAD mismatch (clean) - previous commit detected",
                "localHead": local_head,
                "stateSha": last_sha,
            },
        )

    if dirty:
        return StepResult(
            action="recovery",
            data={
                "reason": "matched HEAD but dirty tree - partial resolve from previous session",
            },
        )

    # Check remote for new commits
    try:
        new_sha = check_new_commits(area, pr, last_sha)
    except RuntimeError:
        new_sha = None

    if new_sha:
        return StepResult(
            action="recovery",
            data={
                "reason": "new commits on remote",
                "newSha": new_sha,
                "stateSha": last_sha,
            },
        )

    # Fetch review body + inline comments
    try:
        review_data = fetch_review(area, pr, review_id)
    except RuntimeError as e:
        return StepResult(
            action="escalate",
            data={"reason": f"failed to fetch review: {e}"},
        )

    comments = fetch_review_comments(area, pr, review_id)

    return StepResult(
        action="ready",
        data={
            "reviewBody": review_data.get("body", ""),
            "comments": comments,
            "worktreePath": str(wt),
            "reviewId": review_id,
        },
        message=f"[step:resolve:setup] review loaded, {len(comments)} inline comments",
    )


def step_resolve_finalize(issue: int, area: str, monorepo_root: Path) -> StepResult:
    """Commit/push fixes, update state, decide re-review or merge."""
    state = state_read(issue, area, monorepo_root)
    wt = pipeline_worktree_path(issue, area, monorepo_root)

    add_all(str(wt))

    if has_staged_changes(str(wt)):
        commit(str(wt), f"fix: address review comments (#{issue})")

    push_safely(str(wt))  # always push — ensures remote is in sync even if AI committed directly

    # Always read current HEAD - AI may have committed directly before finalize
    new_sha = rev_parse_head(str(wt))
    if new_sha and new_sha != state.last_commit_sha:
        state_update(issue, area, monorepo_root, {"lastCommitSha": new_sha})

    if state.skip_review:
        state_update(issue, area, monorepo_root, {"step": "merge"})
        log_transition(issue, area, monorepo_root, "resolve", "merge", "skipReview=true")
        return StepResult(action="merge", data={"sha": new_sha or ""})
    else:
        state_update(issue, area, monorepo_root, {"step": "review_dispatch"})
        log_transition(
            issue, area, monorepo_root,
            "resolve", "review_dispatch", "re-review requested",
        )
        return StepResult(action="re_review", data={"sha": new_sha or ""})


# ---------------------------------------------------------------------------
# 5. merge — runs BEFORE log
# ---------------------------------------------------------------------------

def step_merge(issue: int, area: str, monorepo_root: Path) -> StepResult:
    """Check PR state, merge, transition to log."""
    state = state_read(issue, area, monorepo_root)
    pr = state.pr
    branch = state.branch
    repo_dir = area_repo_dir(area, monorepo_root)

    try:
        pr_state = get_pr_state(area, pr)
    except RuntimeError as e:
        return StepResult(action="escalate", data={"reason": f"get_pr_state failed: {e}"})

    if pr_state == "MERGED":
        fetch_prune(str(repo_dir))
        log_transition(issue, area, monorepo_root, "merge", "cleanup_wt", "PR already merged")
        state_update(issue, area, monorepo_root, {"step": "cleanup_wt"})
        return StepResult(action="already_merged", data={"pr": pr})
    if pr_state == "CLOSED":
        return StepResult(action="closed", data={"pr": pr})

    try:
        merge_pr(issue, area, pr, branch, monorepo_root)
    except Exception as e:
        can_retry = stage_retry(issue, area, monorepo_root, "merge")
        error_kind = "conflict" if isinstance(e, MergeConflictError) else "unknown"
        conflict_files = e.files if isinstance(e, MergeConflictError) else []
        if can_retry:
            return StepResult(action="retry", data={
                "error": str(e),
                "errorKind": error_kind,
                "conflictFiles": conflict_files,
            })
        return StepResult(action="escalate", data={
            "reason": f"merge failed: {e}",
            "errorKind": error_kind,
            "conflictFiles": conflict_files,
        })

    fetch_prune(str(repo_dir))
    log_transition(issue, area, monorepo_root, "merge", "cleanup_wt", "PR merged")
    state_update(issue, area, monorepo_root, {"step": "cleanup_wt"})

    return StepResult(action="merged", data={"pr": pr})


# ---------------------------------------------------------------------------
# 5.5. cleanup_wt — remove worktree BEFORE log (state preserved for dev-log)
# ---------------------------------------------------------------------------

def step_cleanup_wt(issue: int, area: str, monorepo_root: Path) -> StepResult:
    """Remove worktree and branch. State file preserved so dev-log can read it."""
    state = state_read(issue, area, monorepo_root)
    pr = state.pr
    branch = state.branch

    cleanup_worktree(issue, area, branch, pr, monorepo_root)
    state_update(issue, area, monorepo_root, {"step": "log"})
    log_transition(issue, area, monorepo_root, "cleanup_wt", "log", "worktree removed")

    return StepResult(action="continue", data={})


# ---------------------------------------------------------------------------
# 6. log (setup + finalize) — runs AFTER cleanup_wt
# ---------------------------------------------------------------------------

def step_log_setup(issue: int, area: str, monorepo_root: Path) -> StepResult:
    """Provide ready signal for /dev-log execution (no worktree needed)."""
    return StepResult(
        action="ready",
        data={},
        message="[step:log:setup] ready for /dev-log",
    )


def step_log_finalize(issue: int, area: str, monorepo_root: Path) -> StepResult:
    """Delete state file and mark pipeline done."""
    log_transition(issue, area, monorepo_root, "log", "done", "dev-log complete")
    cleanup_state(issue, area, monorepo_root)

    return StepResult(action="done", data={})
