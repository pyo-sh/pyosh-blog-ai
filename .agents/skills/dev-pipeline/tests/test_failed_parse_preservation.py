"""Regression test: failed_parse status must not be overwritten by dispatch_review().

Before the fix, _dispatch_codex() wrote reviewJob.status=failed_parse, then
dispatch_review() unconditionally overwrote it with "failed" (rc != 0 → "failed").
The FAILED_PARSE value never survived as an observable state.
"""
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from dev_pipeline.models import PipelineState, ReviewJobStatus
from dev_pipeline.state_store import state_write, state_read


@pytest.fixture
def initialized_state(monorepo_root, sample_state):
    """Write a running review job state and return (issue, area, monorepo_root)."""
    sample_state["reviewJob"]["status"] = "running"
    sample_state["reviewJob"]["runId"] = "test-run-001"
    state = PipelineState.from_dict(sample_state)
    state_write(sample_state["issue"], sample_state["area"], monorepo_root, state)
    return sample_state["issue"], sample_state["area"], monorepo_root


def _make_fake_result(rc: int, stdout: str = "", stderr: str = "", timed_out: bool = False):
    result = MagicMock()
    result.rc = rc
    result.stdout = stdout
    result.stderr = stderr
    result.timed_out = timed_out
    return result


class TestFailedParsePreservation:
    def test_failed_parse_survives_dispatch_review(self, initialized_state, monorepo_root, sample_state):
        """dispatch_review() must not overwrite failed_parse with 'failed'.

        REGRESSION: before the fix, dispatch_review() always wrote
        status="failed" when rc != 0, erasing the failed_parse value set by
        _dispatch_codex() and making parse failures indistinguishable from
        general errors.
        """
        issue, area, monorepo_root = initialized_state
        pr = sample_state["pr"]

        # Simulate _dispatch_codex: parse failure sets failed_parse + returns rc=1
        def fake_dispatch_codex(*args, **kwargs):
            from dev_pipeline.state_store import state_update
            from datetime import datetime, timezone
            state_update(issue, area, monorepo_root, {
                "reviewJob": {
                    "status": "failed_parse",
                    "finishedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                }
            })
            return 1

        with (
            patch("dev_pipeline.review_runner._dispatch_codex", side_effect=fake_dispatch_codex),
            patch("dev_pipeline.review_runner.state_read", wraps=state_read),
        ):
            from dev_pipeline.review_runner import dispatch_review
            rc = dispatch_review(issue, area, pr, monorepo_root, tool="codex")

        assert rc == 1
        final_state = state_read(issue, area, monorepo_root)
        assert final_state.review_job.status == ReviewJobStatus.FAILED_PARSE, (
            "REGRESSION: dispatch_review() overwrote failed_parse with 'failed'. "
            "Parse failures must stay as failed_parse for routing to separate recovery."
        )

    def test_normal_failure_stays_failed(self, initialized_state, monorepo_root, sample_state):
        """When inner dispatch returns rc=1 without setting failed_parse, status must be 'failed'."""
        issue, area, monorepo_root = initialized_state
        pr = sample_state["pr"]

        def fake_dispatch_codex(*args, **kwargs):
            return 1  # error, no state written

        with patch("dev_pipeline.review_runner._dispatch_codex", side_effect=fake_dispatch_codex):
            from dev_pipeline.review_runner import dispatch_review
            rc = dispatch_review(issue, area, pr, monorepo_root, tool="codex")

        assert rc == 1
        final_state = state_read(issue, area, monorepo_root)
        assert final_state.review_job.status == ReviewJobStatus.FAILED

    def test_success_sets_success(self, initialized_state, monorepo_root, sample_state):
        """rc=0 inner dispatch must result in status='success'."""
        issue, area, monorepo_root = initialized_state
        pr = sample_state["pr"]

        def fake_dispatch_claude(*args, **kwargs):
            return 0

        with patch("dev_pipeline.review_runner._dispatch_claude", side_effect=fake_dispatch_claude):
            from dev_pipeline.review_runner import dispatch_review
            rc = dispatch_review(issue, area, pr, monorepo_root, tool="claude")

        assert rc == 0
        final_state = state_read(issue, area, monorepo_root)
        assert final_state.review_job.status == ReviewJobStatus.SUCCESS
