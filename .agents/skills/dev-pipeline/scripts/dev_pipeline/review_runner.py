import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .command_runner import run
from .paths import (
    area_repo_dir,
    area_repo_name,
    pipeline_err_path,
    pipeline_headless_meta_path,
    pipeline_log_path,
    pipeline_message_path,
    pipeline_init,
    resolve_worktree_path,
)
from .models import ReviewJobStatus
from .state_store import recovery_log_append, state_read, state_update

# Stale review job timeout (seconds). Jobs running longer than this are
# considered stuck and eligible for reclaim.
REVIEW_JOB_STALE_TIMEOUT_SECS = 1800  # 30 minutes


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _review_prompt(
    issue: int,
    area: str,
    pr: int,
    monorepo_root: str,
    repo: str,
    repo_dir: str,
) -> str:
    return f"""/dev-review
Target issue: #{issue}
Target PR: #{pr}
Target area: {area}
GitHub repo: {repo}
Repo dir on disk: {repo_dir}
Session skill root: {monorepo_root}

Rules:
- Skills must resolve from {monorepo_root}. Do not change that assumption.
- For GitHub commands, use either "gh ... -R {repo}" or work from "{repo_dir}" explicitly.
- Do not assume the process cwd is the repo checkout.
- Review only the PR diff and directly necessary context.
- After posting the review, exit immediately.
"""


def _write_job_meta(
    meta_path: Path,
    *,
    status: str,
    issue: int,
    area: str,
    stage: str,
    pr: int,
    repo: str,
    repo_dir: str,
    worktree_dir: str,
    skill_cwd: str,
    log_path: str,
    err_path: str,
    tool: str,
    model: str,
    exit_code: Optional[int] = None,
) -> None:
    # Preserve startedAt from previous meta when transitioning from running to done
    started_at = None
    if status == "running":
        started_at = _now_iso()
    else:
        try:
            prev = json.loads(meta_path.read_text())
            started_at = prev.get("startedAt")
        except Exception:
            pass

    data = {
        "status": status,
        "tool": tool,
        "issue": issue,
        "area": area,
        "stage": stage,
        "pr": pr,
        "repo": repo,
        "repoDir": repo_dir,
        "worktreeDir": worktree_dir,
        "skillCwd": skill_cwd,
        "log": str(log_path),
        "err": str(err_path),
        "model": model,
        "startedAt": started_at,
        "finishedAt": _now_iso() if status != "running" else None,
        "exitCode": exit_code,
    }
    tmp = str(meta_path) + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, str(meta_path))


def dispatch_review(
    issue: int,
    area: str,
    pr: int,
    monorepo_root: Path,
    tool: str = "claude",
    model: str = "",
) -> int:
    """Dispatch a review subprocess. Returns exit code."""
    repo = area_repo_name(area)

    # Duplicate dispatch guard with stale detection
    try:
        state = state_read(issue, area, monorepo_root)
        if state.review_job.status == ReviewJobStatus.RUNNING:
            if state.review_job.is_stale(REVIEW_JOB_STALE_TIMEOUT_SECS):
                print(
                    f"[review_runner] stale review job detected for issue #{issue} "
                    f"area={area} (startedAt={state.review_job.started_at}) - reclaiming",
                    file=sys.stderr,
                )
                recovery_log_append(
                    issue, area, monorepo_root,
                    "review_dispatch",
                    f"stale review job (runId={state.review_job.run_id})",
                    "reclaim",
                    "proceeding with new dispatch",
                )
            else:
                print(
                    f"[review_runner] review job already running for issue #{issue} "
                    f"area={area} - duplicate dispatch prevented",
                    file=sys.stderr,
                )
                return 3  # "already running" — distinct from error (1) or unknown tool (2)
    except Exception:
        pass

    run_id = f"review-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{os.getpid()}"

    try:
        state_update(issue, area, monorepo_root, {
            "reviewJob": {
                "runId": run_id,
                "status": "running",
                "startedAt": _now_iso(),
                "finishedAt": None,
                "tool": tool,
                "model": model,
            }
        })
    except Exception:
        pass

    if tool == "claude":
        rc = _dispatch_claude(issue, area, pr, monorepo_root, model)
    elif tool == "codex":
        rc = _dispatch_codex(issue, area, pr, monorepo_root, model)
    else:
        print(f"[review_runner] unknown tool: {tool}", file=sys.stderr)
        rc = 2

    try:
        # Do not overwrite failed_parse with generic "failed":
        # _dispatch_codex() may have already written failed_parse, which needs
        # to survive so callers can route to a separate recovery path.
        current_status = None
        try:
            current_status = state_read(issue, area, monorepo_root).review_job.status
        except Exception:
            pass

        if current_status == ReviewJobStatus.FAILED_PARSE:
            state_update(issue, area, monorepo_root, {
                "reviewJob": {"finishedAt": _now_iso()}
            })
        else:
            status = "success" if rc == 0 else "failed"
            state_update(issue, area, monorepo_root, {
                "reviewJob": {"status": status, "finishedAt": _now_iso()}
            })
    except Exception:
        pass

    return rc


