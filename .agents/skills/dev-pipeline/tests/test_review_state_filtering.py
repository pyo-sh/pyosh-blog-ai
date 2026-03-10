"""Tests for check_review_exists review state filtering."""
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from dev_pipeline.command_runner import RunResult


def _make_result(rc=0, stdout="", stderr=""):
    return RunResult(command=[], rc=rc, stdout=stdout, stderr=stderr, timed_out=False)


def _review(review_id, state, body="## Review Summary\n### Critical\nNone"):
    return {"id": review_id, "state": state, "body": body}


class TestCheckReviewExistsStateFiltering:
    def test_commented_review_accepted(self):
        reviews = [_review(100, "COMMENTED")]
        with patch("dev_pipeline.github_client.run", return_value=_make_result(stdout=json.dumps(reviews))):
            from dev_pipeline.github_client import check_review_exists
            result = check_review_exists("client", 42, last_review_id=0)
        assert result == 100

    def test_changes_requested_accepted(self):
        reviews = [_review(101, "CHANGES_REQUESTED")]
        with patch("dev_pipeline.github_client.run", return_value=_make_result(stdout=json.dumps(reviews))):
            from dev_pipeline.github_client import check_review_exists
            result = check_review_exists("client", 42, last_review_id=0)
        assert result == 101

    def test_approved_review_accepted(self):
        reviews = [_review(102, "APPROVED")]
        with patch("dev_pipeline.github_client.run", return_value=_make_result(stdout=json.dumps(reviews))):
            from dev_pipeline.github_client import check_review_exists
            result = check_review_exists("client", 42, last_review_id=0)
        assert result == 102

    def test_dismissed_review_ignored(self):
        reviews = [_review(103, "DISMISSED")]
        with patch("dev_pipeline.github_client.run", return_value=_make_result(stdout=json.dumps(reviews))):
            from dev_pipeline.github_client import check_review_exists
            result = check_review_exists("client", 42, last_review_id=0)
        assert result is None

    def test_pending_review_ignored(self):
        reviews = [_review(104, "PENDING")]
        with patch("dev_pipeline.github_client.run", return_value=_make_result(stdout=json.dumps(reviews))):
            from dev_pipeline.github_client import check_review_exists
            result = check_review_exists("client", 42, last_review_id=0)
        assert result is None

    def test_dismissed_then_commented(self):
        """Only the non-dismissed review should be returned."""
        reviews = [
            _review(100, "DISMISSED"),
            _review(101, "COMMENTED"),
        ]
        with patch("dev_pipeline.github_client.run", return_value=_make_result(stdout=json.dumps(reviews))):
            from dev_pipeline.github_client import check_review_exists
            result = check_review_exists("client", 42, last_review_id=0)
        assert result == 101

    def test_no_state_field_review_ignored(self):
        """Reviews without a state field should be skipped."""
        reviews = [{"id": 105, "body": "## Review Summary\nContent"}]
        with patch("dev_pipeline.github_client.run", return_value=_make_result(stdout=json.dumps(reviews))):
            from dev_pipeline.github_client import check_review_exists
            result = check_review_exists("client", 42, last_review_id=0)
        assert result is None
