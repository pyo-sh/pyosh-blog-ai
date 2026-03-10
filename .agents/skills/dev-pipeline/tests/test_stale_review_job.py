"""Tests for stale review job detection and recovery."""
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from dev_pipeline.models import ReviewJob, ReviewJobStatus
from dev_pipeline.command_runner import RunResult


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ago_iso(seconds):
    dt = datetime.now(timezone.utc) - timedelta(seconds=seconds)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


class TestReviewJobIsStale:
    def test_idle_job_is_not_stale(self):
        job = ReviewJob(status=ReviewJobStatus.IDLE)
        assert job.is_stale() is False

    def test_success_job_is_not_stale(self):
        job = ReviewJob(status=ReviewJobStatus.SUCCESS)
        assert job.is_stale() is False

    def test_failed_job_is_not_stale(self):
        job = ReviewJob(status=ReviewJobStatus.FAILED)
        assert job.is_stale() is False

    def test_running_no_started_at_is_stale(self):
        job = ReviewJob(status=ReviewJobStatus.RUNNING, started_at=None)
        assert job.is_stale() is True

    def test_running_recent_is_not_stale(self):
        job = ReviewJob(status=ReviewJobStatus.RUNNING, started_at=_now_iso())
        assert job.is_stale() is False

    def test_running_old_is_stale(self):
        job = ReviewJob(status=ReviewJobStatus.RUNNING, started_at=_ago_iso(3600))
        assert job.is_stale(timeout_secs=1800) is True

    def test_running_at_boundary_is_not_stale(self):
        job = ReviewJob(status=ReviewJobStatus.RUNNING, started_at=_ago_iso(1799))
        assert job.is_stale(timeout_secs=1800) is False

    def test_running_past_boundary_is_stale(self):
        job = ReviewJob(status=ReviewJobStatus.RUNNING, started_at=_ago_iso(1801))
        assert job.is_stale(timeout_secs=1800) is True

    def test_running_invalid_started_at_is_stale(self):
        job = ReviewJob(status=ReviewJobStatus.RUNNING, started_at="not-a-date")
        assert job.is_stale() is True

    def test_custom_timeout(self):
        job = ReviewJob(status=ReviewJobStatus.RUNNING, started_at=_ago_iso(120))
        assert job.is_stale(timeout_secs=60) is True
        assert job.is_stale(timeout_secs=300) is False


class TestDispatchReviewStaleRecovery:
    """Integration test: dispatch_review should reclaim stale jobs."""

    def _make_result(self, rc=0, stdout="", stderr=""):
        return RunResult(command=[], rc=rc, stdout=stdout, stderr=stderr, timed_out=False)

    def test_active_running_job_returns_3(self, tmp_path, monkeypatch):
        """A non-stale running job returns 3 (already running)."""
        (tmp_path / ".workspace" / "pipeline" / "client").mkdir(parents=True)
        (tmp_path / ".workspace" / "pipeline" / "logs" / "client").mkdir(parents=True)
        (tmp_path / ".workspace" / "messages").mkdir(parents=True)
        (tmp_path / ".workspace" / "worktrees" / "client").mkdir(parents=True)

        # Write state with a recent running job
        from dev_pipeline.models import PipelineState
        from dev_pipeline.state_store import state_write

        state = PipelineState(issue=1, area="client", pr=10)
        state_write(1, "client", tmp_path, state)
        from dev_pipeline.state_store import state_update
        state_update(1, "client", tmp_path, {
            "reviewJob": {
                "runId": "test-run",
                "status": "running",
                "startedAt": _now_iso(),
            }
        })

        from dev_pipeline import review_runner
        rc = review_runner.dispatch_review(
            issue=1, area="client", pr=10, monorepo_root=tmp_path
        )
        assert rc == 3

    def test_stale_running_job_allows_redispatch(self, tmp_path, monkeypatch):
        """A stale running job should be reclaimed and dispatch proceeds."""
        (tmp_path / ".workspace" / "pipeline" / "client").mkdir(parents=True)
        (tmp_path / ".workspace" / "pipeline" / "logs" / "client").mkdir(parents=True)
        (tmp_path / ".workspace" / "messages").mkdir(parents=True)
        (tmp_path / ".workspace" / "worktrees" / "client").mkdir(parents=True)

        from dev_pipeline.models import PipelineState
        from dev_pipeline.state_store import state_write, state_update

        state = PipelineState(issue=1, area="client", pr=10)
        state_write(1, "client", tmp_path, state)
        state_update(1, "client", tmp_path, {
            "reviewJob": {
                "runId": "old-run",
                "status": "running",
                "startedAt": _ago_iso(7200),  # 2 hours ago
            }
        })

        def fake_run(cmd, *, cwd=None, env=None, timeout=None, capture_output=True, replace_env=False):
            return self._make_result(rc=0, stdout="review output")

        with patch("dev_pipeline.review_runner.run", side_effect=fake_run):
            from dev_pipeline import review_runner
            rc = review_runner.dispatch_review(
                issue=1, area="client", pr=10, monorepo_root=tmp_path
            )

        assert rc == 0  # dispatch succeeded

        # Verify recovery was logged
        from dev_pipeline.state_store import state_read
        final_state = state_read(1, "client", tmp_path)
        assert any(
            "stale review job" in r.get("error", "")
            for r in final_state.recovery_log
        )

    def test_idle_job_dispatches_normally(self, tmp_path, monkeypatch):
        """An idle job should dispatch without issues."""
        (tmp_path / ".workspace" / "pipeline" / "client").mkdir(parents=True)
        (tmp_path / ".workspace" / "pipeline" / "logs" / "client").mkdir(parents=True)
        (tmp_path / ".workspace" / "messages").mkdir(parents=True)
        (tmp_path / ".workspace" / "worktrees" / "client").mkdir(parents=True)

        from dev_pipeline.models import PipelineState
        from dev_pipeline.state_store import state_write

        state = PipelineState(issue=1, area="client", pr=10)
        state_write(1, "client", tmp_path, state)

        def fake_run(cmd, *, cwd=None, env=None, timeout=None, capture_output=True, replace_env=False):
            return self._make_result(rc=0, stdout="review output")

        with patch("dev_pipeline.review_runner.run", side_effect=fake_run):
            from dev_pipeline import review_runner
            rc = review_runner.dispatch_review(
                issue=1, area="client", pr=10, monorepo_root=tmp_path
            )
        assert rc == 0