def _dispatch_claude(
    issue: int,
    area: str,
    pr: int,
    monorepo_root: Path,
    model: str = "",
) -> int:
    repo = area_repo_name(area)
    pipeline_init(area, monorepo_root)

    log = pipeline_log_path(issue, area, "review", monorepo_root)
    err = pipeline_err_path(issue, area, "review", monorepo_root)
    meta = pipeline_headless_meta_path(issue, area, "review", monorepo_root)
    repo_dir = str(area_repo_dir(area, monorepo_root))

    prompt = _review_prompt(issue, area, pr, str(monorepo_root), repo, repo_dir)

    _write_job_meta(
        meta,
        status="running",
        issue=issue,
        area=area,
        stage="review",
        pr=pr,
        repo=repo,
        repo_dir=repo_dir,
        worktree_dir="",
        skill_cwd=str(monorepo_root),
        log_path=str(log),
        err_path=str(err),
        tool="claude",
        model=model,
    )

    cmd = [
        "claude",
        "-p",
        "--dangerously-skip-permissions",
        "--no-session-persistence",
        "--allowedTools", "Bash,Read,Skill",
        "--max-turns", "15",
    ]
    if model:
        cmd += ["--model", model]
    cmd.append(prompt)

    env_extra = {
        "PIPELINE_MONOREPO_ROOT": str(monorepo_root),
        "PIPELINE_AREA": area,
        "PIPELINE_REPO": repo,
        "PIPELINE_REPO_DIR": repo_dir,
        "PIPELINE_WORKTREE_DIR": "",
        "PIPELINE_STAGE": "review",
        "PIPELINE_ISSUE": str(issue),
        "PIPELINE_PR": str(pr),
    }
    # Strip CLAUDECODE from env to avoid nesting issues
    clean_env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    clean_env.update(env_extra)

    print(
        f"[review_runner:subprocess] start tool=claude stage=review "
        f"issue=#{issue} area={area} pr=#{pr} cwd={monorepo_root}",
        file=sys.stderr,
    )
    result = run(cmd, cwd=str(monorepo_root), env=clean_env, timeout=900, capture_output=True, replace_env=True)
    print(
        f"[review_runner:subprocess] end tool=claude stage=review "
        f"issue=#{issue} rc={result.rc}",
        file=sys.stderr,
    )

    log.write_text(result.stdout)
    err.write_text(result.stderr)

    status = "success" if result.rc == 0 else ("timeout" if result.timed_out else "error")
    _write_job_meta(
        meta,
        status=status,
        issue=issue,
        area=area,
        stage="review",
        pr=pr,
        repo=repo,
        repo_dir=repo_dir,
        worktree_dir="",
        skill_cwd=str(monorepo_root),
        log_path=str(log),
        err_path=str(err),
        tool="claude",
        model=model,
        exit_code=result.rc,
    )

    return result.rc


def normalize_codex_output(raw: str) -> str | None:
    """Extract review content from Codex transcript output.

    Searches for the last '## Review Summary' occurrence in the raw transcript.
    Codex may produce multi-turn output; we extract the final review block.

    Returns:
        The review body starting with '## Review Summary' if found.
        None if the input is empty, whitespace-only, or contains no '## Review Summary'.

    Callers must treat None as a parse failure and must NOT upload raw content
    to GitHub. Save the raw transcript as a local artifact instead.
    """
    if not raw or not raw.strip():
        return None

    marker = "## Review Summary"
    idx = raw.rfind(marker)
    if idx == -1:
        return None

    extracted = raw[idx:].rstrip() + "\n"
    return extracted


