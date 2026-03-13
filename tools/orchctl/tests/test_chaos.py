"""Chaos / resilience tests for orchctl — 10 fault-injection scenarios.

Scenario index
--------------
1.  Post-dispatch controller crash           — dangling dispatched+running row on restart
2.  Stale terminal (state) file              — state_mtime signal absent
3.  PID reuse by OS                          — expired-but-pid-alive lease persists until TTL
4.  GitHub API timeout during discovery      — non-fatal; reconcile continues
5.  PR open but worker process dead          — ≥2 absent signals → stall detection
6.  Worker alive but log frozen              — 1 absent signal → no stall
7.  Retry budget exhaustion                  — issue escalated to needs-human
8.  Dependency cycle                         — both blocked issues stay blocked across passes
9.  Manual hold added before dispatch        — area pause prevents new dispatches
10. Scheduler overlap (concurrent reconcile) — lease prevents double-dispatch
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from orchctl.commands.reconcile import (
    _dispatch_pass,
    _discovery_pass,
    _heartbeat_pass,
    _mark_complete_pass,
    _observe_config,
    _observe_issues,
    _unblock_pass,
)
from orchctl.db.connection import init_db
from orchctl.db.lease import acquire, has_active_attempt, release
from orchctl.db import get_config_bool, set_config
from orchctl.github import GitHubError
from orchctl.heartbeat import (
    STALL_MIN_ABSENT,
    SignalSnapshot,
    check_stall,
    collect_signals,
    record_heartbeat,
)
from orchctl.models import IssueState
from orchctl.state_machine import apply_issue_transition, apply_attempt_transition


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def conn(tmp_path: Path):
    db_path = tmp_path / "test.db"
    c, _ = init_db(db_path)
    yield c
    c.close()


def _insert_issue(
    conn,
    area: str = "workspace",
    number: int = 1,
    state: str = "pending",
    dependency_type: str = "none",
    retry_count: int = 0,
) -> int:
    cur = conn.execute(
        "INSERT INTO issues (area, number, state, dependency_type, retry_count)"
        " VALUES (?, ?, ?, ?, ?)",
        (area, number, state, dependency_type, retry_count),
    )
    conn.commit()
    return cur.lastrowid


def _insert_running_attempt(conn, issue_id: int, attempt_id: str, pid: int | None = None) -> None:
    conn.execute(
        "INSERT INTO attempts (attempt_id, issue_id, status, pid) VALUES (?, ?, 'running', ?)",
        (attempt_id, issue_id, pid),
    )
    conn.commit()


def _insert_failed_attempt(
    conn,
    issue_id: int,
    attempt_id: str,
    terminal_json: str | None = None,
) -> None:
    conn.execute(
        "INSERT INTO attempts (attempt_id, issue_id, status, terminal_json)"
        " VALUES (?, ?, 'failed', ?)",
        (attempt_id, issue_id, terminal_json),
    )
    conn.commit()


def _issue_state(conn, issue_id: int) -> str:
    return conn.execute(
        "SELECT state FROM issues WHERE id = ?", (issue_id,)
    ).fetchone()["state"]


# ---------------------------------------------------------------------------
# Scenario 1: Post-dispatch controller crash
# ---------------------------------------------------------------------------


class TestPostDispatchCrash:
    """Issue is dispatched + running when controller crashes.
    On the next reconcile pass, mark-complete inspects the attempt.
    A running attempt (no terminal status) is left alone — the reconcile
    is idempotent and does not corrupt state.
    """

    def test_running_attempt_is_not_transitioned(self, conn):
        """mark_complete pass ignores a still-running attempt."""
        issue_id = _insert_issue(conn, state="dispatched")
        _insert_running_attempt(conn, issue_id, "att-crash-1")

        pid = os.getpid()
        acquire(conn, "workspace", pid)
        issues_by_state = _observe_issues(conn, "workspace")
        result = _mark_complete_pass(conn, "workspace", pid, False, issues_by_state)

        assert result is True
        # Issue remains dispatched — crash-recovery is safe
        assert _issue_state(conn, issue_id) == "dispatched"

    def test_repeated_reconcile_passes_are_stable(self, conn):
        """Multiple reconcile passes with an orphaned running attempt are idempotent."""
        issue_id = _insert_issue(conn, state="dispatched")
        _insert_running_attempt(conn, issue_id, "att-crash-2")

        pid = os.getpid()
        acquire(conn, "workspace", pid)
        for _ in range(3):
            issues_by_state = _observe_issues(conn, "workspace")
            _mark_complete_pass(conn, "workspace", pid, False, issues_by_state)

        assert _issue_state(conn, issue_id) == "dispatched"


# ---------------------------------------------------------------------------
# Scenario 2: Stale terminal (state) file
# ---------------------------------------------------------------------------


class TestStaleTerminalFile:
    """A pipeline state file exists but was last modified outside the threshold.
    The state_mtime heartbeat signal should be False for that file.
    """

    def test_state_mtime_absent_for_stale_file(self, tmp_path: Path):
        state_dir = tmp_path / ".workspace" / "pipeline" / "workspace"
        state_dir.mkdir(parents=True)
        state_file = state_dir / "issue-5.state.json"
        state_file.write_text("{}", encoding="utf-8")

        # Back-date the file to well outside the threshold
        stale_time = time.time() - 7200  # 2 hours ago
        os.utime(state_file, (stale_time, stale_time))

        with patch(
            "orchctl.heartbeat._check_pr_activity", return_value=False
        ), patch("orchctl.heartbeat._read_cpu_jiffies", return_value=None):
            snapshot = collect_signals(
                area="workspace",
                issue_number=5,
                pid=None,
                attempt_dir=str(tmp_path / "attempt"),
                monorepo_root=str(tmp_path),
                prev_cpu_jiffies=None,
                threshold_s=600,
            )

        assert snapshot.state_mtime is False

    def test_fresh_state_file_gives_present_signal(self, tmp_path: Path):
        state_dir = tmp_path / ".workspace" / "pipeline" / "workspace"
        state_dir.mkdir(parents=True)
        state_file = state_dir / "issue-5.state.json"
        state_file.write_text("{}", encoding="utf-8")
        # mtime is now — within threshold

        with patch(
            "orchctl.heartbeat._check_pr_activity", return_value=False
        ), patch("orchctl.heartbeat._read_cpu_jiffies", return_value=None):
            snapshot = collect_signals(
                area="workspace",
                issue_number=5,
                pid=None,
                attempt_dir=str(tmp_path / "attempt"),
                monorepo_root=str(tmp_path),
                prev_cpu_jiffies=None,
                threshold_s=600,
            )

        assert snapshot.state_mtime is True


# ---------------------------------------------------------------------------
# Scenario 3: PID reuse by OS
# ---------------------------------------------------------------------------


class TestPidReuse:
    """When the leaseholder crashes and the OS recycles its PID for an unrelated
    process, cleanup_stale cannot distinguish the new process from the original
    leaseholder.  The lease persists until the TTL elapses.  This is the
    documented PID-reuse limitation in db/lease.py.

    The test verifies that a 'dead PID' that appears alive (simulated via mock)
    does NOT get cleaned up, so the lease remains held by the 'recycled' PID.
    """

    def test_pid_alive_lease_not_cleaned_up(self, conn):
        stale_pid = 99999  # likely non-existent; we mock it as 'alive'

        # Insert a lease with an expiry far in the future (to avoid expiry clean-up path)
        future_exp = "2099-01-01 00:00:00"
        conn.execute(
            "INSERT INTO leases (area, holder_pid, acquired_at, heartbeat_at, expires_at)"
            " VALUES (?, ?, datetime('now'), datetime('now'), ?)",
            ("workspace", stale_pid, future_exp),
        )
        conn.commit()

        # Simulate PID reuse: _pid_alive returns True for the recycled PID
        with patch("orchctl.db.lease._pid_alive", return_value=True):
            from orchctl.db.lease import cleanup_stale
            removed = cleanup_stale(conn)
            conn.commit()

        # The lease was NOT removed because the PID appears alive
        assert removed == 0
        row = conn.execute(
            "SELECT holder_pid FROM leases WHERE area = ?", ("workspace",)
        ).fetchone()
        assert row is not None and row["holder_pid"] == stale_pid

    def test_truly_dead_pid_lease_is_cleaned(self, conn):
        """A lease whose holder PID is genuinely dead is removed by cleanup_stale."""
        dead_pid = 2  # PID 2 is kthreadd on Linux and we can't signal it normally,
        # but we just mock _pid_alive to return False for certainty.

        future_exp = "2099-01-01 00:00:00"
        conn.execute(
            "INSERT INTO leases (area, holder_pid, acquired_at, heartbeat_at, expires_at)"
            " VALUES (?, ?, datetime('now'), datetime('now'), ?)",
            ("workspace", dead_pid, future_exp),
        )
        conn.commit()

        with patch("orchctl.db.lease._pid_alive", return_value=False):
            from orchctl.db.lease import cleanup_stale
            removed = cleanup_stale(conn)
            conn.commit()

        assert removed >= 1
        row = conn.execute(
            "SELECT holder_pid FROM leases WHERE area = ?", ("workspace",)
        ).fetchone()
        assert row is None


# ---------------------------------------------------------------------------
# Scenario 4: GitHub API timeout during discovery
# ---------------------------------------------------------------------------


class TestGitHubApiTimeout:
    """Discovery pass raises GitHubError (timeout, rate-limit, network).
    The reconcile should log the error and continue — non-fatal.
    """

    def _full_config(self, enabled: bool = True) -> dict:
        return {
            "discovery_enabled": enabled,
            "scope_include_labels": [],
            "scope_exclude_labels": [],
            "scope_milestone": "",
            "scope_allow_unassigned": True,
        }

    def test_github_timeout_is_non_fatal(self, conn):
        pid = os.getpid()
        acquire(conn, "workspace", pid)

        def fail_list(*_args, **_kwargs):
            raise GitHubError("connection timed out")

        result = _discovery_pass(
            conn, "workspace", pid, False, self._full_config(), gh_list_fn=fail_list
        )

        # Must return True (non-fatal) rather than propagating the error
        assert result is True

    def test_github_timeout_leaves_existing_issues_intact(self, conn):
        issue_id = _insert_issue(conn, number=10, state="pending")
        pid = os.getpid()
        acquire(conn, "workspace", pid)

        def fail_list(*_args, **_kwargs):
            raise GitHubError("read timed out after 30s")

        _discovery_pass(
            conn, "workspace", pid, False, self._full_config(), gh_list_fn=fail_list
        )

        # Existing issue state is untouched
        assert _issue_state(conn, issue_id) == "pending"

    def test_discovery_disabled_skips_gh_call(self, conn):
        """When discovery_enabled=false the GitHub call is never made."""
        called = []

        def should_not_be_called(*_a, **_kw):
            called.append(True)
            return []

        result = _discovery_pass(
            conn, "workspace", os.getpid(), False,
            self._full_config(enabled=False),
            gh_list_fn=should_not_be_called,
        )

        assert result is True
        assert called == []


# ---------------------------------------------------------------------------
# Scenario 5: PR open but worker process dead
# ---------------------------------------------------------------------------


class TestPrOpenWorkerDead:
    """Worker process is dead (no PID or PID gone).  Log file is also stale.
    Two signals absent → stall detected on the second heartbeat cycle.
    """

    def test_dead_worker_with_stale_log_triggers_stall(self, conn, tmp_path: Path):
        issue_id = _insert_issue(conn, state="dispatched")
        attempt_id = "att-dead-1"
        _insert_running_attempt(conn, issue_id, attempt_id, pid=None)

        # Write a stale log to the path check_stall derives internally:
        # {monorepo_root}/.workspace/orchestrate/{area}/issues/{N}/attempts/{id}/worker.log
        attempt_dir = (
            tmp_path / ".workspace" / "orchestrate" / "workspace"
            / "issues" / "1" / "attempts" / attempt_id
        )
        attempt_dir.mkdir(parents=True)
        log_file = attempt_dir / "worker.log"
        log_file.write_text("some output", encoding="utf-8")
        stale_time = time.time() - 7200
        os.utime(log_file, (stale_time, stale_time))

        # First call — first-cycle protection means stall=False
        with patch("orchctl.heartbeat._check_pr_activity", return_value=True), \
             patch("orchctl.heartbeat._read_cpu_jiffies", return_value=None):
            stalled, snap1 = check_stall(
                conn,
                area="workspace",
                issue_number=1,
                attempt_id=attempt_id,
                pid=None,
                monorepo_root=str(tmp_path),
                threshold_s=600,
            )
        assert stalled is False  # first-cycle protection

        # Second call — stall should be detected (log stale + no PID = 2 absent)
        with patch("orchctl.heartbeat._check_pr_activity", return_value=True), \
             patch("orchctl.heartbeat._read_cpu_jiffies", return_value=None):
            stalled, snap2 = check_stall(
                conn,
                area="workspace",
                issue_number=1,
                attempt_id=attempt_id,
                pid=None,
                monorepo_root=str(tmp_path),
                threshold_s=600,
            )
        # cpu_delta absent (no PID) + log_mtime absent = 2 absent signals
        assert snap2.cpu_delta is False
        assert snap2.log_mtime is False
        assert snap2.absent_count >= STALL_MIN_ABSENT
        assert stalled is True

    def test_heartbeat_pass_transitions_stalled_issue(self, conn, tmp_path: Path):
        """_heartbeat_pass marks attempt timed-out and issue failed-terminal on stall."""
        issue_id = _insert_issue(conn, state="dispatched")
        attempt_id = "att-dead-2"
        _insert_running_attempt(conn, issue_id, attempt_id, pid=None)

        pid = os.getpid()
        acquire(conn, "workspace", pid)

        # Pre-insert a heartbeat so the second call isn't first-cycle
        record_heartbeat(
            conn, attempt_id,
            SignalSnapshot(pr_activity=True, state_mtime=False, log_mtime=False, cpu_delta=False),
        )

        issues_by_state = {"dispatched": conn.execute(
            "SELECT id, number FROM issues WHERE state='dispatched'"
        ).fetchall()}

        with patch("orchctl.heartbeat.check_stall") as mock_stall:
            mock_stall.return_value = (
                True,
                SignalSnapshot(
                    pr_activity=True, state_mtime=False, log_mtime=False, cpu_delta=False
                ),
            )
            _heartbeat_pass(
                conn, "workspace", pid, False, issues_by_state,
                owns_lease=True,
            )

        assert _issue_state(conn, issue_id) == "failed-terminal"
        row = conn.execute(
            "SELECT status FROM attempts WHERE attempt_id = ?", (attempt_id,)
        ).fetchone()
        assert row["status"] == "timed-out"


# ---------------------------------------------------------------------------
# Scenario 6: Worker alive but log frozen
# ---------------------------------------------------------------------------


class TestWorkerAliveLogFrozen:
    """Worker is alive (CPU jiffies are changing) but the log file is stale.
    Only 1 signal is absent → no stall declared.
    """

    def test_single_absent_signal_is_not_stall(self):
        snap = SignalSnapshot(
            pr_activity=True,
            state_mtime=True,
            log_mtime=False,  # log frozen
            cpu_delta=True,   # worker alive
        )
        assert snap.absent_count == 1
        assert snap.is_stalled() is False

    def test_two_absent_signals_is_stall(self):
        snap = SignalSnapshot(
            pr_activity=True,
            state_mtime=False,
            log_mtime=False,
            cpu_delta=True,
        )
        assert snap.absent_count == 2
        assert snap.is_stalled() is True

    def test_stall_min_absent_is_two(self):
        """Constant must be 2 — changing it without updating tests is intentional."""
        assert STALL_MIN_ABSENT == 2

    def test_cpu_delta_present_with_one_other_absent_no_stall(self, conn, tmp_path: Path):
        """End-to-end: worker alive, log stale → second heartbeat cycle does not stall."""
        issue_id = _insert_issue(conn, state="dispatched")
        attempt_id = "att-alive-1"
        _insert_running_attempt(conn, issue_id, attempt_id, pid=os.getpid())

        # Write a stale log to the path check_stall derives internally
        attempt_dir = (
            tmp_path / ".workspace" / "orchestrate" / "workspace"
            / "issues" / "1" / "attempts" / attempt_id
        )
        attempt_dir.mkdir(parents=True)
        log_file = attempt_dir / "worker.log"
        log_file.write_text("output", encoding="utf-8")
        # Back-date log (stale)
        os.utime(log_file, (time.time() - 7200, time.time() - 7200))

        # Create a fresh state file so state_mtime=True (only log is stale)
        state_dir = tmp_path / ".workspace" / "pipeline" / "workspace"
        state_dir.mkdir(parents=True)
        (state_dir / "issue-1.state.json").write_text("{}", encoding="utf-8")

        # First heartbeat (first-cycle protection)
        with patch("orchctl.heartbeat._check_pr_activity", return_value=True), \
             patch("orchctl.heartbeat._read_cpu_jiffies", return_value=1000):
            check_stall(
                conn, area="workspace", issue_number=1,
                attempt_id=attempt_id, pid=os.getpid(),
                monorepo_root=str(tmp_path), threshold_s=600,
            )

        # Second heartbeat — CPU changed, so cpu_delta=True; log stale → log_mtime=False
        with patch("orchctl.heartbeat._check_pr_activity", return_value=True), \
             patch("orchctl.heartbeat._read_cpu_jiffies", return_value=2000):
            stalled, snap = check_stall(
                conn, area="workspace", issue_number=1,
                attempt_id=attempt_id, pid=os.getpid(),
                monorepo_root=str(tmp_path), threshold_s=600,
            )

        assert snap.cpu_delta is True
        assert snap.log_mtime is False
        assert snap.absent_count == 1
        assert stalled is False


# ---------------------------------------------------------------------------
# Scenario 7: Retry budget exhaustion
# ---------------------------------------------------------------------------


class TestRetryBudgetExhaustion:
    """When retry_count >= budget, a failed attempt escalates to needs-human."""

    def _run_mark_complete(self, conn, area: str = "workspace") -> bool:
        pid = os.getpid()
        acquire(conn, area, pid)
        issues_by_state = _observe_issues(conn, area)
        return _mark_complete_pass(conn, area, pid, False, issues_by_state)

    def test_first_failure_within_budget_retries(self, conn):
        # Use infra_crash class (triggered by rc=137 in reason) → NextAction.RETRY
        set_config(conn, "retry_budget_by_class", '{"infra_crash": 2}')
        issue_id = _insert_issue(conn, state="dispatched", retry_count=0)
        _insert_failed_attempt(
            conn, issue_id, "att-budget-1",
            terminal_json='{"reason": "process killed rc=137"}',
        )

        self._run_mark_complete(conn)

        assert _issue_state(conn, issue_id) == "pending"
        row = conn.execute("SELECT retry_count FROM issues WHERE id = ?", (issue_id,)).fetchone()
        assert row["retry_count"] == 1

    def test_failure_at_budget_limit_escalates_to_needs_human(self, conn):
        # retry_count == budget (2) means exhausted
        set_config(conn, "retry_budget_by_class", '{"infra_crash": 2}')
        issue_id = _insert_issue(conn, state="dispatched", retry_count=2)
        _insert_failed_attempt(
            conn, issue_id, "att-budget-2",
            terminal_json='{"reason": "process killed rc=137"}',
        )

        self._run_mark_complete(conn)

        assert _issue_state(conn, issue_id) == "needs-human"

    def test_zero_budget_always_escalates(self, conn):
        set_config(conn, "retry_budget_by_class", '{"infra_crash": 0}')
        issue_id = _insert_issue(conn, state="dispatched", retry_count=0)
        _insert_failed_attempt(
            conn, issue_id, "att-budget-3",
            terminal_json='{"reason": "process killed rc=137"}',
        )

        self._run_mark_complete(conn)

        assert _issue_state(conn, issue_id) == "needs-human"

    def test_timed_out_attempt_always_retries_within_budget(self, conn):
        """timed-out → FailureClass.TIMEOUT → NextAction.RETRY."""
        set_config(conn, "retry_budget_by_class", '{"timeout": 3}')
        issue_id = _insert_issue(conn, state="dispatched", retry_count=0)
        conn.execute(
            "INSERT INTO attempts (attempt_id, issue_id, status)"
            " VALUES ('att-timeout-1', ?, 'timed-out')",
            (issue_id,),
        )
        conn.commit()

        self._run_mark_complete(conn)

        assert _issue_state(conn, issue_id) == "pending"


# ---------------------------------------------------------------------------
# Scenario 8: Dependency cycle
# ---------------------------------------------------------------------------


class TestDependencyCycle:
    """Issue A is blocked waiting for B; B is blocked waiting for A.
    Both have dependency_type='hard'.  Neither should get unblocked across
    multiple reconcile passes (the unblock pass defers hard/soft deps).
    """

    def test_cycle_both_stay_blocked_after_unblock_pass(self, conn):
        id_a = _insert_issue(conn, number=101, state="blocked", dependency_type="hard")
        id_b = _insert_issue(conn, number=102, state="blocked", dependency_type="hard")

        pid = os.getpid()
        acquire(conn, "workspace", pid)

        for _ in range(3):
            issues_by_state = _observe_issues(conn, "workspace")
            _unblock_pass(conn, "workspace", pid, False, issues_by_state)

        assert _issue_state(conn, id_a) == "blocked"
        assert _issue_state(conn, id_b) == "blocked"

    def test_no_dep_issue_is_unblocked(self, conn):
        """Issue with dependency_type='none' is unblocked even if others are stuck."""
        id_cycle_a = _insert_issue(conn, number=201, state="blocked", dependency_type="hard")
        id_cycle_b = _insert_issue(conn, number=202, state="blocked", dependency_type="hard")
        id_free = _insert_issue(conn, number=203, state="blocked", dependency_type="none")

        pid = os.getpid()
        acquire(conn, "workspace", pid)

        issues_by_state = _observe_issues(conn, "workspace")
        _unblock_pass(conn, "workspace", pid, False, issues_by_state)

        # The two cyclic issues stay blocked
        assert _issue_state(conn, id_cycle_a) == "blocked"
        assert _issue_state(conn, id_cycle_b) == "blocked"
        # The dependency-free issue is unblocked
        assert _issue_state(conn, id_free) == "pending"


# ---------------------------------------------------------------------------
# Scenario 9: Manual hold added before dispatch
# ---------------------------------------------------------------------------


class TestManualHoldBeforeDispatch:
    """Area-level pause blocks all new dispatches for that area.
    Existing dispatched workers are not affected.
    """

    def _run_full_pass(
        self,
        conn,
        area: str = "workspace",
        dispatch_fn=None,
    ) -> None:
        from orchctl.commands.reconcile import _run_pass

        pid = os.getpid()
        owns_lease = acquire(conn, area, pid)
        try:
            _run_pass(
                conn,
                area=area,
                pid=pid,
                dry_run=False,
                dispatch_fn=dispatch_fn,
                owns_lease=owns_lease,
                gh_list_fn=lambda *a, **kw: [],  # skip discovery
            )
        finally:
            release(conn, area, pid)

    def test_paused_area_dispatches_nothing(self, conn):
        set_config(conn, "workspace.paused", "true")
        id1 = _insert_issue(conn, number=1, state="pending")
        id2 = _insert_issue(conn, number=2, state="pending")

        dispatched = []
        self._run_full_pass(conn, dispatch_fn=lambda *a: dispatched.append(a[2]))

        assert dispatched == []
        assert _issue_state(conn, id1) == "pending"
        assert _issue_state(conn, id2) == "pending"

    def test_unpaused_area_dispatches_normally(self, conn):
        set_config(conn, "workspace.paused", "false")
        id1 = _insert_issue(conn, number=3, state="pending")

        dispatched = []
        self._run_full_pass(conn, dispatch_fn=lambda *a: dispatched.append(a[2]))

        assert 3 in dispatched
        assert _issue_state(conn, id1) == "dispatched"

    def test_already_dispatched_issue_not_cancelled_on_pause(self, conn):
        """Pause only prevents new dispatches; existing dispatched issues are untouched."""
        set_config(conn, "workspace.paused", "true")
        issue_id = _insert_issue(conn, state="dispatched")

        self._run_full_pass(conn)

        assert _issue_state(conn, issue_id) == "dispatched"

    def test_drain_mode_also_prevents_dispatch(self, conn):
        """Global drain_mode blocks dispatch regardless of per-area pause."""
        set_config(conn, "drain_mode", "true")
        set_config(conn, "workspace.paused", "false")
        issue_id = _insert_issue(conn, number=4, state="pending")

        dispatched = []
        self._run_full_pass(conn, dispatch_fn=lambda *a: dispatched.append(a[2]))

        assert dispatched == []
        assert _issue_state(conn, issue_id) == "pending"


# ---------------------------------------------------------------------------
# Scenario 10: Scheduler overlap (concurrent reconcile)
# ---------------------------------------------------------------------------


class TestSchedulerOverlap:
    """Two reconcilers running simultaneously for the same area.

    With scheduler_overlap=False (default): the second reconciler must exit
    immediately after failing to acquire the lease.

    With scheduler_overlap=True: both run, but atomic _record_dispatch
    prevents double-dispatch when maxOpenPR is reached.
    """

    def test_second_reconciler_skips_when_overlap_disabled(self, tmp_path: Path):
        """Second reconciler exits early when scheduler_overlap=false and lease is held.

        The early-exit is enforced by the reconcile *command*, not by _dispatch_pass.
        This test uses the CLI runner to verify that the command emits the expected
        message and performs no dispatches when another process holds the lease.
        """
        from click.testing import CliRunner
        from orchctl.cli import cli

        db_path = str(tmp_path / "overlap.db")
        runner = CliRunner()
        # Init DB
        runner.invoke(cli, ["--db", db_path, "init"])

        # Insert pending issues
        from orchctl.db.connection import get_db
        db = get_db(db_path)
        db.execute("INSERT INTO issues (area, number, state) VALUES ('workspace', 1, 'pending')")
        db.execute("INSERT INTO issues (area, number, state) VALUES ('workspace', 2, 'pending')")
        db.execute(
            "UPDATE config SET value = 'false' WHERE key = 'scheduler_overlap'"
        )
        # Pre-acquire the lease as a foreign PID.  Mock _pid_alive so cleanup_stale
        # treats it as alive (same pattern as TestPidReuse), making the test portable
        # across Linux, macOS, and container environments.
        foreign_pid = 99999
        future_exp = "2099-01-01 00:00:00"
        db.execute(
            "INSERT INTO leases (area, holder_pid, acquired_at, heartbeat_at, expires_at)"
            " VALUES ('workspace', ?, datetime('now'), datetime('now'), ?)",
            (foreign_pid, future_exp),
        )
        db.commit()
        db.close()

        with patch("orchctl.db.lease._pid_alive", return_value=True):
            result = runner.invoke(cli, ["--db", db_path, "reconcile", "--area", "workspace"])

        assert result.exit_code == 0
        assert "lease held by another process" in result.output

        # No issues should have been dispatched
        db2 = get_db(db_path)
        dispatched_count = db2.execute(
            "SELECT COUNT(*) FROM issues WHERE state = 'dispatched'"
        ).fetchone()[0]
        db2.close()
        assert dispatched_count == 0

    def test_atomic_record_dispatch_prevents_exceeding_max_open_pr(self, conn):
        """maxOpenPR is enforced atomically; a second concurrent dispatch cannot exceed it."""
        set_config(conn, "max_open_pr", "1")

        id1 = _insert_issue(conn, number=10, state="pending")
        id2 = _insert_issue(conn, number=11, state="pending")

        pid = os.getpid()
        acquire(conn, "workspace", pid)
        config = _observe_config(conn, "workspace")
        issues_by_state = _observe_issues(conn, "workspace")

        dispatched: list[int] = []
        _dispatch_pass(
            conn, "workspace", pid, False, issues_by_state, config,
            dispatch_fn=lambda *a: dispatched.append(a[2]),
        )

        # With maxOpenPR=1, only one issue should be dispatched
        assert len(dispatched) == 1
        total_dispatched = conn.execute(
            "SELECT COUNT(*) FROM issues WHERE state = 'dispatched'"
        ).fetchone()[0]
        assert total_dispatched == 1

    def test_scheduler_overlap_true_second_reconciler_runs_but_no_double_dispatch(self, conn):
        """With scheduler_overlap=True both reconcilers may run the dispatch pass.
        Atomic _record_dispatch prevents exceeding maxOpenPR.
        """
        set_config(conn, "scheduler_overlap", "true")
        set_config(conn, "max_open_pr", "1")

        _insert_issue(conn, number=20, state="pending")
        _insert_issue(conn, number=21, state="pending")

        pid = os.getpid()
        acquire(conn, "workspace", pid)
        config = _observe_config(conn, "workspace")

        # Simulate two reconcilers running the dispatch pass on the same state snapshot
        dispatched_first: list[int] = []
        dispatched_second: list[int] = []

        issues_by_state_1 = _observe_issues(conn, "workspace")
        _dispatch_pass(
            conn, "workspace", pid, False, issues_by_state_1, config,
            dispatch_fn=lambda *a: dispatched_first.append(a[2]),
        )

        # Same reconciler re-runs dispatch pass with a fresh state snapshot.
        # The atomic _record_dispatch guard prevents issue #21 from being dispatched
        # because maxOpenPR=1 is already reached by the first pass.
        issues_by_state_2 = _observe_issues(conn, "workspace")
        _dispatch_pass(
            conn, "workspace", pid, False, issues_by_state_2, config,
            dispatch_fn=lambda *a: dispatched_second.append(a[2]),
        )

        total_dispatched = conn.execute(
            "SELECT COUNT(*) FROM issues WHERE state = 'dispatched'"
        ).fetchone()[0]
        # Exactly 1 dispatched — second pass stopped by the maxOpenPR atomic guard
        assert total_dispatched == 1
        assert dispatched_second == []
