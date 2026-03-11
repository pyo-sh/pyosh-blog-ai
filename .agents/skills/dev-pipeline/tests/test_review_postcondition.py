"""Tests for post-condition enforcement in review dispatch.

Regression for: false-success where subprocess rc=0 was recorded as
status=success even when no GitHub review was actually posted.
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from dev_pipeline.command_runner import RunResult
from dev_pipeline.models import PipelineState, ReviewJobStatus
from dev_pipeline.state_store import state_write, state_read


def _make_run_result(rc=0, stdout="", stderr="", timed_out=False):
    return RunResult(command=[], rc=rc, stdout=stdout, stderr=stderr, timed_out=timed_out)


def _init_state(tmp_path, issue=1, area="client", pr=10):
    for sub in [
        f".workspace/pipeline/{area}",
        f".workspace/pipeline/logs/{area}",
        ".workspace/messages",
        f".workspace/worktrees/{area}/issue-{issue}",
    ]:
        (tmp_path / sub).mkdir(parents=True, exist_ok=True)

    state_dict = {
        "version": 2,
        "issue": issue,
        "area": area,
        "pr": pr,
        "branch": f"feat/issue-{issue}",
        "paths": {
            "skillCwd": str(tmp_path),
            "repoDir": str(tmp_path / area),
            "worktreeDir": str(tmp_path / f".workspace/worktrees/{area}/issue-{issue}"),
        },
        "step": "review_dispatch",
        "lastReviewId": 0,
        "lastCommitSha": "abc123",
        "skipReview": False,
        "reviewResolveRound": 0,
        "maxReviewResolveRounds": 5,
        "stageRetries": {s: 0 for s in ["build", "review_dispatch", "review_wait", "review_process", "resolve", "merge", "log"]},
        "maxStageRetries": 3,
        "reviewJob": {"runId": "test-run", "status": "running", "startedAt": None, "finishedAt": None, "tool": "", "model": ""},
        "transitionLog": [],
        "recoveryLog": [],
        "updatedAt": None,
    }
    state = PipelineState.from_dict(state_dict)
    state_write(issue, area, tmp_path, state)
    return issue, area, pr


class TestClaudePostCondition:
    def test_claude_rc0_but_no_review_on_github_sets_failed_postcondition(self, tmp_path):
        """REGRESSION: claude rc=0 with no review posted must not set status=success.

        Before the fix, subprocess rc=0 was unconditionally treated as success.
        The fix adds a check_review_exists post-condition after rc=0.
        """
        issue, area, pr = _init_state(tmp_path)

        def fake_run(cmd, *, cwd=None, env=None, timeout=None, capture_output=False, replace_env=False):
            return _make_run_result(rc=0, stdout="claude ran but did not post")

        with (
            patch("dev_pipeline.review_runner.run", side_effect=fake_run),
            patch("dev_pipeline.github_client.check_review_exists", return_value=None),
        ):
            from dev_pipeline import review_runner
            rc = review_runner._dispatch_claude(issue=issue, area=area, pr=pr, monorepo_root=tmp_path)

        assert rc == 1
        state = state_read(issue, area, tmp_path)
        assert state.review_job.status == ReviewJobStatus.FAILED_POSTCONDITION, (
            "REGRESSION: claude returned rc=0 but no review was posted; "
            "status must be failed_postcondition, not success"
        )

    def test_claude_rc0_with_review_on_github_sets_success(self, tmp_path):
        """When claude rc=0 AND check_review_exists returns a review_id, status is success."""
        issue, area, pr = _init_state(tmp_path)

        def fake_run(cmd, *, cwd=None, env=None, timeout=None, capture_output=False, replace_env=False):
            return _make_run_result(rc=0, stdout="review posted")

        with (
            patch("dev_pipeline.review_runner.run", side_effect=fake_run),
            patch("dev_pipeline.github_client.check_review_exists", return_value=99001),
        ):
            from dev_pipeline import review_runner
            rc = review_runner._dispatch_claude(issue=issue, area=area, pr=pr, monorepo_root=tmp_path)

        assert rc == 0
        state = state_read(issue, area, tmp_path)
        assert state.review_job.status == ReviewJobStatus.SUCCESS

    def test_claude_rc0_check_review_raises_sets_failed_postcondition(self, tmp_path):
        """If check_review_exists raises, status must be failed_postcondition, not success."""
        issue, area, pr = _init_state(tmp_path)

        def fake_run(cmd, *, cwd=None, env=None, timeout=None, capture_output=False, replace_env=False):
            return _make_run_result(rc=0, stdout="")

        with (
            patch("dev_pipeline.review_runner.run", side_effect=fake_run),
            patch("dev_pipeline.github_client.check_review_exists", side_effect=RuntimeError("gh api error")),
        ):
            from dev_pipeline import review_runner
            rc = review_runner._dispatch_claude(issue=issue, area=area, pr=pr, monorepo_root=tmp_path)

        assert rc == 1
        state = state_read(issue, area, tmp_path)
        assert state.review_job.status == ReviewJobStatus.FAILED_POSTCONDITION

    def test_claude_nonzero_rc_skips_postcondition(self, tmp_path):
        """When claude subprocess fails (rc!=0), post-condition is not checked."""
        issue, area, pr = _init_state(tmp_path)

        def fake_run(cmd, *, cwd=None, env=None, timeout=None, capture_output=False, replace_env=False):
            return _make_run_result(rc=1)

        check_called = []

        def fake_check(*args, **kwargs):
            check_called.append(True)
            return None

        with (
            patch("dev_pipeline.review_runner.run", side_effect=fake_run),
            patch("dev_pipeline.github_client.check_review_exists", side_effect=fake_check),
        ):
            from dev_pipeline import review_runner
            rc = review_runner._dispatch_claude(issue=issue, area=area, pr=pr, monorepo_root=tmp_path)

        assert rc == 1
        assert not check_called, "check_review_exists must not be called when subprocess fails"


class TestCodexPostCondition:
    def test_publisher_failure_sets_failed_publish_not_success(self, tmp_path):
        """When review_publish.py fails, status must be failed_publish, not success."""
        issue, area, pr = _init_state(tmp_path)
        review_json = '{"verdict":"comment","summary":"ok","issues":[]}'

        def fake_run(cmd, *, cwd=None, env=None, timeout=None, capture_output=False, replace_env=False):
            if "-o" in cmd:
                out_path = cmd[cmd.index("-o") + 1]
                Path(out_path).write_text(review_json)
            return _make_run_result(rc=0, stderr="codex ok")

        def fake_subprocess_run(cmd, **kwargs):
            # codex login status → session valid; publisher call → fails
            if "login" in cmd:
                return MagicMock(returncode=0, stdout="", stderr="")
            return MagicMock(returncode=1, stderr="publish error", stdout="")

        with (
            patch("subprocess.run", side_effect=fake_subprocess_run),
            patch("dev_pipeline.review_runner.run", side_effect=fake_run),
            patch("dev_pipeline.github_client.get_pr_base_ref", return_value="main"),
        ):
            from dev_pipeline import review_runner
            rc = review_runner._dispatch_codex(issue=issue, area=area, pr=pr, monorepo_root=tmp_path)

        assert rc == 1
        state = state_read(issue, area, tmp_path)
        assert state.review_job.status == ReviewJobStatus.FAILED_PUBLISH

    def test_codex_review_missing_after_publish_sets_failed_postcondition(self, tmp_path):
        """Publisher rc=0 but GitHub review absent must set failed_postcondition."""
        issue, area, pr = _init_state(tmp_path)
        review_json = '{"verdict":"comment","summary":"ok","issues":[]}'

        def fake_run(cmd, *, cwd=None, env=None, timeout=None, capture_output=False, replace_env=False):
            if "-o" in cmd:
                out_path = cmd[cmd.index("-o") + 1]
                Path(out_path).write_text(review_json)
            return _make_run_result(rc=0, stderr="codex ok")

        def fake_subprocess_run(cmd, **kwargs):
            # All subprocess.run calls succeed (auth + publisher)
            return MagicMock(returncode=0, stdout="", stderr="")

        with (
            patch("subprocess.run", side_effect=fake_subprocess_run),
            patch("dev_pipeline.review_runner.run", side_effect=fake_run),
            patch("dev_pipeline.github_client.get_pr_base_ref", return_value="main"),
            patch("dev_pipeline.github_client.check_review_exists", return_value=None),
        ):
            from dev_pipeline import review_runner
            rc = review_runner._dispatch_codex(issue=issue, area=area, pr=pr, monorepo_root=tmp_path)

        assert rc == 1
        state = state_read(issue, area, tmp_path)
        assert state.review_job.status == ReviewJobStatus.FAILED_POSTCONDITION, (
            "REGRESSION: publisher succeeded but no GitHub review was found; "
            "status must be failed_postcondition, not success"
        )

    def test_codex_review_present_after_publish_sets_success(self, tmp_path):
        """Publisher rc=0 AND GitHub review found must set status=success."""
        issue, area, pr = _init_state(tmp_path)
        review_json = '{"verdict":"comment","summary":"ok","issues":[]}'

        def fake_run(cmd, *, cwd=None, env=None, timeout=None, capture_output=False, replace_env=False):
            if "-o" in cmd:
                out_path = cmd[cmd.index("-o") + 1]
                Path(out_path).write_text(review_json)
            return _make_run_result(rc=0, stderr="codex ok")

        def fake_subprocess_run(cmd, **kwargs):
            return MagicMock(returncode=0, stdout="", stderr="")

        with (
            patch("subprocess.run", side_effect=fake_subprocess_run),
            patch("dev_pipeline.review_runner.run", side_effect=fake_run),
            patch("dev_pipeline.github_client.get_pr_base_ref", return_value="main"),
            patch("dev_pipeline.github_client.check_review_exists", return_value=88001),
        ):
            from dev_pipeline import review_runner
            rc = review_runner._dispatch_codex(issue=issue, area=area, pr=pr, monorepo_root=tmp_path)

        assert rc == 0
        state = state_read(issue, area, tmp_path)
        assert state.review_job.status == ReviewJobStatus.SUCCESS
