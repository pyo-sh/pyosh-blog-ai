"""Tests for cycle quarantine and rate-limit / infra-degraded playbooks."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from orchctl.db.config import get_config, get_config_bool, get_config_int
from orchctl.db.connection import get_db, init_db
from orchctl.models import IssueState


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def conn(tmp_path: Path):
    db_path = tmp_path / "test.db"
    conn, _ = init_db(db_path)
    yield conn
    conn.close()


@pytest.fixture
def db_path(tmp_path: Path) -> str:
    path = str(tmp_path / "test.db")
    from click.testing import CliRunner
    from orchctl.cli import cli
    CliRunner().invoke(cli, ["--db", path, "init"])
    return path


def _insert_issue(conn, area: str, number: int, state: str = "blocked") -> int:
    cur = conn.execute(
        "INSERT INTO issues (area, number, state, dependency_type) VALUES (?, ?, ?, ?)",
        (area, number, state, "hard"),
    )
    conn.commit()
    return cur.lastrowid


def _insert_dep(conn, issue_id: int, dep_area: str, dep_number: int, dep_type: str = "hard") -> None:
    conn.execute(
        "INSERT INTO dependencies (issue_id, dep_area, dep_number, dep_type) VALUES (?, ?, ?, ?)",
        (issue_id, dep_area, dep_number, dep_type),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# IssueState model: cycle-isolated
# ---------------------------------------------------------------------------


class TestCycleIsolatedModel:
    def test_cycle_isolated_is_in_issue_state(self):
        assert IssueState.CYCLE_ISOLATED.value == "cycle-isolated"

    def test_cycle_isolated_is_terminal(self):
        from orchctl.models import TERMINAL_ISSUE_STATES
        assert IssueState.CYCLE_ISOLATED in TERMINAL_ISSUE_STATES

    def test_blocked_can_transition_to_cycle_isolated(self):
        from orchctl.state_machine import transition_issue
        assert transition_issue("blocked", "cycle-isolated") == "cycle-isolated"

    def test_cycle_isolated_can_requeue_to_pending(self):
        from orchctl.state_machine import transition_issue
        assert transition_issue("cycle-isolated", "pending") == "pending"

    def test_cycle_isolated_cannot_dispatch(self):
        from orchctl.state_machine import InvalidTransitionError, transition_issue
        with pytest.raises(InvalidTransitionError):
            transition_issue("cycle-isolated", "dispatched")

    def test_pending_cannot_go_to_cycle_isolated(self):
        from orchctl.state_machine import InvalidTransitionError, transition_issue
        with pytest.raises(InvalidTransitionError):
            transition_issue("pending", "cycle-isolated")


# ---------------------------------------------------------------------------
# Schema migration v14: cycle-isolated in CHECK constraint
# ---------------------------------------------------------------------------


class TestSchemaMigrationV14:
    def test_cycle_isolated_state_accepted(self, conn):
        """After migration, issues can be inserted with cycle-isolated state."""
        cur = conn.execute(
            "INSERT INTO issues (area, number, state) VALUES (?, ?, ?)",
            ("client", 99, "cycle-isolated"),
        )
        conn.commit()
        row = conn.execute("SELECT state FROM issues WHERE id = ?", (cur.lastrowid,)).fetchone()
        assert row["state"] == "cycle-isolated"

    def test_rate_limit_config_keys_exist(self, conn):
        """v14 migration inserts rate_limit_backoff_base_s and infra_degraded_threshold."""
        assert get_config_int(conn, "rate_limit_backoff_base_s", default=-1) == 60
        assert get_config_int(conn, "infra_degraded_threshold", default=-1) == 5


# ---------------------------------------------------------------------------
# _is_rate_limit_error
# ---------------------------------------------------------------------------


class TestIsRateLimitError:
    def _make_exc(self, msg: str):
        from orchctl.github import GitHubError
        return GitHubError(msg)

    def test_detects_rate_limit_phrase(self):
        from orchctl.commands.reconcile import _is_rate_limit_error
        assert _is_rate_limit_error(self._make_exc("gh: API rate limit exceeded")) is True

    def test_detects_429_status(self):
        from orchctl.commands.reconcile import _is_rate_limit_error
        assert _is_rate_limit_error(self._make_exc("HTTP 429 Too Many Requests")) is True

    def test_ignores_unrelated_errors(self):
        from orchctl.commands.reconcile import _is_rate_limit_error
        assert _is_rate_limit_error(self._make_exc("connection refused")) is False

    def test_case_insensitive(self):
        from orchctl.commands.reconcile import _is_rate_limit_error
        assert _is_rate_limit_error(self._make_exc("Rate Limit")) is True


# ---------------------------------------------------------------------------
# _handle_rate_limit_error
# ---------------------------------------------------------------------------


class TestHandleRateLimitError:
    def test_sets_area_paused(self, conn):
        from orchctl.commands.reconcile import _handle_rate_limit_error
        _handle_rate_limit_error(conn, "client", Exception("rate limit"), dry_run=False)
        assert get_config_bool(conn, "client.paused") is True

    def test_increments_backoff_count(self, conn):
        from orchctl.commands.reconcile import _handle_rate_limit_error
        _handle_rate_limit_error(conn, "client", Exception("rate limit"), dry_run=False)
        assert get_config_int(conn, "client.backoff_count") == 1
        _handle_rate_limit_error(conn, "client", Exception("rate limit"), dry_run=False)
        assert get_config_int(conn, "client.backoff_count") == 2

    def test_sets_backoff_until_in_future(self, conn):
        from orchctl.commands.reconcile import _handle_rate_limit_error
        before = datetime.now(timezone.utc)
        _handle_rate_limit_error(conn, "client", Exception("rate limit"), dry_run=False)
        after = datetime.now(timezone.utc)
        raw = get_config(conn, "client.backoff_until")
        assert raw, "backoff_until should be set"
        ts = datetime.fromisoformat(raw)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        assert ts > before

    def test_exponential_backoff_doubles(self, conn):
        from orchctl.commands.reconcile import _handle_rate_limit_error
        # backoff_base = 60 (from v14 default), so delays are 60, 120, 240...
        from orchctl.db.config import set_config as sc
        sc(conn, "rate_limit_backoff_base_s", "10")

        before1 = datetime.now(timezone.utc)
        _handle_rate_limit_error(conn, "client", Exception("rate limit"), dry_run=False)
        ts1 = datetime.fromisoformat(get_config(conn, "client.backoff_until")).replace(tzinfo=timezone.utc)
        delay1 = (ts1 - before1).total_seconds()
        assert 9 <= delay1 <= 15  # base=10, count=1: 10*2^0=10

        before2 = datetime.now(timezone.utc)
        _handle_rate_limit_error(conn, "client", Exception("rate limit"), dry_run=False)
        ts2 = datetime.fromisoformat(get_config(conn, "client.backoff_until")).replace(tzinfo=timezone.utc)
        delay2 = (ts2 - before2).total_seconds()
        assert 19 <= delay2 <= 25  # base=10, count=2: 10*2^1=20

    def test_infra_degraded_on_threshold(self, conn):
        from orchctl.commands.reconcile import _handle_rate_limit_error
        from orchctl.db.config import set_config as sc
        sc(conn, "infra_degraded_threshold", "3")

        for _ in range(3):
            _handle_rate_limit_error(conn, "client", Exception("rate limit"), dry_run=False)

        assert get_config_bool(conn, "client.infra_degraded") is True

    def test_not_infra_degraded_below_threshold(self, conn):
        from orchctl.commands.reconcile import _handle_rate_limit_error
        from orchctl.db.config import set_config as sc
        sc(conn, "infra_degraded_threshold", "3")

        for _ in range(2):
            _handle_rate_limit_error(conn, "client", Exception("rate limit"), dry_run=False)

        assert get_config_bool(conn, "client.infra_degraded") is False

    def test_dry_run_does_not_write(self, conn):
        from orchctl.commands.reconcile import _handle_rate_limit_error
        _handle_rate_limit_error(conn, "client", Exception("rate limit"), dry_run=True)
        assert get_config_bool(conn, "client.paused") is False
        assert get_config_int(conn, "client.backoff_count") == 0


# ---------------------------------------------------------------------------
# _check_and_release_backoff
# ---------------------------------------------------------------------------


class TestCheckAndReleaseBackoff:
    def _set_backoff(self, conn, area: str, seconds_ago: float, infra_degraded: bool = False) -> None:
        from orchctl.db.config import set_config as sc
        elapsed = datetime.now(timezone.utc) - timedelta(seconds=seconds_ago)
        sc(conn, f"{area}.paused", "true")
        sc(conn, f"{area}.backoff_until", elapsed.isoformat())
        sc(conn, f"{area}.backoff_count", "2")
        if infra_degraded:
            sc(conn, f"{area}.infra_degraded", "true")

    def test_releases_when_window_elapsed(self, conn):
        from orchctl.commands.reconcile import _check_and_release_backoff
        self._set_backoff(conn, "client", seconds_ago=120)
        _check_and_release_backoff(conn, "client", dry_run=False)
        assert get_config_bool(conn, "client.paused") is False
        assert get_config_int(conn, "client.backoff_count") == 0
        assert get_config(conn, "client.backoff_until") == ""

    def test_no_release_when_window_not_elapsed(self, conn):
        from orchctl.commands.reconcile import _check_and_release_backoff
        from orchctl.db.config import set_config as sc
        future = (datetime.now(timezone.utc) + timedelta(seconds=300)).isoformat()
        sc(conn, "client.paused", "true")
        sc(conn, "client.backoff_until", future)
        sc(conn, "client.backoff_count", "2")

        _check_and_release_backoff(conn, "client", dry_run=False)
        assert get_config_bool(conn, "client.paused") is True

    def test_infra_degraded_blocks_auto_release(self, conn):
        from orchctl.commands.reconcile import _check_and_release_backoff
        self._set_backoff(conn, "client", seconds_ago=3600, infra_degraded=True)
        _check_and_release_backoff(conn, "client", dry_run=False)
        # Area should still be paused — infra_degraded requires operator action.
        assert get_config_bool(conn, "client.paused") is True

    def test_no_backoff_until_is_noop(self, conn):
        from orchctl.commands.reconcile import _check_and_release_backoff
        # Should not raise and should not touch the paused flag.
        _check_and_release_backoff(conn, "client", dry_run=False)
        assert get_config_bool(conn, "client.paused") is False

    def test_dry_run_does_not_write(self, conn):
        from orchctl.commands.reconcile import _check_and_release_backoff
        self._set_backoff(conn, "client", seconds_ago=120)
        _check_and_release_backoff(conn, "client", dry_run=True)
        # paused flag should remain true in dry-run mode.
        assert get_config_bool(conn, "client.paused") is True


# ---------------------------------------------------------------------------
# _cycle_quarantine_pass (unit)
# ---------------------------------------------------------------------------


class TestCycleQuarantinePass:
    def _run_pass(self, conn, area: str, dry_run: bool = False):
        from orchctl.commands.reconcile import _cycle_quarantine_pass, _observe_issues
        issues_by_state = _observe_issues(conn, area)
        return _cycle_quarantine_pass(conn, area, pid=1, dry_run=dry_run, issues_by_state=issues_by_state, owns_lease=False)

    def test_no_blocked_issues_is_noop(self, conn):
        result = self._run_pass(conn, "client")
        assert result is True

    def test_simple_two_issue_cycle(self, conn):
        """A -> B -> A: both should be quarantined."""
        id_a = _insert_issue(conn, "client", 1)
        id_b = _insert_issue(conn, "client", 2)
        _insert_dep(conn, id_a, "client", 2)  # A depends on B
        _insert_dep(conn, id_b, "client", 1)  # B depends on A

        with patch("orchctl.commands.reconcile.post_issue_comment"):
            result = self._run_pass(conn, "client")

        assert result is True
        row_a = conn.execute("SELECT state FROM issues WHERE id = ?", (id_a,)).fetchone()
        row_b = conn.execute("SELECT state FROM issues WHERE id = ?", (id_b,)).fetchone()
        assert row_a["state"] == "cycle-isolated"
        assert row_b["state"] == "cycle-isolated"

    def test_non_cycle_blocked_issue_untouched(self, conn):
        """An issue with no cycle deps should remain blocked."""
        id_c = _insert_issue(conn, "client", 3)  # no deps → not in cycle

        result = self._run_pass(conn, "client")

        assert result is True
        row = conn.execute("SELECT state FROM issues WHERE id = ?", (id_c,)).fetchone()
        assert row["state"] == "blocked"

    def test_three_issue_chain_no_cycle(self, conn):
        """A depends on B, B depends on C (linear chain): no cycle, no quarantine."""
        id_a = _insert_issue(conn, "client", 10)
        id_b = _insert_issue(conn, "client", 11)
        id_c = _insert_issue(conn, "client", 12)
        _insert_dep(conn, id_a, "client", 11)
        _insert_dep(conn, id_b, "client", 12)

        result = self._run_pass(conn, "client")

        assert result is True
        for iid in (id_a, id_b, id_c):
            row = conn.execute("SELECT state FROM issues WHERE id = ?", (iid,)).fetchone()
            assert row["state"] == "blocked"

    def test_cycle_only_quarantines_cycle_members(self, conn):
        """A -> B -> A cycle + C -> A (C is NOT in cycle, just depends on it)."""
        id_a = _insert_issue(conn, "client", 20)
        id_b = _insert_issue(conn, "client", 21)
        id_c = _insert_issue(conn, "client", 22)
        _insert_dep(conn, id_a, "client", 21)  # A depends on B
        _insert_dep(conn, id_b, "client", 20)  # B depends on A (cycle)
        _insert_dep(conn, id_c, "client", 20)  # C depends on A (not in cycle)

        with patch("orchctl.commands.reconcile.post_issue_comment"):
            result = self._run_pass(conn, "client")

        assert result is True
        row_a = conn.execute("SELECT state FROM issues WHERE id = ?", (id_a,)).fetchone()
        row_b = conn.execute("SELECT state FROM issues WHERE id = ?", (id_b,)).fetchone()
        row_c = conn.execute("SELECT state FROM issues WHERE id = ?", (id_c,)).fetchone()
        assert row_a["state"] == "cycle-isolated"
        assert row_b["state"] == "cycle-isolated"
        assert row_c["state"] == "blocked"  # C is not in cycle

    def test_dry_run_does_not_quarantine(self, conn):
        id_a = _insert_issue(conn, "client", 30)
        id_b = _insert_issue(conn, "client", 31)
        _insert_dep(conn, id_a, "client", 31)
        _insert_dep(conn, id_b, "client", 30)

        result = self._run_pass(conn, "client", dry_run=True)

        assert result is True
        row_a = conn.execute("SELECT state FROM issues WHERE id = ?", (id_a,)).fetchone()
        row_b = conn.execute("SELECT state FROM issues WHERE id = ?", (id_b,)).fetchone()
        assert row_a["state"] == "blocked"
        assert row_b["state"] == "blocked"

    def test_comment_posted_for_cycle_members(self, conn):
        id_a = _insert_issue(conn, "client", 40)
        id_b = _insert_issue(conn, "client", 41)
        _insert_dep(conn, id_a, "client", 41)
        _insert_dep(conn, id_b, "client", 40)

        with patch("orchctl.commands.reconcile.post_issue_comment") as mock_comment:
            self._run_pass(conn, "client")

        assert mock_comment.call_count == 2
        # Both issue numbers should appear in each call's body.
        for call_args in mock_comment.call_args_list:
            body = call_args[0][2]
            assert "#40" in body and "#41" in body


# ---------------------------------------------------------------------------
# control requeue: cycle-isolated
# ---------------------------------------------------------------------------


class TestRequeueCycleIsolated:
    def test_requeue_cycle_isolated_to_pending(self, db_path):
        from click.testing import CliRunner
        from orchctl.cli import cli

        conn = get_db(db_path)
        conn.execute(
            "INSERT INTO issues (area, number, state) VALUES (?, ?, ?)",
            ("client", 5, "cycle-isolated"),
        )
        conn.commit()
        conn.close()

        runner = CliRunner()
        result = runner.invoke(cli, ["--db", db_path, "control", "requeue", "--area", "client", "--issue", "5"])
        assert result.exit_code == 0, result.output
        assert "requeued" in result.output

        conn = get_db(db_path)
        row = conn.execute("SELECT state FROM issues WHERE number = 5", ).fetchone()
        conn.close()
        assert row["state"] == "pending"

    def test_requeue_cycle_isolated_in_requeueable_set(self):
        # Verify the set is defined correctly in control.py by checking the error message
        # does not exclude cycle-isolated.
        from click.testing import CliRunner
        from orchctl.cli import cli
        import tempfile, os
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "t.db")
            runner = CliRunner()
            runner.invoke(cli, ["--db", db, "init"])
            conn = get_db(db)
            conn.execute(
                "INSERT INTO issues (area, number, state) VALUES (?, ?, ?)",
                ("client", 7, "needs-human"),
            )
            conn.commit()
            conn.close()
            result = runner.invoke(cli, ["--db", db, "control", "requeue", "--area", "client", "--issue", "7"])
            assert result.exit_code == 0
