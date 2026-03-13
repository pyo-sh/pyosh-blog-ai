import json
import os
import shutil
import subprocess
import sys
import tempfile
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
    pipeline_init,
    resolve_worktree_path,
)
from .models import ReviewJobStatus
from .state_store import recovery_log_append, state_read, state_update

# Stale review job timeout (seconds). Jobs running longer than this are
# considered stuck and eligible for reclaim.
REVIEW_JOB_STALE_TIMEOUT_SECS = 1800  # 30 minutes

# Claude-related env vars that trigger codex external-agent-config detection.
# Stripped from the subprocess environment when dispatching codex.
_CLAUDE_ENV_STRIP = frozenset({
    "CLAUDECODE",
    "CLAUDE_CODE_ENTRYPOINT",
    "CLAUDE_BASH_MAINTAIN_PROJECT_WORKING_DIR",
})

# All terminal statuses that carry explicit failure information.
# dispatch_review() preserves these when they are set by the dispatch function,
# rather than overwriting them with the generic "failed" or "success".
_EXPLICIT_FAILURE_STATUSES = frozenset({
    ReviewJobStatus.FAILED_PARSE,
    ReviewJobStatus.FAILED_AUTH,
    ReviewJobStatus.FAILED_PUBLISH,
    ReviewJobStatus.FAILED_POSTCONDITION,
    ReviewJobStatus.FAILED_DISPATCH,
})


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _detect_codex_auth(env: dict) -> tuple[str, Optional[Path]]:
    """Detect Codex auth mode. Returns (mode, auth_json_path).

    mode is one of: "session", "api", "missing".
    auth_json_path is the path to the auth.json file if mode="session" and
    the file exists in the real CODEX_HOME (may be None for keyring-backed auth).

    Detection order:
    1. Run `codex login status` - if exit 0, session-auth is valid.
    2. If CODEX_API_KEY is present, use API key auth.
    3. Otherwise, auth is missing.
    """
    try:
        proc = subprocess.run(
            ["codex", "login", "status"],
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )
        if proc.returncode == 0:
            # Session-auth is valid. Try to locate file-backed auth.json so the
            # caller can seed it into the isolated CODEX_HOME if needed.
            real_codex_home = Path(env.get("CODEX_HOME") or os.path.expanduser("~/.codex"))
            auth_json = real_codex_home / "auth.json"
            return ("session", auth_json if auth_json.exists() else None)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    if env.get("CODEX_API_KEY"):
        return ("api", None)

    return ("missing", None)


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

    # Read last_review_id before dispatch so the post-condition can require
    # a review newer than any previously seen on the PR.  Default to 0 when
    # no state file exists (first dispatch).
    last_review_id = 0
    try:
        pre_state = state_read(issue, area, monorepo_root)
        last_review_id = pre_state.last_review_id

        # Duplicate dispatch guard with stale detection
        if pre_state.review_job.status == ReviewJobStatus.RUNNING:
            if pre_state.review_job.is_stale(REVIEW_JOB_STALE_TIMEOUT_SECS):
                print(
                    f"[review_runner] stale review job detected for issue #{issue} "
                    f"area={area} (startedAt={pre_state.review_job.started_at}) - reclaiming",
                    file=sys.stderr,
                )
                recovery_log_append(
                    issue, area, monorepo_root,
                    "review_dispatch",
                    f"stale review job (runId={pre_state.review_job.run_id})",
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
        rc = _dispatch_claude(issue, area, pr, monorepo_root, model, last_review_id=last_review_id)
    elif tool == "codex":
        rc = _dispatch_codex(issue, area, pr, monorepo_root, model, last_review_id=last_review_id)
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

        if current_status in _EXPLICIT_FAILURE_STATUSES:
            # Preserve the explicit failure status set by the dispatch function.
            # Only update finishedAt so the status is not overwritten.
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
    last_review_id: int = 0,
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
        "--allowedTools", "Bash,Read,Write,Skill",
        "--max-turns", "30",
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

    if result.rc != 0:
        status = "timeout" if result.timed_out else "error"
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

    # Post-condition: verify the review was actually posted to GitHub.
    # Claude subprocess returning rc=0 does not guarantee a review was published.
    from .github_client import check_review_exists

    def _fail_postcondition_claude(reason: str) -> int:
        print(
            f"[review_runner] claude post-condition failed for "
            f"issue #{issue} area={area} pr=#{pr}: {reason}",
            file=sys.stderr,
        )
        _write_job_meta(
            meta,
            status="failed_postcondition",
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
        try:
            state_update(issue, area, monorepo_root, {
                "reviewJob": {"status": "failed_postcondition", "finishedAt": _now_iso()}
            })
        except Exception:
            pass
        return 1

    try:
        review_id = check_review_exists(area, pr, last_review_id)
        if review_id is None:
            return _fail_postcondition_claude(
                f"no actionable review newer than id={last_review_id} found on GitHub after subprocess success"
            )
    except Exception as exc:
        return _fail_postcondition_claude(f"check_review_exists raised: {exc}")

    _write_job_meta(
        meta,
        status="success",
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
    try:
        state_update(issue, area, monorepo_root, {
            "reviewJob": {"status": "success", "finishedAt": _now_iso()}
        })
    except Exception:
        pass
    return 0


def normalize_codex_output(raw: str) -> str | None:
    """Extract review content from a raw Codex transcript. LOCAL ARTIFACT SALVAGE ONLY.

    This function must NOT be used as the primary GitHub publish path.
    The primary path is: codex structured JSON output -> review_publish.py
    (schema validation + contamination check + markdown rendering + gh publish).
    Use this function only as a fallback for inspecting local transcript artifacts.

    Searches for the last '## Review Summary' that begins at a line start
    (idx == 0 or preceded by a newline). This prevents false-positives from
    occurrences inside backtick spans such as:
        Posts a review beginning with `## Review Summary`.

    Returns:
        The review body starting with '## Review Summary' if found at line start.
        None if the input is empty, whitespace-only, or no line-start match exists.
    """
    if not raw or not raw.strip():
        return None

    marker = "## Review Summary"
    idx = len(raw)
    while True:
        idx = raw.rfind(marker, 0, idx)
        if idx == -1:
            return None
        # Only accept line-start matches; skip backtick-enclosed occurrences
        if idx == 0 or raw[idx - 1] == '\n':
            break

    return raw[idx:].rstrip() + "\n"


def _dispatch_codex(
    issue: int,
    area: str,
    pr: int,
    monorepo_root: Path,
    model: str = "",
    last_review_id: int = 0,
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
    review_json_path = log.with_suffix(".json")

    base_ref = get_pr_base_ref(area, pr)

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

    # Auth preflight: session-auth takes priority over API key.
    # codex login status is the authoritative check - it returns exit 0 when
    # any valid auth mode (ChatGPT session or API key) is active.
    base_env = {k: v for k, v in os.environ.items() if k not in _CLAUDE_ENV_STRIP}
    auth_mode, auth_json_src = _detect_codex_auth(base_env)

    if auth_mode == "missing":
        reason = "no valid Codex auth: codex login status returned non-zero and CODEX_API_KEY is not set"
        print(
            f"[review_runner] {reason} for issue #{issue} area={area}",
            file=sys.stderr,
        )
        _write_job_meta(
            meta,
            status="failed_auth",
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
            exit_code=None,
        )
        try:
            state_update(issue, area, monorepo_root, {
                "reviewJob": {"status": "failed_auth", "finishedAt": _now_iso()}
            })
        except Exception:
            pass
        return 1

    print(
        f"[review_runner] codex auth mode={auth_mode} for issue #{issue} area={area}",
        file=sys.stderr,
    )

    # Build isolated environment using a dedicated CODEX_HOME to avoid
    # user-profile skill discovery. For session-auth with file-backed auth.json,
    # seed the temp dir so the session remains accessible.
    with tempfile.TemporaryDirectory(prefix="codex-home-") as tmp_codex_home:
        clean_env = dict(base_env)
        clean_env["CODEX_HOME"] = tmp_codex_home

        if auth_mode == "session" and auth_json_src is not None:
            # Seed auth.json so session-auth survives the isolated CODEX_HOME.
            shutil.copy2(str(auth_json_src), str(Path(tmp_codex_home) / "auth.json"))

        # Write automation config.toml to force-disable repo-scoped skills that
        # could be auto-invoked by generic prompts. This is the authoritative
        # disable at the CODEX_HOME level - more reliable than openai.yaml inside
        # the repo because it cannot be modified by the PR under review.
        skill_md = str(monorepo_root / ".agents/skills/dev-review/SKILL.md")
        config_toml = (
            "[[skills.config]]\n"
            f'path = "{skill_md}"\n'
            "enabled = false\n"
        )
        Path(tmp_codex_home, "config.toml").write_text(config_toml)

        cmd = [
            "codex", "exec", "review",
            "--base", f"origin/{base_ref}",
            "--output-last-message", str(review_json_path),
            "--dangerously-bypass-approvals-and-sandbox",
        ]
        if model:
            cmd += ["--model", model]

        print(
            f"[review_runner:subprocess] start tool=codex stage=review "
            f"issue=#{issue} area={area} pr=#{pr} cwd={worktree_dir}",
            file=sys.stderr,
        )
        result = run(
            cmd, cwd=str(worktree_dir), env=clean_env,
            timeout=900, capture_output=True, replace_env=True,
        )
        print(
            f"[review_runner:subprocess] end tool=codex stage=review "
            f"issue=#{issue} rc={result.rc}",
            file=sys.stderr,
        )

    # Save transcript artifacts (stderr = progress log, stdout per codex convention)
    log.write_text(result.stderr)
    err.write_text(result.stdout)

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

    if result.rc != 0:
        return result.rc

    # --- Structured output path ---
    # All failures below are fail-closed: no GitHub post, local artifact only.
    def _fail_parse(reason: str, raw_content: str = "") -> int:
        print(
            f"[review_runner] codex structured output failed for "
            f"issue #{issue} area={area} pr=#{pr}: {reason} - "
            f"setting failed_parse, transcript artifact saved at {log}",
            file=sys.stderr,
        )
        if raw_content:
            snippet = raw_content[:500]
            if len(raw_content) > 500:
                snippet += f"... ({len(raw_content)} chars total)"
            print(
                f"[review_runner] raw output snippet:\n{snippet}",
                file=sys.stderr,
            )
        # Update both headless meta and pipeline state so they stay consistent.
        # Without this, meta would read "success" while state reads "failed_parse".
        try:
            _write_job_meta(
                meta,
                status="failed_parse",
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
        except Exception:
            pass
        try:
            state_update(issue, area, monorepo_root, {
                "reviewJob": {"status": "failed_parse", "finishedAt": _now_iso()}
            })
        except Exception:
            pass
        return 1

    if not review_json_path.exists():
        # Log codex stdout/stderr for debugging (stderr=progress, stdout=output)
        return _fail_parse(
            "output JSON file not created",
            raw_content=result.stdout[:1000] if result.stdout else "(empty stdout)",
        )

    # Basic JSON parse check before handing off to publisher
    raw_json_text = review_json_path.read_text()
    try:
        json.loads(raw_json_text)
    except json.JSONDecodeError as exc:
        review_json_path.unlink(missing_ok=True)
        return _fail_parse(f"output JSON parse error: {exc}", raw_content=raw_json_text)

    # Move codex output to canonical artifact path
    review_dir = monorepo_root / ".workspace" / "dev-review" / f"pr-{pr}"
    review_dir.mkdir(parents=True, exist_ok=True)
    canonical_json = review_dir / "review.json"
    shutil.move(str(review_json_path), str(canonical_json))

    # Delegate validation, contamination check, rendering, and posting
    # to the shared review publisher CLI.
    publisher = (
        monorepo_root / ".agents" / "skills" / "dev-review"
        / "scripts" / "review_publish.py"
    )
    pub_cmd = [
        sys.executable, str(publisher),
        "--input", str(canonical_json),
        "--mode", "publish",
        "--repo", repo,
        "--pr", str(pr),
        "--output-dir", str(review_dir),
    ]
    print(
        f"[review_runner] invoking publisher for issue #{issue} "
        f"area={area} pr=#{pr}",
        file=sys.stderr,
    )
    pub_result = subprocess.run(pub_cmd, capture_output=True, text=True)
    if pub_result.stderr:
        print(pub_result.stderr, end="", file=sys.stderr)

    if pub_result.returncode != 0:
        reason = f"publisher failed (rc={pub_result.returncode})"
        print(
            f"[review_runner] codex publish failed for "
            f"issue #{issue} area={area} pr=#{pr}: {reason} - "
            f"setting failed_publish",
            file=sys.stderr,
        )
        try:
            _write_job_meta(
                meta,
                status="failed_publish",
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
        except Exception:
            pass
        try:
            state_update(issue, area, monorepo_root, {
                "reviewJob": {"status": "failed_publish", "finishedAt": _now_iso()}
            })
        except Exception:
            pass
        return 1

    # Post-condition: verify the review was actually posted to GitHub.
    # Publisher returning rc=0 does not guarantee the API call succeeded
    # and the review is now visible on GitHub.
    from .github_client import check_review_exists

    def _fail_postcondition_codex(reason: str) -> int:
        print(
            f"[review_runner] codex post-condition failed for "
            f"issue #{issue} area={area} pr=#{pr}: {reason}",
            file=sys.stderr,
        )
        try:
            _write_job_meta(
                meta,
                status="failed_postcondition",
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
        except Exception:
            pass
        try:
            state_update(issue, area, monorepo_root, {
                "reviewJob": {"status": "failed_postcondition", "finishedAt": _now_iso()}
            })
        except Exception:
            pass
        return 1

    try:
        review_id = check_review_exists(area, pr, last_review_id)
        if review_id is None:
            return _fail_postcondition_codex(
                f"no actionable review newer than id={last_review_id} found on GitHub after publisher success"
            )
    except Exception as exc:
        return _fail_postcondition_codex(f"check_review_exists raised: {exc}")

    try:
        state_update(issue, area, monorepo_root, {
            "reviewJob": {"status": "success", "finishedAt": _now_iso()}
        })
    except Exception:
        pass
    return 0
