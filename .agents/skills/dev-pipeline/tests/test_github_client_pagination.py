"""Regression tests for github_client.fetch_review_comments pagination handling."""
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


def test_fetch_review_comments_single_page():
    """Single JSON array is parsed correctly."""
    comments = [
        {"path": "src/foo.py", "original_line": 10, "line": 10, "side": "RIGHT", "body": "fix this"},
        {"path": "src/bar.py", "original_line": None, "line": 20, "side": "RIGHT", "body": "consider"},
    ]
    mock_output = json.dumps(comments)

    with patch("dev_pipeline.github_client.run", return_value=_make_result(stdout=mock_output)):
        from dev_pipeline.github_client import fetch_review_comments
        result = fetch_review_comments("client", 42, 999)

    assert len(result) == 2
    assert result[0]["path"] == "src/foo.py"
    assert result[0]["line"] == 10
    assert result[1]["line"] == 20


def test_fetch_review_comments_paginated_concatenated():
    """Paginated --paginate output (concatenated JSON arrays) is merged correctly."""
    page1 = [{"path": "a.py", "original_line": 1, "line": 1, "side": "RIGHT", "body": "issue 1"}]
    page2 = [{"path": "b.py", "original_line": 2, "line": 2, "side": "RIGHT", "body": "issue 2"}]
    # gh --paginate emits each page as a separate JSON array on its own line
    mock_output = json.dumps(page1) + "\n" + json.dumps(page2)

    with patch("dev_pipeline.github_client.run", return_value=_make_result(stdout=mock_output)):
        from dev_pipeline.github_client import fetch_review_comments
        result = fetch_review_comments("client", 42, 999)

    assert len(result) == 2
    paths = {r["path"] for r in result}
    assert paths == {"a.py", "b.py"}


def test_fetch_review_comments_empty_response():
    """Empty stdout returns empty list (non-fatal)."""
    with patch("dev_pipeline.github_client.run", return_value=_make_result(stdout="")):
        from dev_pipeline.github_client import fetch_review_comments
        result = fetch_review_comments("client", 42, 999)
    assert result == []


def test_fetch_review_comments_gh_error_returns_empty():
    """gh CLI failure returns [] instead of raising (non-fatal contract)."""
    with patch("dev_pipeline.github_client.run", return_value=_make_result(rc=1, stderr="API rate limit")):
        from dev_pipeline.github_client import fetch_review_comments
        result = fetch_review_comments("client", 42, 999)
    assert result == []


def test_fetch_review_comments_malformed_json_returns_empty():
    """Malformed JSON in stdout returns [] gracefully."""
    with patch("dev_pipeline.github_client.run", return_value=_make_result(stdout="not json at all")):
        from dev_pipeline.github_client import fetch_review_comments
        result = fetch_review_comments("client", 42, 999)
    assert result == []


def test_fetch_review_comments_many_pages():
    """Three pages of paginated output are all collected."""
    pages = [
        [{"path": f"file{i}.py", "original_line": i, "line": i, "side": "RIGHT", "body": f"comment {i}"}]
        for i in range(1, 4)
    ]
    mock_output = "\n".join(json.dumps(p) for p in pages)

    with patch("dev_pipeline.github_client.run", return_value=_make_result(stdout=mock_output)):
        from dev_pipeline.github_client import fetch_review_comments
        result = fetch_review_comments("client", 42, 999)

    assert len(result) == 3
