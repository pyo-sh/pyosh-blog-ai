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


def _init_state(tmp_path, issue=1, area="client", pr=10, last_review_id=0):
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
        "lastReviewId": last_review_id,
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


class TestPostConditionWatermark:
    """REGRESSION: post-condition must require a review newer than last_review_id.

    Before the fix, check_review_exists was called without last_review_id, defaulting
    to 0.  On any second-or-later review round an older existing review could satisfy
    the check even when the current publish step silently failed.
    """

    def test_claude_old_review_id_does_not_satisfy_postcondition(self, tmp_path):
        """A review whose id <= last_review_id must not count as a new review."""
        # last_review_id=500 means any review with id <=500 is old
        issue, area, pr = _init_state(tmp_path, last_review_id=500)

        check_calls = []

        def fake_check(area, pr, last_review_id=0):
            check_calls.append(last_review_id)
            # The stale review has id=500 which is NOT > last_review_id=500
            return None  # check_review_exists returns None when no qualifying review found

        def fake_run(cmd, *, cwd=None, env=None, timeout=None, capture_output=False, replace_env=False):
            return _make_run_result(rc=0, stdout="")

        with (
            patch("dev_pipeline.review_runner.run", side_effect=fake_run),
            patch("dev_pipeline.github_client.check_review_exists", side_effect=fake_check),
        ):
            from dev_pipeline import review_runner
            rc = review_runner._dispatch_claude(
                issue=issue, area=area, pr=pr, monorepo_root=tmp_path,
                last_review_id=500,
            )

        assert rc == 1
        assert check_calls == [500], (
            "REGRESSION: post-condition must pass last_review_id=500 to check_review_exists"
        )
        state = state_read(issue, area, tmp_path)
        assert state.review_job.status == ReviewJobStatus.FAILED_POSTCONDITION

    def test_claude_new_review_id_satisfies_postcondition(self, tmp_path):
        """A review with id > last_review_id counts as a new review."""
        issue, area, pr = _init_state(tmp_path, last_review_id=500)

        def fake_check(area, pr, last_review_id=0):
            # New review has id=501 which is > 500
            return 501

        def fake_run(cmd, *, cwd=None, env=None, timeout=None, capture_output=False, replace_env=False):
            return _make_run_result(rc=0, stdout="")

        with (
            patch("dev_pipeline.review_runner.run", side_effect=fake_run),
            patch("dev_pipeline.github_client.check_review_exists", side_effect=fake_check),
        ):
            from dev_pipeline import review_runner
            rc = review_runner._dispatch_claude(
                issue=issue, area=area, pr=pr, monorepo_root=tmp_path,
                last_review_id=500,
            )

        assert rc == 0
        state = state_read(issue, area, tmp_path)
        assert state.review_job.status == ReviewJobStatus.SUCCESS

    def test_dispatch_review_reads_last_review_id_from_state(self, tmp_path):
        """REGRESSION: dispatch_review must read last_review_id from state before dispatch.

        If dispatch_review always passes 0, the watermark from a previous round is
        ignored and the false-success window remains open.
        """
        issue, area, pr = _init_state(tmp_path, last_review_id=777)

        captured_last_review_ids = []

        def fake_dispatch_claude(issue, area, pr, monorepo_root, model, last_review_id=0):
            captured_last_review_ids.append(last_review_id)
            return 0

        with patch("dev_pipeline.review_runner._dispatch_claude", side_effect=fake_dispatch_claude):
            from dev_pipeline.review_runner import dispatch_review
            dispatch_review(issue, area, pr, tmp_path, tool="claude")

        assert captured_last_review_ids == [777], (
            "REGRESSION: dispatch_review must pass last_review_id=777 from state to "
            "_dispatch_claude, not 0"
        )