def _dispatch_codex(
    issue: int,
    area: str,
    pr: int,
    monorepo_root: Path,
    model: str = "",
) -> int:
    from .github_client import get_pr_base_ref

    repo = area_repo_name(area)
    pipeline_init(area, monorepo_root)

    worktree_dir = resolve_worktree_path(issue, area, monorepo_root)
    if not worktree_dir:
        print(
            f"[review_runner] codex review requires worktree for "
            f"issue #{issue} area={area}",
            file=sys.stderr,
        )
        return 1

    repo_dir = str(area_repo_dir(area, monorepo_root))
    log = pipeline_log_path(issue, area, "review", monorepo_root)
    err = pipeline_err_path(issue, area, "review", monorepo_root)
    meta = pipeline_headless_meta_path(issue, area, "review", monorepo_root)

    base_ref = get_pr_base_ref(area, pr)

    cmd = [
        "codex", "exec", "review",
        "--base", f"origin/{base_ref}",
        "--dangerously-bypass-approvals-and-sandbox",
    ]
    if model:
        cmd += ["--model", model]

    _write_job_meta(
        meta,
        status="running",
        issue=issue,
        area=area,
        stage="review",
        pr=pr,
        repo=repo,
        repo_dir=repo_dir,
        worktree_dir=str(worktree_dir),
        skill_cwd=str(monorepo_root),
        log_path=str(log),
        err_path=str(err),
        tool="codex",
        model=model,
    )

    print(
        f"[review_runner:subprocess] start tool=codex stage=review "
        f"issue=#{issue} area={area} pr=#{pr} cwd={worktree_dir}",
        file=sys.stderr,
    )
    result = run(cmd, cwd=str(worktree_dir), timeout=900, capture_output=True)
    print(
        f"[review_runner:subprocess] end tool=codex stage=review "
        f"issue=#{issue} rc={result.rc}",
        file=sys.stderr,
    )

    # Codex writes review content to stderr; stdout is empty
    log.write_text(result.stderr)
    err.write_text("")

    status = "success" if result.rc == 0 else ("timeout" if result.timed_out else "error")
    _write_job_meta(
        meta,
        status=status,
        issue=issue,
        area=area,
        stage="review",
        pr=pr,
        repo=repo,
        repo_dir=repo_dir,
        worktree_dir=str(worktree_dir),
        skill_cwd=str(monorepo_root),
        log_path=str(log),
        err_path=str(err),
        tool="codex",
        model=model,
        exit_code=result.rc,
    )

    # Post codex review output to GitHub
    if result.rc == 0:
        from .github_client import post_review_comment

        if not log.exists() or log.stat().st_size == 0:
            print(
                f"[review_runner] codex exited 0 but produced no output for "
                f"issue #{issue} area={area} pr=#{pr}",
                file=sys.stderr,
            )
            try:
                state_update(issue, area, monorepo_root, {
                    "reviewJob": {"status": "failed_parse", "finishedAt": _now_iso()}
                })
            except Exception:
                pass
            return 1

        raw = log.read_text()
        normalized = normalize_codex_output(raw)
        if normalized is None:
            # fail-closed: parse failed, do NOT upload raw transcript to GitHub.
            # Raw output is already saved in the log artifact for local inspection.
            print(
                f"[review_runner] codex output missing '## Review Summary' for "
                f"issue #{issue} area={area} pr=#{pr} - "
                f"setting failed_parse, artifact saved at {log}",
                file=sys.stderr,
            )
            try:
                state_update(issue, area, monorepo_root, {
                    "reviewJob": {"status": "failed_parse", "finishedAt": _now_iso()}
                })
            except Exception:
                pass
            return 1

        msg_file = pipeline_message_path(area, pr, "review", monorepo_root)
        msg_file.write_text(normalized)
        try:
            post_review_comment(area, pr, str(msg_file))
        except Exception as e:
            print(
                f"[review_runner] failed to post codex review for "
                f"issue #{issue} area={area} pr=#{pr}: {e}",
                file=sys.stderr,
            )
            return 1
        finally:
            msg_file.unlink(missing_ok=True)

    return result.rc
