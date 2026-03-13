"""Tests for the merge conflict auto-rebase playbook (#99).

Covers:
- git_conflict routes to REPAIR (not ESCALATE)
- Rebase attempt is scheduled on first failure
- Rebase playbook posts comment with PR ref and conflict reason
- Rebase playbook posts comment without PR info when unavailable
- Rebase playbook posts comment when conflict reason absent
- Blocker issue is created after budget exhaustion
- Blocker issue body includes conflict history and original issue reference
- Blocker issue not created within budget
- Rebase playbook not called on budget exhaustion
- Dry-run skips blocker creation
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from unittest.mock import call, patch

import pytest

from orchctl.db.connection import init_db
from orchctl.db.config import set_config
from orchctl.failure_classifier import next_action_for_class
from orchctl.models import FailureClass, NextAction
from orchctl.commands.reconcile import (
    _run_git_rebase_playbook,
    _create_git_rebase_blocker_issue,
    _next_action_to_state,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    db_path = tmp_path / "test.db"
    c, _ = init_db(db_path)
    set_config(
        c,
        "retry_budget_by_class",
        json.dumps({"git_conflict": 2, "default": 1}),
    )
    c.execute(
        "INSERT INTO issues (area, number, state) VALUES ('workspace', 55, 'dispatched')"
    )
    c.commit()
    yield c
    c.close()


def _issue_id(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT id FROM issues WHERE number = 55").fetchone()
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
# Unit: next_action for git_conflict
# ---------------------------------------------------------------------------


def test_git_conflict_routes_to_repair() -> None:
    assert next_action_for_class(FailureClass.GIT_CONFLICT) == NextAction.REPAIR


# ---------------------------------------------------------------------------
# Unit: _next_action_to_state — rebase attempt scheduled (within budget)
# ---------------------------------------------------------------------------


def test_rebase_attempt_scheduled_within_budget(conn: sqlite3.Connection) -> None:
    iid = _issue_id(conn)
    with (
        patch("orchctl.commands.reconcile.post_issue_comment") as mock_comment,
        patch("orchctl.commands.reconcile._run_git_rebase_playbook") as mock_playbook,
    ):
        state = _next_action_to_state(
            conn,
            area="workspace",
            issue_id=iid,
            number=55,
            retry_count=0,
            failure_class=FailureClass.GIT_CONFLICT,
            next_action=NextAction.REPAIR,
            dry_run=False,
        )
    assert state == "pending"
    row = conn.execute("SELECT retry_count FROM issues WHERE id = ?", (iid,)).fetchone()
    assert row["retry_count"] == 1
    mock_comment.assert_called_once()
    body = mock_comment.call_args[0][2]
    assert "git_conflict" in body
    mock_playbook.assert_called_once()


# ---------------------------------------------------------------------------
# Unit: _next_action_to_state — budget exhausted → blocker + needs-human
# ---------------------------------------------------------------------------


def test_blocker_created_on_budget_exhaustion(conn: sqlite3.Connection) -> None:
    iid = _issue_id(conn)
    _insert_attempt(conn, "r-001", iid, "failed", '{"prNumber": 20, "reason": "merge conflict in src/foo.ts"}')
    _insert_attempt(conn, "r-002", iid, "failed", '{"prNumber": 20, "reason": "rebase failed: conflict in src/bar.ts"}')

    with (
        patch("orchctl.commands.reconcile.post_issue_comment") as mock_comment,
        patch("orchctl.commands.reconcile.create_issue", return_value=88) as mock_create,
    ):
        state = _next_action_to_state(
            conn,
            area="workspace",
            issue_id=iid,
            number=55,
            retry_count=2,
            failure_class=FailureClass.GIT_CONFLICT,
            next_action=NextAction.REPAIR,
            dry_run=False,
            terminal_json='{"prNumber": 20, "reason": "rebase failed: conflict in src/bar.ts"}',
        )

    assert state == "needs-human"
    mock_create.assert_called_once()
    create_kwargs = mock_create.call_args
    title = create_kwargs[1]["title"] if create_kwargs[1] else create_kwargs[0][1]
    assert "blocker" in title.lower()
    assert "55" in title
    body = create_kwargs[1]["body"] if create_kwargs[1] else create_kwargs[0][2]
    assert "#55" in body
    assert "git_conflict" in body
    assert "merge conflict" in body

    comment_calls = mock_comment.call_args_list
    blocker_comments = [c for c in comment_calls if "#88" in str(c)]
    assert blocker_comments, "Expected a comment referencing the blocker issue #88"


def test_blocker_not_created_within_budget(conn: sqlite3.Connection) -> None:
    iid = _issue_id(conn)
    with (
        patch("orchctl.commands.reconcile.post_issue_comment"),
        patch("orchctl.commands.reconcile._run_git_rebase_playbook"),
        patch("orchctl.commands.reconcile.create_issue") as mock_create,
    ):
        state = _next_action_to_state(
            conn,
            area="workspace",
            issue_id=iid,
            number=55,
            retry_count=1,
            failure_class=FailureClass.GIT_CONFLICT,
            next_action=NextAction.REPAIR,
            dry_run=False,
        )

    assert state == "pending"
    mock_create.assert_not_called()


def test_rebase_playbook_not_called_on_budget_exhaustion(conn: sqlite3.Connection) -> None:
    iid = _issue_id(conn)
    with (
        patch("orchctl.commands.reconcile.post_issue_comment"),
        patch("orchctl.commands.reconcile.create_issue", return_value=88),
        patch("orchctl.commands.reconcile._run_git_rebase_playbook") as mock_playbook,
    ):
        state = _next_action_to_state(
            conn,
            area="workspace",
            issue_id=iid,
            number=55,
            retry_count=2,
            failure_class=FailureClass.GIT_CONFLICT,
            next_action=NextAction.REPAIR,
            dry_run=False,
        )

    assert state == "needs-human"
    mock_playbook.assert_not_called()


# ---------------------------------------------------------------------------
# Unit: _run_git_rebase_playbook — posts rebase context comment
# ---------------------------------------------------------------------------


def test_rebase_playbook_posts_comment_with_pr_and_reason(conn: sqlite3.Connection) -> None:
    terminal_json = json.dumps({"prNumber": 12, "reason": "merge conflict in src/index.ts"})
    with (
        patch("orchctl.commands.reconcile.get_pr_branch", return_value="feat/issue-55-foo"),
        patch("orchctl.commands.reconcile.post_issue_comment") as mock_comment,
    ):
        _run_git_rebase_playbook(conn, "workspace", 55, terminal_json)

    mock_comment.assert_called_once()
    body = mock_comment.call_args[0][2]
    assert "PR #12" in body
    assert "merge conflict in src/index.ts" in body
    assert "git_conflict" in body


def test_rebase_playbook_posts_comment_with_branch(conn: sqlite3.Connection) -> None:
    terminal_json = json.dumps({"prNumber": 12, "reason": "rebase failed"})
    with (
        patch("orchctl.commands.reconcile.get_pr_branch", return_value="feat/issue-55-my-branch"),
        patch("orchctl.commands.reconcile.post_issue_comment") as mock_comment,
    ):
        _run_git_rebase_playbook(conn, "workspace", 55, terminal_json)

    mock_comment.assert_called_once()
    body = mock_comment.call_args[0][2]
    assert "feat/issue-55-my-branch" in body


def test_rebase_playbook_posts_comment_without_conflict_reason(conn: sqlite3.Connection) -> None:
    terminal_json = json.dumps({"prNumber": 12})
    with (
        patch("orchctl.commands.reconcile.get_pr_branch", return_value="feat/issue-55-foo"),
        patch("orchctl.commands.reconcile.post_issue_comment") as mock_comment,
    ):
        _run_git_rebase_playbook(conn, "workspace", 55, terminal_json)

    mock_comment.assert_called_once()
    body = mock_comment.call_args[0][2]
    assert "unavailable" in body


def test_rebase_playbook_posts_comment_without_pr_number(conn: sqlite3.Connection) -> None:
    with (
        patch("orchctl.commands.reconcile.get_pr_branch") as mock_branch,
        patch("orchctl.commands.reconcile.post_issue_comment") as mock_comment,
    ):
        _run_git_rebase_playbook(conn, "workspace", 55, None)

    mock_branch.assert_not_called()
    mock_comment.assert_called_once()
    body = mock_comment.call_args[0][2]
    assert "git_conflict" in body


def test_rebase_playbook_renews_lease_before_second_gh_call(conn: sqlite3.Connection) -> None:
    terminal_json = json.dumps({"prNumber": 12, "reason": "merge conflict"})
    with (
        patch("orchctl.commands.reconcile.get_pr_branch", return_value="feat/foo"),
        patch("orchctl.commands.reconcile.renew") as mock_renew,
        patch("orchctl.commands.reconcile.post_issue_comment"),
    ):
        _run_git_rebase_playbook(
            conn, "workspace", 55, terminal_json, pid=42, owns_lease=True
        )

    mock_renew.assert_called_once_with(conn, "workspace", 42)


def test_rebase_playbook_no_renew_when_not_owner(conn: sqlite3.Connection) -> None:
    terminal_json = json.dumps({"prNumber": 12, "reason": "merge conflict"})
    with (
        patch("orchctl.commands.reconcile.get_pr_branch", return_value="feat/foo"),
        patch("orchctl.commands.reconcile.renew") as mock_renew,
        patch("orchctl.commands.reconcile.post_issue_comment"),
    ):
        _run_git_rebase_playbook(
            conn, "workspace", 55, terminal_json, pid=0, owns_lease=False
        )

    mock_renew.assert_not_called()


# ---------------------------------------------------------------------------
# Unit: _create_git_rebase_blocker_issue — failure history in body
# ---------------------------------------------------------------------------


def test_rebase_blocker_body_contains_conflict_history(conn: sqlite3.Connection) -> None:
    iid = _issue_id(conn)
    _insert_attempt(conn, "r-001", iid, "failed", '{"prNumber": 20, "reason": "conflict in src/a.ts"}')
    _insert_attempt(conn, "r-002", iid, "failed", '{"prNumber": 20, "reason": "conflict in src/b.ts"}')

    with (
        patch("orchctl.commands.reconcile.create_issue", return_value=200) as mock_create,
        patch("orchctl.commands.reconcile.post_issue_comment"),
    ):
        _create_git_rebase_blocker_issue(conn, "workspace", iid, 55, 2, None)

    mock_create.assert_called_once()
    body = mock_create.call_args[1]["body"]
    assert "conflict in src/a.ts" in body
    assert "conflict in src/b.ts" in body
    assert "#55" in body
    assert "workspace" in body
    assert "git_conflict" in body


def test_rebase_blocker_dry_run_skips_creation(conn: sqlite3.Connection) -> None:
    iid = _issue_id(conn)
    with (
        patch("orchctl.commands.reconcile.create_issue") as mock_create,
        patch("orchctl.commands.reconcile.post_issue_comment"),
    ):
        state = _next_action_to_state(
            conn,
            area="workspace",
            issue_id=iid,
            number=55,
            retry_count=2,
            failure_class=FailureClass.GIT_CONFLICT,
            next_action=NextAction.REPAIR,
            dry_run=True,
        )
    assert state == "needs-human"
    mock_create.assert_not_called()


def test_rebase_blocker_includes_requeue_instructions(conn: sqlite3.Connection) -> None:
    iid = _issue_id(conn)
    with (
        patch("orchctl.commands.reconcile.create_issue", return_value=201) as mock_create,
        patch("orchctl.commands.reconcile.post_issue_comment"),
    ):
        _create_git_rebase_blocker_issue(conn, "workspace", iid, 55, 1, None)

    body = mock_create.call_args[1]["body"]
    assert "requeue" in body
    assert "orchctl control requeue" in body
    assert "--area workspace" in body
    assert "--issue 55" in body
