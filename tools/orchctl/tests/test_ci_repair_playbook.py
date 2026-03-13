"""Tests for the CI failure repair + blocker issue playbook (#98).

Covers:
- deterministic_test_failure routes to REPAIR (not ESCALATE)
- Repair attempt is auto-started on first failure
- CI logs are collected and posted as a comment
- Blocker issue is created after budget exhaustion (2+ failures)
- Blocker issue body includes failure history and original issue reference
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from orchctl.db.connection import init_db
from orchctl.db.config import set_config
from orchctl.failure_classifier import next_action_for_class
from orchctl.models import FailureClass, NextAction
from orchctl.commands.reconcile import (
    _run_ci_repair_playbook,
    _create_ci_blocker_issue,
    _next_action_to_state,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    db_path = tmp_path / "test.db"
    c, _ = init_db(db_path)
    # Set deterministic_test_failure budget to 2.
    set_config(
        c,
        "retry_budget_by_class",
        json.dumps({"deterministic_test_failure": 2, "default": 1}),
    )
    c.execute(
        "INSERT INTO issues (area, number, state) VALUES ('workspace', 42, 'dispatched')"
    )
    c.commit()
    yield c
    c.close()


def _issue_id(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT id FROM issues WHERE number = 42").fetchone()
    return row["id"]


def _insert_attempt(
    conn: sqlite3.Connection,
    attempt_id: str,
    issue_id: int,
    status: str = "failed",
    terminal_json: str | None = None,
) -> None:
    conn.execute(
        "INSERT INTO attempts (attempt_id, issue_id, status, terminal_json)"
        " VALUES (?, ?, ?, ?)",
        (attempt_id, issue_id, status, terminal_json),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Unit: next_action for deterministic_test_failure
# ---------------------------------------------------------------------------


def test_deterministic_test_failure_routes_to_repair() -> None:
    assert next_action_for_class(FailureClass.DETERMINISTIC_TEST_FAILURE) == NextAction.REPAIR


# ---------------------------------------------------------------------------
# Unit: _next_action_to_state — repair attempt scheduled (within budget)
# ---------------------------------------------------------------------------


def test_repair_attempt_scheduled_within_budget(conn: sqlite3.Connection) -> None:
    iid = _issue_id(conn)
    with (
        patch("orchctl.commands.reconcile.post_issue_comment") as mock_comment,
        patch("orchctl.commands.reconcile._run_ci_repair_playbook"),
    ):
        state = _next_action_to_state(
            conn,
            area="workspace",
            issue_id=iid,
            number=42,
            retry_count=0,
            failure_class=FailureClass.DETERMINISTIC_TEST_FAILURE,
            next_action=NextAction.REPAIR,
            dry_run=False,
        )
    assert state == "pending"
    row = conn.execute("SELECT retry_count FROM issues WHERE id = ?", (iid,)).fetchone()
    assert row["retry_count"] == 1
    # Retry comment posted
    mock_comment.assert_called_once()
    body = mock_comment.call_args[0][2]
    assert "deterministic_test_failure" in body


# ---------------------------------------------------------------------------
# Unit: _next_action_to_state — budget exhausted → blocker issue + needs-human
# ---------------------------------------------------------------------------


def test_blocker_issue_created_on_budget_exhaustion(conn: sqlite3.Connection) -> None:
    iid = _issue_id(conn)
    # Simulate two previous attempts.
    _insert_attempt(conn, "a-001", iid, "failed", '{"prNumber": 10, "reason": "jest failed"}')
    _insert_attempt(conn, "a-002", iid, "failed", '{"prNumber": 11, "reason": "jest failed again"}')

    with (
        patch("orchctl.commands.reconcile.post_issue_comment") as mock_comment,
        patch("orchctl.commands.reconcile.create_issue", return_value=99) as mock_create,
    ):
        state = _next_action_to_state(
            conn,
            area="workspace",
            issue_id=iid,
            number=42,
            retry_count=2,  # budget=2, exhausted
            failure_class=FailureClass.DETERMINISTIC_TEST_FAILURE,
            next_action=NextAction.REPAIR,
            dry_run=False,
            terminal_json='{"prNumber": 11, "reason": "jest failed again"}',
        )

    assert state == "needs-human"
    # Blocker issue created
    mock_create.assert_called_once()
    create_kwargs = mock_create.call_args
    title = create_kwargs[1]["title"] if create_kwargs[1] else create_kwargs[0][1]
    assert "blocker" in title.lower()
    assert "42" in title
    body = create_kwargs[1]["body"] if create_kwargs[1] else create_kwargs[0][2]
    assert "#42" in body
    assert "deterministic_test_failure" in body
    assert "a-001" in body or "jest failed" in body

    # Blocker reference comment posted on original issue
    comment_calls = mock_comment.call_args_list
    blocker_comments = [c for c in comment_calls if "#99" in str(c)]
    assert blocker_comments, "Expected a comment referencing the blocker issue #99"


def test_blocker_issue_not_created_within_budget(conn: sqlite3.Connection) -> None:
    iid = _issue_id(conn)
    with (
        patch("orchctl.commands.reconcile.post_issue_comment"),
        patch("orchctl.commands.reconcile._run_ci_repair_playbook"),
        patch("orchctl.commands.reconcile.create_issue") as mock_create,
    ):
        state = _next_action_to_state(
            conn,
            area="workspace",
            issue_id=iid,
            number=42,
            retry_count=1,  # budget=2, still within
            failure_class=FailureClass.DETERMINISTIC_TEST_FAILURE,
            next_action=NextAction.REPAIR,
            dry_run=False,
        )

    assert state == "pending"
    mock_create.assert_not_called()


def test_repair_playbook_not_called_on_budget_exhaustion(conn: sqlite3.Connection) -> None:
    """_run_ci_repair_playbook must NOT be called when budget is already exhausted."""
    iid = _issue_id(conn)
    with (
        patch("orchctl.commands.reconcile.post_issue_comment"),
        patch("orchctl.commands.reconcile.create_issue", return_value=99),
        patch("orchctl.commands.reconcile._run_ci_repair_playbook") as mock_playbook,
    ):
        state = _next_action_to_state(
            conn,
            area="workspace",
            issue_id=iid,
            number=42,
            retry_count=2,  # budget=2, exhausted
            failure_class=FailureClass.DETERMINISTIC_TEST_FAILURE,
            next_action=NextAction.REPAIR,
            dry_run=False,
        )

    assert state == "needs-human"
    mock_playbook.assert_not_called()


# ---------------------------------------------------------------------------
# Unit: _run_ci_repair_playbook — posts repair context comment with CI logs
# ---------------------------------------------------------------------------


def test_repair_playbook_posts_comment_with_logs(conn: sqlite3.Connection) -> None:
    terminal_json = json.dumps({"prNumber": 7, "reason": "test failed"})
    with (
        patch("orchctl.commands.reconcile.get_pr_branch", return_value="feat/issue-42-foo"),
        patch("orchctl.commands.reconcile.fetch_ci_logs", return_value="FAIL: test_bar\n  AssertionError"),
        patch("orchctl.commands.reconcile.post_issue_comment") as mock_comment,
    ):
        _run_ci_repair_playbook(conn, "workspace", 42, terminal_json)

    mock_comment.assert_called_once()
    body = mock_comment.call_args[0][2]
    assert "PR #7" in body
    assert "AssertionError" in body


def test_repair_playbook_posts_comment_without_logs_when_unavailable(conn: sqlite3.Connection) -> None:
    terminal_json = json.dumps({"prNumber": 7, "reason": "test failed"})
    with (
        patch("orchctl.commands.reconcile.get_pr_branch", return_value="feat/issue-42-foo"),
        patch("orchctl.commands.reconcile.fetch_ci_logs", return_value=None),
        patch("orchctl.commands.reconcile.post_issue_comment") as mock_comment,
    ):
        _run_ci_repair_playbook(conn, "workspace", 42, terminal_json)

    mock_comment.assert_called_once()
    body = mock_comment.call_args[0][2]
    assert "unavailable" in body


def test_repair_playbook_skips_log_when_no_pr_number(conn: sqlite3.Connection) -> None:
    with (
        patch("orchctl.commands.reconcile.get_pr_branch") as mock_branch,
        patch("orchctl.commands.reconcile.post_issue_comment") as mock_comment,
    ):
        _run_ci_repair_playbook(conn, "workspace", 42, None)

    mock_branch.assert_not_called()
    mock_comment.assert_called_once()
    body = mock_comment.call_args[0][2]
    assert "unavailable" in body


# ---------------------------------------------------------------------------
# Unit: _create_ci_blocker_issue — failure history in body
# ---------------------------------------------------------------------------


def test_blocker_issue_body_contains_failure_history(conn: sqlite3.Connection) -> None:
    iid = _issue_id(conn)
    _insert_attempt(conn, "a-001", iid, "failed", '{"prNumber": 5, "reason": "AssertionError in test_foo"}')
    _insert_attempt(conn, "a-002", iid, "failed", '{"prNumber": 6, "reason": "AssertionError again"}')

    with (
        patch("orchctl.commands.reconcile.create_issue", return_value=200) as mock_create,
        patch("orchctl.commands.reconcile.post_issue_comment"),
    ):
        _create_ci_blocker_issue(conn, "workspace", iid, 42, 2, None)

    mock_create.assert_called_once()
    body = mock_create.call_args[1]["body"]
    assert "AssertionError in test_foo" in body
    assert "AssertionError again" in body
    assert "#42" in body
    assert "workspace" in body


def test_blocker_issue_dry_run_skips_creation(conn: sqlite3.Connection) -> None:
    iid = _issue_id(conn)
    with (
        patch("orchctl.commands.reconcile.create_issue") as mock_create,
        patch("orchctl.commands.reconcile.post_issue_comment"),
    ):
        state = _next_action_to_state(
            conn,
            area="workspace",
            issue_id=iid,
            number=42,
            retry_count=2,
            failure_class=FailureClass.DETERMINISTIC_TEST_FAILURE,
            next_action=NextAction.REPAIR,
            dry_run=True,
        )
    assert state == "needs-human"
    mock_create.assert_not_called()
