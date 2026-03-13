"""Tests for orchctl.heartbeat — multi-signal heartbeat collection and stall detection."""

from __future__ import annotations

import json
import os
import sqlite3
import time
from unittest.mock import MagicMock, patch

import pytest

from orchctl.db.connection import init_db
from orchctl.heartbeat import (
    STALL_MIN_ABSENT,
    SignalSnapshot,
    attempt_dir_path,
    check_stall,
    collect_signals,
    get_last_cpu_jiffies,
    record_heartbeat,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def conn(tmp_path):
    db_path = tmp_path / "test.db"
    c, _ = init_db(db_path)
    yield c
    c.close()


@pytest.fixture()
def running_attempt(conn):
    """Insert a minimal running issue + attempt. Returns (issue_id, attempt_id)."""
    conn.execute(
        "INSERT INTO issues (area, number, state) VALUES ('workspace', 42, 'dispatched')"
    )
    conn.commit()
    issue_id = conn.execute(
        "SELECT id FROM issues WHERE area='workspace' AND number=42"
    ).fetchone()["id"]
    attempt_id = "issue-42-aaaa0001"
    conn.execute(
        "INSERT INTO attempts (attempt_id, issue_id, status) VALUES (?, ?, 'running')",
        (attempt_id, issue_id),
    )
    conn.commit()
    return issue_id, attempt_id


# ---------------------------------------------------------------------------
# SignalSnapshot unit tests
# ---------------------------------------------------------------------------


class TestSignalSnapshot:
    def test_absent_count_all_present(self):
        s = SignalSnapshot(pr_activity=True, state_mtime=True, log_mtime=True, cpu_delta=True)
        assert s.absent_count == 0

    def test_absent_count_all_absent(self):
        s = SignalSnapshot(pr_activity=False, state_mtime=False, log_mtime=False, cpu_delta=False)
        assert s.absent_count == 4

    def test_absent_count_mixed(self):
        s = SignalSnapshot(pr_activity=True, state_mtime=False, log_mtime=False, cpu_delta=True)
        assert s.absent_count == 2

    def test_is_stalled_below_threshold(self):
        s = SignalSnapshot(pr_activity=False, state_mtime=True, log_mtime=True, cpu_delta=True)
        assert s.absent_count == 1
        assert not s.is_stalled()

    def test_is_stalled_at_threshold(self):
        s = SignalSnapshot(pr_activity=False, state_mtime=False, log_mtime=True, cpu_delta=True)
        assert s.absent_count == STALL_MIN_ABSENT
        assert s.is_stalled()

    def test_is_stalled_above_threshold(self):
        s = SignalSnapshot(pr_activity=False, state_mtime=False, log_mtime=False, cpu_delta=False)
        assert s.is_stalled()

    def test_to_json_round_trips(self):
        s = SignalSnapshot(
            pr_activity=True, state_mtime=False, log_mtime=True, cpu_delta=False,
            cpu_jiffies=12345,
        )
        data = json.loads(s.to_json())
        assert data["pr_activity"] is True
        assert data["state_mtime"] is False
        assert data["cpu_jiffies"] == 12345

    def test_custom_min_absent(self):
        s = SignalSnapshot(pr_activity=False, state_mtime=True, log_mtime=True, cpu_delta=True)
        assert not s.is_stalled(min_absent=2)
        assert s.is_stalled(min_absent=1)


# ---------------------------------------------------------------------------
# record_heartbeat / get_last_cpu_jiffies
# ---------------------------------------------------------------------------


class TestHeartbeatDB:
    def test_record_and_retrieve_cpu_jiffies(self, conn, running_attempt):
        _, attempt_id = running_attempt
        snap = SignalSnapshot(
            pr_activity=True, state_mtime=True, log_mtime=False, cpu_delta=True,
            cpu_jiffies=9876,
        )
        record_heartbeat(conn, attempt_id, snap)

        jiffies = get_last_cpu_jiffies(conn, attempt_id)
        assert jiffies == 9876

    def test_get_last_cpu_jiffies_no_rows(self, conn):
        assert get_last_cpu_jiffies(conn, "nonexistent-attempt") is None

    def test_get_last_cpu_jiffies_null_value(self, conn, running_attempt):
        _, attempt_id = running_attempt
        snap = SignalSnapshot(
            pr_activity=False, state_mtime=False, log_mtime=False, cpu_delta=False,
            cpu_jiffies=None,
        )
        record_heartbeat(conn, attempt_id, snap)
        assert get_last_cpu_jiffies(conn, attempt_id) is None

    def test_record_multiple_returns_latest(self, conn, running_attempt):
        _, attempt_id = running_attempt
        for jiffies in [100, 200, 300]:
            snap = SignalSnapshot(
                pr_activity=True, state_mtime=True, log_mtime=True, cpu_delta=True,
                cpu_jiffies=jiffies,
            )
            record_heartbeat(conn, attempt_id, snap)

        assert get_last_cpu_jiffies(conn, attempt_id) == 300

    def test_heartbeat_row_written_to_db(self, conn, running_attempt):
        _, attempt_id = running_attempt
        snap = SignalSnapshot(
            pr_activity=True, state_mtime=True, log_mtime=True, cpu_delta=True,
        )
        record_heartbeat(conn, attempt_id, snap)

        rows = conn.execute(
            "SELECT * FROM heartbeats WHERE attempt_id = ?", (attempt_id,)
        ).fetchall()
        assert len(rows) == 1
        signals = json.loads(rows[0]["signals"])
        assert signals["pr_activity"] is True


# ---------------------------------------------------------------------------
# collect_signals unit tests
# ---------------------------------------------------------------------------


class TestCollectSignals:
    def _call(self, tmp_path, *, pid=None, prev_cpu=None, threshold_s=600, **file_kw):
        """Helper to call collect_signals with controlled file system."""
        monorepo_root = str(tmp_path)
        attempt_dir = str(tmp_path / "attempt")
        os.makedirs(attempt_dir, exist_ok=True)

        # Set up files if requested
        if file_kw.get("state_file_recent"):
            state_path = tmp_path / ".workspace" / "pipeline" / "workspace"
            state_path.mkdir(parents=True, exist_ok=True)
            (state_path / "issue-42.state.json").write_text('{"pr": 0}')

        if file_kw.get("log_file_recent"):
            (tmp_path / "attempt" / "worker.log").write_text("output")

        with patch("orchctl.heartbeat._check_pr_activity", return_value=file_kw.get("pr_activity", False)):
            return collect_signals(
                area="workspace",
                issue_number=42,
                pid=pid,
                attempt_dir=attempt_dir,
                monorepo_root=monorepo_root,
                prev_cpu_jiffies=prev_cpu,
                threshold_s=threshold_s,
            )

    def test_all_signals_absent_no_files(self, tmp_path):
        snap = self._call(tmp_path)
        assert snap.pr_activity is False
        assert snap.state_mtime is False
        assert snap.log_mtime is False
        assert snap.cpu_delta is False
        assert snap.is_stalled()

    def test_state_file_present_recent(self, tmp_path):
        snap = self._call(tmp_path, state_file_recent=True)
        assert snap.state_mtime is True
        # Only 3 signals absent (pr, log, cpu) -> stalled
        assert snap.is_stalled()

    def test_log_file_present_recent(self, tmp_path):
        snap = self._call(tmp_path, log_file_recent=True)
        assert snap.log_mtime is True

    def test_pr_activity_signal(self, tmp_path):
        snap = self._call(tmp_path, pr_activity=True)
        assert snap.pr_activity is True

    def test_cpu_delta_first_sample(self, tmp_path):
        """First CPU sample (no prev) should be treated as active (benefit of doubt)."""
        with patch("orchctl.heartbeat._read_cpu_jiffies", return_value=1000):
            snap = self._call(tmp_path, pid=99999, prev_cpu=None)
        assert snap.cpu_delta is True
        assert snap.cpu_jiffies == 1000

    def test_cpu_delta_changed(self, tmp_path):
        with patch("orchctl.heartbeat._read_cpu_jiffies", return_value=1500):
            snap = self._call(tmp_path, pid=99999, prev_cpu=1000)
        assert snap.cpu_delta is True

    def test_cpu_delta_unchanged(self, tmp_path):
        with patch("orchctl.heartbeat._read_cpu_jiffies", return_value=1000):
            snap = self._call(tmp_path, pid=99999, prev_cpu=1000)
        assert snap.cpu_delta is False

    def test_cpu_delta_no_pid(self, tmp_path):
        snap = self._call(tmp_path, pid=None)
        assert snap.cpu_delta is False
        assert snap.cpu_jiffies is None

    def test_cpu_delta_process_gone(self, tmp_path):
        with patch("orchctl.heartbeat._read_cpu_jiffies", return_value=None):
            snap = self._call(tmp_path, pid=99999, prev_cpu=500)
        assert snap.cpu_delta is False

    def test_one_absent_not_stalled(self, tmp_path):
        """With 3 signals present, absent_count=1 — not a stall."""
        with patch("orchctl.heartbeat._read_cpu_jiffies", return_value=1000):
            snap = self._call(
                tmp_path,
                pid=99999,
                prev_cpu=None,
                pr_activity=True,
                log_file_recent=True,
            )
        # pr_activity=True, log=True, cpu=True (first sample), state=False
        assert snap.absent_count == 1
        assert not snap.is_stalled()

    def test_two_absent_stalled(self, tmp_path):
        """With 2 signals absent, is_stalled() returns True."""
        snap = self._call(tmp_path, pr_activity=True, log_file_recent=True)
        # pr=True, log=True, state=False, cpu=False -> 2 absent
        assert snap.absent_count == 2
        assert snap.is_stalled()


# ---------------------------------------------------------------------------
# check_stall integration
# ---------------------------------------------------------------------------


class TestCheckStall:
    def test_check_stall_records_heartbeat(self, conn, running_attempt, tmp_path):
        _, attempt_id = running_attempt
        with patch("orchctl.heartbeat.collect_signals") as mock_collect:
            mock_collect.return_value = SignalSnapshot(
                pr_activity=False, state_mtime=False, log_mtime=False, cpu_delta=False
            )
            stalled, _ = check_stall(
                conn,
                area="workspace",
                issue_number=42,
                attempt_id=attempt_id,
                pid=None,
                monorepo_root=str(tmp_path),
            )

        assert stalled is True
        rows = conn.execute(
            "SELECT * FROM heartbeats WHERE attempt_id = ?", (attempt_id,)
        ).fetchall()
        assert len(rows) == 1

    def test_check_stall_not_stalled_when_one_absent(self, conn, running_attempt, tmp_path):
        _, attempt_id = running_attempt
        with patch("orchctl.heartbeat.collect_signals") as mock_collect:
            mock_collect.return_value = SignalSnapshot(
                pr_activity=True, state_mtime=True, log_mtime=True, cpu_delta=False
            )
            stalled, snap = check_stall(
                conn,
                area="workspace",
                issue_number=42,
                attempt_id=attempt_id,
                pid=None,
                monorepo_root=str(tmp_path),
            )

        assert stalled is False
        assert snap.absent_count == 1

    def test_check_stall_passes_prev_cpu_to_collect(self, conn, running_attempt, tmp_path):
        """get_last_cpu_jiffies result must be forwarded to collect_signals."""
        _, attempt_id = running_attempt
        # Pre-seed a heartbeat with cpu_jiffies=500
        record_heartbeat(
            conn, attempt_id,
            SignalSnapshot(
                pr_activity=True, state_mtime=True, log_mtime=True, cpu_delta=True,
                cpu_jiffies=500,
            ),
        )

        captured = {}

        def fake_collect(**kwargs):
            captured["prev_cpu_jiffies"] = kwargs.get("prev_cpu_jiffies")
            return SignalSnapshot(
                pr_activity=True, state_mtime=True, log_mtime=True, cpu_delta=True,
                cpu_jiffies=600,
            )

        with patch("orchctl.heartbeat.collect_signals", side_effect=fake_collect):
            check_stall(
                conn,
                area="workspace",
                issue_number=42,
                attempt_id=attempt_id,
                pid=None,
                monorepo_root=str(tmp_path),
            )

        assert captured["prev_cpu_jiffies"] == 500


# ---------------------------------------------------------------------------
# attempt_dir_path
# ---------------------------------------------------------------------------


class TestAttemptDirPath:
    def test_path_convention(self):
        path = attempt_dir_path("/repo", "workspace", 42, "issue-42-aaaa0001")
        expected = "/repo/.workspace/orchestrate/workspace/issues/42/attempts/issue-42-aaaa0001"
        assert path == expected


# ---------------------------------------------------------------------------
# Reconcile heartbeat pass integration
# ---------------------------------------------------------------------------


class TestHeartbeatPassInReconcile:
    """Test the _heartbeat_pass is called by reconcile and handles stall transitions."""

    def _setup_dispatched(self, conn, area="workspace", number=10):
        conn.execute(
            f"INSERT INTO issues (area, number, state) VALUES ('{area}', {number}, 'dispatched')"
        )
        conn.commit()
        issue_id = conn.execute(
            "SELECT id FROM issues WHERE area=? AND number=?", (area, number)
        ).fetchone()["id"]
        attempt_id = f"issue-{number}-test0001"
        conn.execute(
            "INSERT INTO attempts (attempt_id, issue_id, pid, status) VALUES (?, ?, ?, 'running')",
            (attempt_id, issue_id, None),
        )
        conn.commit()
        return issue_id, attempt_id

    def test_stalled_issue_transitions_to_failed_terminal(self, conn, tmp_path):
        from orchctl.commands.reconcile import _heartbeat_pass
        from collections import defaultdict

        issue_id, attempt_id = self._setup_dispatched(conn, number=10)

        issues_by_state = {
            "dispatched": [
                conn.execute(
                    "SELECT id, number FROM issues WHERE id=?", (issue_id,)
                ).fetchone()
            ]
        }

        with patch("orchctl.heartbeat.collect_signals") as mock_collect:
            mock_collect.return_value = SignalSnapshot(
                pr_activity=False, state_mtime=False, log_mtime=False, cpu_delta=False
            )
            with patch.dict(os.environ, {"MONOREPO_ROOT": str(tmp_path)}):
                result = _heartbeat_pass(
                    conn, "workspace", os.getpid(), False, issues_by_state,
                    owns_lease=False,
                )

        assert result is True

        issue_state = conn.execute(
            "SELECT state FROM issues WHERE id=?", (issue_id,)
        ).fetchone()["state"]
        assert issue_state == "failed-terminal"

        attempt_status = conn.execute(
            "SELECT status FROM attempts WHERE attempt_id=?", (attempt_id,)
        ).fetchone()["status"]
        assert attempt_status == "timed-out"

    def test_not_stalled_issue_stays_dispatched(self, conn, tmp_path):
        from orchctl.commands.reconcile import _heartbeat_pass

        issue_id, attempt_id = self._setup_dispatched(conn, number=11)

        issues_by_state = {
            "dispatched": [
                conn.execute(
                    "SELECT id, number FROM issues WHERE id=?", (issue_id,)
                ).fetchone()
            ]
        }

        with patch("orchctl.heartbeat.collect_signals") as mock_collect:
            mock_collect.return_value = SignalSnapshot(
                pr_activity=True, state_mtime=True, log_mtime=True, cpu_delta=False
            )
            with patch.dict(os.environ, {"MONOREPO_ROOT": str(tmp_path)}):
                result = _heartbeat_pass(
                    conn, "workspace", os.getpid(), False, issues_by_state,
                    owns_lease=False,
                )

        assert result is True

        issue_state = conn.execute(
            "SELECT state FROM issues WHERE id=?", (issue_id,)
        ).fetchone()["state"]
        assert issue_state == "dispatched"

    def test_dry_run_skips_recording(self, conn, tmp_path):
        from orchctl.commands.reconcile import _heartbeat_pass

        issue_id, attempt_id = self._setup_dispatched(conn, number=12)

        issues_by_state = {
            "dispatched": [
                conn.execute(
                    "SELECT id, number FROM issues WHERE id=?", (issue_id,)
                ).fetchone()
            ]
        }

        with patch("orchctl.heartbeat.collect_signals") as mock_collect:
            with patch.dict(os.environ, {"MONOREPO_ROOT": str(tmp_path)}):
                result = _heartbeat_pass(
                    conn, "workspace", os.getpid(), True, issues_by_state,
                    owns_lease=False,
                )

        # Dry-run: collect_signals must not be called
        mock_collect.assert_not_called()
        assert result is True

        # No heartbeats recorded
        rows = conn.execute(
            "SELECT * FROM heartbeats WHERE attempt_id=?", (attempt_id,)
        ).fetchall()
        assert len(rows) == 0

    def test_no_dispatched_issues_returns_true(self, conn, tmp_path):
        from orchctl.commands.reconcile import _heartbeat_pass

        result = _heartbeat_pass(
            conn, "workspace", os.getpid(), False, {}, owns_lease=False
        )
        assert result is True
