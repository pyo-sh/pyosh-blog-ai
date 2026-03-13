"""Tests for advanced scheduling: priority ordering, age/retry weights, max_awaiting_merge."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from orchctl.db.connection import get_db, init_db
from orchctl.db.config import get_config
from orchctl.github import GitHubIssue, parse_priority_from_body


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_db(tmp_path: Path):
    return tmp_path / "test.db"


@pytest.fixture
def db_conn(tmp_db):
    conn, _ = init_db(tmp_db)
    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# parse_priority_from_body
# ---------------------------------------------------------------------------


class TestParsePriorityFromBody:
    def test_no_orchestrator_block_returns_zero(self):
        assert parse_priority_from_body("## No fenced block here") == 0

    def test_orchestrator_block_without_priority_returns_zero(self):
        body = "```orchestrator\nhard: #10\n```"
        assert parse_priority_from_body(body) == 0

    def test_priority_extracted_from_block(self):
        body = "```orchestrator\npriority: 5\nhard: #10\n```"
        assert parse_priority_from_body(body) == 5

    def test_priority_zero_is_valid(self):
        body = "```orchestrator\npriority: 0\n```"
        assert parse_priority_from_body(body) == 0

    def test_priority_large_value(self):
        body = "```orchestrator\npriority: 100\n```"
        assert parse_priority_from_body(body) == 100

    def test_priority_with_surrounding_whitespace(self):
        body = "```orchestrator\n  priority : 7  \n```"
        assert parse_priority_from_body(body) == 7

    def test_only_first_block_considered(self):
        body = (
            "```orchestrator\npriority: 3\n```"
            "\n\nsome text\n\n"
            "```orchestrator\npriority: 9\n```"
        )
        # First block wins
        assert parse_priority_from_body(body) == 3

    def test_non_integer_priority_returns_zero(self):
        body = "```orchestrator\npriority: high\n```"
        assert parse_priority_from_body(body) == 0

    def test_priority_outside_block_ignored(self):
        body = "priority: 10\n\n```orchestrator\nhard: #1\n```"
        assert parse_priority_from_body(body) == 0


# ---------------------------------------------------------------------------
# GitHubIssue priority field
# ---------------------------------------------------------------------------


class TestGitHubIssuePriority:
    def test_default_priority_is_zero(self):
        issue = GitHubIssue(number=1, title="Test")
        assert issue.priority == 0

    def test_priority_set_explicitly(self):
        issue = GitHubIssue(number=1, title="Test", priority=5)
        assert issue.priority == 5


# ---------------------------------------------------------------------------
# _sort_pending: priority ordering
# ---------------------------------------------------------------------------


class TestSortPending:
    def _make_row(self, number: int, priority: int, retry_count: int = 0, created_at: str = "2024-01-01 00:00:00"):
        """Build a minimal sqlite3.Row-like dict for testing."""
        return {"number": number, "priority": priority, "retry_count": retry_count, "created_at": created_at}

    def test_higher_priority_dispatched_first(self):
        from orchctl.commands.reconcile import _sort_pending

        rows = [
            self._make_row(1, priority=0),
            self._make_row(2, priority=5),
            self._make_row(3, priority=2),
        ]
        sorted_rows = _sort_pending(rows, priority_weight=1.0, age_weight=0.0, retry_weight=0.0)
        numbers = [r["number"] for r in sorted_rows]
        assert numbers == [2, 3, 1]

    def test_equal_priority_older_dispatched_first(self):
        from orchctl.commands.reconcile import _sort_pending

        rows = [
            self._make_row(1, priority=0, created_at="2024-06-01 00:00:00"),
            self._make_row(2, priority=0, created_at="2024-01-01 00:00:00"),
        ]
        sorted_rows = _sort_pending(rows, priority_weight=1.0, age_weight=1.0, retry_weight=0.0)
        numbers = [r["number"] for r in sorted_rows]
        # Issue 2 is older so should come first
        assert numbers[0] == 2

    def test_higher_retry_count_deprioritised(self):
        from orchctl.commands.reconcile import _sort_pending

        rows = [
            self._make_row(1, priority=0, retry_count=3),
            self._make_row(2, priority=0, retry_count=0),
        ]
        sorted_rows = _sort_pending(rows, priority_weight=0.0, age_weight=0.0, retry_weight=1.0)
        numbers = [r["number"] for r in sorted_rows]
        # Issue 2 has no retries so gets dispatched first
        assert numbers[0] == 2

    def test_priority_beats_age(self):
        from orchctl.commands.reconcile import _sort_pending

        rows = [
            self._make_row(1, priority=10, created_at="2024-06-01 00:00:00"),
            self._make_row(2, priority=0, created_at="2020-01-01 00:00:00"),
        ]
        # priority_weight=100 makes priority dominant
        sorted_rows = _sort_pending(rows, priority_weight=100.0, age_weight=0.001, retry_weight=0.0)
        assert sorted_rows[0]["number"] == 1

    def test_all_zero_weights_preserves_original_order(self):
        from orchctl.commands.reconcile import _sort_pending

        rows = [
            self._make_row(1, priority=0),
            self._make_row(2, priority=0),
            self._make_row(3, priority=0),
        ]
        sorted_rows = _sort_pending(rows, priority_weight=0.0, age_weight=0.0, retry_weight=0.0)
        # All scores equal — stable sort preserves insertion order
        assert [r["number"] for r in sorted_rows] == [1, 2, 3]

    def test_invalid_created_at_treated_as_zero_age(self):
        """Bad created_at is treated as age=0 (no crash, no bonus age boost)."""
        from orchctl.commands.reconcile import _sort_pending

        rows = [
            self._make_row(1, priority=0, created_at="bad-date"),
            self._make_row(2, priority=0, created_at="bad-date"),
        ]
        # Both have bad dates -> both age=0 -> scores equal -> stable order preserved
        sorted_rows = _sort_pending(rows, priority_weight=1.0, age_weight=1.0, retry_weight=0.0)
        assert [r["number"] for r in sorted_rows] == [1, 2]


# ---------------------------------------------------------------------------
# _count_awaiting_merge
# ---------------------------------------------------------------------------


class TestCountAwaitingMerge:
    def test_empty_db_returns_zero(self, db_conn):
        from orchctl.commands.reconcile import _count_awaiting_merge

        assert _count_awaiting_merge(db_conn) == 0

    def test_completed_none_merge_state_counted(self, db_conn):
        from orchctl.commands.reconcile import _count_awaiting_merge

        db_conn.execute(
            "INSERT INTO issues (area, number, state, merge_state) VALUES ('client', 1, 'completed', 'none')"
        )
        db_conn.commit()
        assert _count_awaiting_merge(db_conn) == 1

    def test_completed_eligible_merge_state_counted(self, db_conn):
        from orchctl.commands.reconcile import _count_awaiting_merge

        db_conn.execute(
            "INSERT INTO issues (area, number, state, merge_state) VALUES ('client', 2, 'completed', 'eligible')"
        )
        db_conn.commit()
        assert _count_awaiting_merge(db_conn) == 1

    def test_completed_done_merge_state_not_counted(self, db_conn):
        from orchctl.commands.reconcile import _count_awaiting_merge

        db_conn.execute(
            "INSERT INTO issues (area, number, state, merge_state) VALUES ('client', 3, 'completed', 'done')"
        )
        db_conn.commit()
        assert _count_awaiting_merge(db_conn) == 0

    def test_completed_rejected_not_counted(self, db_conn):
        from orchctl.commands.reconcile import _count_awaiting_merge

        db_conn.execute(
            "INSERT INTO issues (area, number, state, merge_state) VALUES ('client', 4, 'completed', 'rejected')"
        )
        db_conn.commit()
        assert _count_awaiting_merge(db_conn) == 0

    def test_non_completed_state_not_counted(self, db_conn):
        from orchctl.commands.reconcile import _count_awaiting_merge

        db_conn.execute(
            "INSERT INTO issues (area, number, state, merge_state) VALUES ('client', 5, 'dispatched', 'none')"
        )
        db_conn.commit()
        assert _count_awaiting_merge(db_conn) == 0

    def test_mixed_states_only_counts_unmerged_completed(self, db_conn):
        from orchctl.commands.reconcile import _count_awaiting_merge

        db_conn.executemany(
            "INSERT INTO issues (area, number, state, merge_state) VALUES ('client', ?, ?, ?)",
            [
                (1, "completed", "none"),
                (2, "completed", "eligible"),
                (3, "completed", "done"),
                (4, "completed", "rejected"),
                (5, "dispatched", "none"),
                (6, "pending", "none"),
            ],
        )
        db_conn.commit()
        assert _count_awaiting_merge(db_conn) == 2


# ---------------------------------------------------------------------------
# max_awaiting_merge admission gate (dispatch_pass integration)
# ---------------------------------------------------------------------------


class TestMaxAwaitingMergeGate:
    def test_gate_blocks_dispatch_when_limit_reached(self, tmp_db):
        from click.testing import CliRunner
        from orchctl.cli import cli
        from orchctl.db.lease import acquire, release
        from orchctl.commands.reconcile import _run_pass

        runner = CliRunner()
        runner.invoke(cli, ["--db", str(tmp_db), "init"])

        conn = get_db(str(tmp_db))
        conn.execute("UPDATE config SET value='3' WHERE key='max_awaiting_merge'")
        # Insert 3 completed+unmerged PRs (at the limit)
        conn.executemany(
            "INSERT INTO issues (area, number, state, merge_state) VALUES ('client', ?, 'completed', 'eligible')",
            [(100,), (101,), (102,)],
        )
        # Insert a pending issue that should NOT be dispatched
        conn.execute(
            "INSERT INTO issues (area, number, state) VALUES ('client', 200, 'pending')"
        )
        conn.commit()

        dispatched = []
        pid = 9999
        acquire(conn, "client", pid)
        _run_pass(
            conn,
            "client",
            pid,
            dry_run=False,
            dispatch_fn=lambda area, iid, num, aid: dispatched.append(num),
        )
        release(conn, "client", pid)
        conn.close()

        assert dispatched == []

    def test_gate_allows_dispatch_below_limit(self, tmp_db):
        from click.testing import CliRunner
        from orchctl.cli import cli
        from orchctl.db.lease import acquire, release
        from orchctl.commands.reconcile import _run_pass

        runner = CliRunner()
        runner.invoke(cli, ["--db", str(tmp_db), "init"])

        conn = get_db(str(tmp_db))
        conn.execute("UPDATE config SET value='3' WHERE key='max_awaiting_merge'")
        # Only 2 completed+unmerged (below limit of 3)
        conn.executemany(
            "INSERT INTO issues (area, number, state, merge_state) VALUES ('client', ?, 'completed', 'eligible')",
            [(100,), (101,)],
        )
        conn.execute(
            "INSERT INTO issues (area, number, state) VALUES ('client', 200, 'pending')"
        )
        conn.commit()

        dispatched = []
        pid = 9999
        acquire(conn, "client", pid)
        _run_pass(
            conn,
            "client",
            pid,
            dry_run=False,
            dispatch_fn=lambda area, iid, num, aid: dispatched.append(num),
        )
        release(conn, "client", pid)
        conn.close()

        assert 200 in dispatched

    def test_gate_disabled_when_zero(self, tmp_db):
        from click.testing import CliRunner
        from orchctl.cli import cli
        from orchctl.db.lease import acquire, release
        from orchctl.commands.reconcile import _run_pass

        runner = CliRunner()
        runner.invoke(cli, ["--db", str(tmp_db), "init"])

        conn = get_db(str(tmp_db))
        # max_awaiting_merge=0 means no limit
        conn.execute("UPDATE config SET value='0' WHERE key='max_awaiting_merge'")
        conn.executemany(
            "INSERT INTO issues (area, number, state, merge_state) VALUES ('client', ?, 'completed', 'none')",
            [(100,), (101,), (102,), (103,), (104,)],
        )
        conn.execute(
            "INSERT INTO issues (area, number, state) VALUES ('client', 200, 'pending')"
        )
        conn.commit()

        dispatched = []
        pid = 9999
        acquire(conn, "client", pid)
        _run_pass(
            conn,
            "client",
            pid,
            dry_run=False,
            dispatch_fn=lambda area, iid, num, aid: dispatched.append(num),
        )
        release(conn, "client", pid)
        conn.close()

        assert 200 in dispatched


# ---------------------------------------------------------------------------
# Priority-based dispatch ordering (reconcile integration)
# ---------------------------------------------------------------------------


class TestPriorityDispatchOrdering:
    def test_high_priority_issue_dispatched_first(self, tmp_db):
        """With max_concurrent=1, only the highest-priority issue is dispatched."""
        from click.testing import CliRunner
        from orchctl.cli import cli
        from orchctl.db.lease import acquire, release
        from orchctl.commands.reconcile import _run_pass

        runner = CliRunner()
        runner.invoke(cli, ["--db", str(tmp_db), "init"])

        conn = get_db(str(tmp_db))
        # Limit to 1 concurrent dispatch so only one issue goes through
        conn.execute("UPDATE config SET value='1' WHERE key='max_concurrent'")
        conn.execute("UPDATE config SET value='1' WHERE key='max_open_pr'")
        # Disable age weight to isolate priority ordering
        conn.execute("UPDATE config SET value='0.0' WHERE key='scheduling_age_weight'")

        conn.executemany(
            "INSERT INTO issues (area, number, state, priority) VALUES ('client', ?, 'pending', ?)",
            [(10, 0), (11, 5), (12, 2)],
        )
        conn.commit()

        dispatched = []
        pid = 9999
        acquire(conn, "client", pid)
        _run_pass(
            conn,
            "client",
            pid,
            dry_run=False,
            dispatch_fn=lambda area, iid, num, aid: dispatched.append(num),
        )
        release(conn, "client", pid)
        conn.close()

        assert len(dispatched) == 1
        assert dispatched[0] == 11  # highest priority


# ---------------------------------------------------------------------------
# Schema v11: priority column and config keys
# ---------------------------------------------------------------------------


def test_schema_v11_priority_column(tmp_db):
    conn, _ = init_db(tmp_db)
    # Check that the priority column exists and defaults to 0
    conn.execute("INSERT INTO issues (area, number, state) VALUES ('client', 1, 'pending')")
    conn.commit()
    row = conn.execute("SELECT priority FROM issues WHERE number=1").fetchone()
    assert row[0] == 0
    conn.close()


def test_schema_v11_config_defaults(tmp_db):
    conn, _ = init_db(tmp_db)
    rows = {r["key"]: r["value"] for r in conn.execute("SELECT key, value FROM config")}
    conn.close()
    assert rows["scheduling_priority_weight"] == "1.0"
    assert rows["scheduling_age_weight"] == "0.1"
    assert rows["scheduling_retry_weight"] == "1.0"
    assert rows["max_awaiting_merge"] == "0"


# ---------------------------------------------------------------------------
# Policy apply: scheduling section + max_awaiting_merge
# ---------------------------------------------------------------------------


class TestApplyPolicyScheduling:
    @pytest.fixture
    def conn(self, tmp_db):
        c, _ = init_db(tmp_db)
        yield c
        c.close()

    def test_apply_scheduling_section(self, conn):
        from orchctl.policy import apply_policy

        policy = {
            "scheduling": {
                "priority_weight": 2.5,
                "age_weight": 0.5,
                "retry_weight": 3.0,
            }
        }
        changed = apply_policy(conn, policy)
        assert "scheduling_priority_weight" in changed
        assert "scheduling_age_weight" in changed
        assert "scheduling_retry_weight" in changed
        assert get_config(conn, "scheduling_priority_weight") == "2.5"
        assert get_config(conn, "scheduling_age_weight") == "0.5"
        assert get_config(conn, "scheduling_retry_weight") == "3.0"

    def test_apply_max_awaiting_merge(self, conn):
        from orchctl.policy import apply_policy

        policy = {"guardrails": {"max_awaiting_merge": 5}}
        changed = apply_policy(conn, policy)
        assert "max_awaiting_merge" in changed
        assert get_config(conn, "max_awaiting_merge") == "5"

    def test_apply_scheduling_no_change_when_same_values(self, conn):
        from orchctl.policy import apply_policy

        policy = {"scheduling": {"priority_weight": 1.0}}
        apply_policy(conn, policy)
        changed = apply_policy(conn, policy)
        assert changed == []

    def test_apply_empty_scheduling_changes_nothing(self, conn):
        from orchctl.policy import apply_policy

        changed = apply_policy(conn, {"scheduling": {}})
        assert changed == []


# ---------------------------------------------------------------------------
# Discovery: priority stored when issue is enqueued
# ---------------------------------------------------------------------------


class TestDiscoveryPriorityStore:
    def test_enqueue_stores_priority(self, db_conn):
        from orchctl.commands.reconcile import _enqueue_or_reopen

        _enqueue_or_reopen(db_conn, "client", 42, dry_run=False, priority=7)

        row = db_conn.execute(
            "SELECT priority FROM issues WHERE area='client' AND number=42"
        ).fetchone()
        assert row[0] == 7

    def test_enqueue_default_priority_zero(self, db_conn):
        from orchctl.commands.reconcile import _enqueue_or_reopen

        _enqueue_or_reopen(db_conn, "client", 43, dry_run=False)

        row = db_conn.execute(
            "SELECT priority FROM issues WHERE area='client' AND number=43"
        ).fetchone()
        assert row[0] == 0

    def test_enqueue_dry_run_does_not_store(self, db_conn):
        from orchctl.commands.reconcile import _enqueue_or_reopen

        _enqueue_or_reopen(db_conn, "client", 44, dry_run=True, priority=5)

        row = db_conn.execute(
            "SELECT id FROM issues WHERE area='client' AND number=44"
        ).fetchone()
        assert row is None
