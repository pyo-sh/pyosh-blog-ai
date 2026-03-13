"""Tests for orchctl state machine: transitions, dependency resolution,
reconcile idempotency, duplicate dispatch prevention, and lease conflicts."""

import sqlite3
from pathlib import Path

import pytest

from orchctl.db.connection import init_db
from orchctl.models import AttemptStatus, DependencyType, IssueState
from orchctl.state_machine import (
    InvalidTransitionError,
    StaleStateError,
    apply_attempt_transition,
    apply_issue_transition,
    can_dispatch,
    release_lease,
    resolve_blocked_issue,
    transition_attempt,
    transition_issue,
    try_acquire_lease,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def conn(tmp_path: Path):
    db_path = tmp_path / "test.db"
    conn, _ = init_db(db_path)
    yield conn
    conn.close()


def _insert_issue(
    conn: sqlite3.Connection,
    area: str = "client",
    number: int = 1,
    state: str = "pending",
    dependency_type: str = "none",
) -> int:
    cur = conn.execute(
        "INSERT INTO issues (area, number, state, dependency_type) VALUES (?, ?, ?, ?)",
        (area, number, state, dependency_type),
    )
    conn.commit()
    return cur.lastrowid


def _insert_attempt(
    conn: sqlite3.Connection,
    attempt_id: str,
    issue_id: int,
    status: str = "created",
) -> None:
    conn.execute(
        "INSERT INTO attempts (attempt_id, issue_id, status) VALUES (?, ?, ?)",
        (attempt_id, issue_id, status),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# transition_issue — pure function tests
# ---------------------------------------------------------------------------


class TestTransitionIssuePure:
    def test_pending_to_dispatched(self):
        assert transition_issue("pending", "dispatched") == "dispatched"

    def test_pending_to_blocked(self):
        assert transition_issue("pending", "blocked") == "blocked"

    def test_pending_to_cancelled(self):
        assert transition_issue("pending", "cancelled") == "cancelled"

    def test_dispatched_to_completed(self):
        assert transition_issue("dispatched", "completed") == "completed"

    def test_dispatched_to_failed_terminal(self):
        assert transition_issue("dispatched", "failed-terminal") == "failed-terminal"

    def test_dispatched_to_needs_human(self):
        assert transition_issue("dispatched", "needs-human") == "needs-human"

    def test_dispatched_to_blocked_external(self):
        assert transition_issue("dispatched", "blocked-external") == "blocked-external"

    def test_dispatched_to_cancelled(self):
        assert transition_issue("dispatched", "cancelled") == "cancelled"

    def test_blocked_to_pending(self):
        assert transition_issue("blocked", "pending") == "pending"

    def test_blocked_to_blocked_failed_dep(self):
        assert transition_issue("blocked", "blocked-failed-dependency") == "blocked-failed-dependency"

    def test_blocked_to_cancelled(self):
        assert transition_issue("blocked", "cancelled") == "cancelled"

    def test_blocked_external_to_pending(self):
        assert transition_issue("blocked-external", "pending") == "pending"

    def test_blocked_external_to_cancelled(self):
        assert transition_issue("blocked-external", "cancelled") == "cancelled"

    # Invalid transitions
    def test_pending_cannot_go_to_completed(self):
        with pytest.raises(InvalidTransitionError):
            transition_issue("pending", "completed")

    def test_dispatched_can_retry_to_pending(self):
        # auto-retry: dispatched → pending is valid (failure within budget)
        assert transition_issue("dispatched", "pending") == "pending"

    def test_dispatched_cannot_go_to_blocked_failed_dep(self):
        with pytest.raises(InvalidTransitionError):
            transition_issue("dispatched", "blocked-failed-dependency")

    def test_dispatched_cannot_go_to_blocked(self):
        with pytest.raises(InvalidTransitionError):
            transition_issue("dispatched", "blocked")

    # completed / failed-terminal / cancelled now allow re-open to pending
    def test_completed_can_reopen_to_pending(self):
        assert transition_issue("completed", "pending") == "pending"

    def test_failed_terminal_can_reopen_to_pending(self):
        assert transition_issue("failed-terminal", "pending") == "pending"

    def test_cancelled_can_reopen_to_pending(self):
        assert transition_issue("cancelled", "pending") == "pending"

    def test_completed_cannot_go_to_dispatched(self):
        with pytest.raises(InvalidTransitionError):
            transition_issue("completed", "dispatched")

    def test_failed_terminal_cannot_go_to_dispatched(self):
        with pytest.raises(InvalidTransitionError):
            transition_issue("failed-terminal", "dispatched")

    def test_needs_human_can_requeue_to_pending(self):
        """Operator requeue: needs-human -> pending is allowed."""
        assert transition_issue("needs-human", "pending") == "pending"

    def test_needs_human_cannot_go_to_dispatched(self):
        with pytest.raises(InvalidTransitionError):
            transition_issue("needs-human", "dispatched")

    def test_blocked_failed_dep_can_requeue_to_pending(self):
        """Operator requeue: blocked-failed-dependency -> pending is allowed."""
        assert transition_issue("blocked-failed-dependency", "pending") == "pending"

    def test_blocked_failed_dep_cannot_go_to_dispatched(self):
        with pytest.raises(InvalidTransitionError):
            transition_issue("blocked-failed-dependency", "dispatched")

    def test_cancelled_can_requeue_to_pending(self):
        """Operator requeue: cancelled -> pending is allowed."""
        assert transition_issue("cancelled", "pending") == "pending"

    def test_cancelled_cannot_go_to_dispatched(self):
        with pytest.raises(InvalidTransitionError):
            transition_issue("cancelled", "dispatched")

    def test_unknown_state_raises(self):
        with pytest.raises(InvalidTransitionError):
            transition_issue("not-a-state", "pending")

    def test_unknown_target_raises(self):
        with pytest.raises(InvalidTransitionError):
            transition_issue("pending", "not-a-state")

    def test_error_message_contains_states(self):
        with pytest.raises(InvalidTransitionError) as exc_info:
            transition_issue("completed", "dispatched")
        msg = str(exc_info.value)
        assert "completed" in msg
        assert "dispatched" in msg


# ---------------------------------------------------------------------------
# transition_attempt — pure function tests
# ---------------------------------------------------------------------------


class TestTransitionAttemptPure:
    def test_created_to_running(self):
        assert transition_attempt("created", "running") == "running"

    def test_running_to_completed(self):
        assert transition_attempt("running", "completed") == "completed"

    def test_running_to_failed(self):
        assert transition_attempt("running", "failed") == "failed"

    def test_running_to_timed_out(self):
        assert transition_attempt("running", "timed-out") == "timed-out"

    # Invalid transitions
    def test_created_cannot_skip_to_completed(self):
        with pytest.raises(InvalidTransitionError):
            transition_attempt("created", "completed")

    def test_completed_is_terminal(self):
        with pytest.raises(InvalidTransitionError):
            transition_attempt("completed", "running")

    def test_failed_is_terminal(self):
        with pytest.raises(InvalidTransitionError):
            transition_attempt("failed", "running")

    def test_timed_out_is_terminal(self):
        with pytest.raises(InvalidTransitionError):
            transition_attempt("timed-out", "running")

    def test_unknown_status_raises(self):
        with pytest.raises(InvalidTransitionError):
            transition_attempt("ghost", "running")

    def test_error_message_labels_entity(self):
        with pytest.raises(InvalidTransitionError) as exc_info:
            transition_attempt("completed", "running")
        assert "attempt" in str(exc_info.value)


# ---------------------------------------------------------------------------
# resolve_blocked_issue — dependency resolution logic
# ---------------------------------------------------------------------------


class TestResolveBlockedIssue:
    def test_no_deps_returns_pending(self):
        result = resolve_blocked_issue([], DependencyType.SOFT.value)
        assert result == IssueState.PENDING.value

    def test_all_completed_soft_returns_pending(self):
        deps = ["completed", "completed"]
        result = resolve_blocked_issue(deps, DependencyType.SOFT.value)
        assert result == IssueState.PENDING.value

    def test_all_completed_hard_returns_pending(self):
        deps = ["completed", "completed"]
        result = resolve_blocked_issue(deps, DependencyType.HARD.value)
        assert result == IssueState.PENDING.value

    def test_failed_dep_soft_returns_pending(self):
        """Soft dependency: failure still allows issue to proceed."""
        deps = ["completed", "failed-terminal"]
        result = resolve_blocked_issue(deps, DependencyType.SOFT.value)
        assert result == IssueState.PENDING.value

    def test_failed_dep_hard_returns_blocked_failed_dep(self):
        """Hard dependency: failure blocks the issue permanently."""
        deps = ["completed", "failed-terminal"]
        result = resolve_blocked_issue(deps, DependencyType.HARD.value)
        assert result == IssueState.BLOCKED_FAILED_DEP.value

    def test_cancelled_dep_hard_returns_blocked_failed_dep(self):
        deps = ["cancelled"]
        result = resolve_blocked_issue(deps, DependencyType.HARD.value)
        assert result == IssueState.BLOCKED_FAILED_DEP.value

    def test_needs_human_dep_hard_returns_blocked_failed_dep(self):
        """needs-human is a non-success terminal state; hard dep should fail."""
        deps = ["needs-human"]
        result = resolve_blocked_issue(deps, DependencyType.HARD.value)
        assert result == IssueState.BLOCKED_FAILED_DEP.value

    def test_needs_human_dep_soft_returns_pending(self):
        """Soft dep: even needs-human terminal state allows dependent to proceed."""
        deps = ["needs-human"]
        result = resolve_blocked_issue(deps, DependencyType.SOFT.value)
        assert result == IssueState.PENDING.value

    def test_blocked_failed_dep_hard_returns_blocked_failed_dep(self):
        """blocked-failed-dependency is non-success; hard dep should fail."""
        deps = ["blocked-failed-dependency"]
        result = resolve_blocked_issue(deps, DependencyType.HARD.value)
        assert result == IssueState.BLOCKED_FAILED_DEP.value

    def test_non_terminal_dep_returns_blocked(self):
        """If deps are still running, issue stays blocked."""
        deps = ["completed", "dispatched"]
        result = resolve_blocked_issue(deps, DependencyType.HARD.value)
        assert result == IssueState.BLOCKED.value

    def test_cancelled_dep_soft_returns_pending(self):
        """Soft dep: cancelled blocker still allows dependent to proceed."""
        deps = ["cancelled"]
        result = resolve_blocked_issue(deps, DependencyType.SOFT.value)
        assert result == IssueState.PENDING.value

    def test_pending_dep_returns_blocked(self):
        deps = ["pending"]
        result = resolve_blocked_issue(deps, DependencyType.SOFT.value)
        assert result == IssueState.BLOCKED.value


# ---------------------------------------------------------------------------
# apply_issue_transition — DB-backed transition
# ---------------------------------------------------------------------------


class TestApplyIssueTransition:
    def test_valid_transition_persisted(self, conn):
        issue_id = _insert_issue(conn, state="pending")
        new_state = apply_issue_transition(conn, issue_id, "dispatched")
        assert new_state == "dispatched"
        row = conn.execute("SELECT state FROM issues WHERE id = ?", (issue_id,)).fetchone()
        assert row["state"] == "dispatched"

    def test_invalid_transition_raises_and_does_not_mutate(self, conn):
        issue_id = _insert_issue(conn, state="completed")
        with pytest.raises(InvalidTransitionError):
            apply_issue_transition(conn, issue_id, "dispatched")
        row = conn.execute("SELECT state FROM issues WHERE id = ?", (issue_id,)).fetchone()
        assert row["state"] == "completed"

    def test_missing_issue_raises_value_error(self, conn):
        with pytest.raises(ValueError, match="not found"):
            apply_issue_transition(conn, 9999, "dispatched")


# ---------------------------------------------------------------------------
# apply_attempt_transition — DB-backed transition
# ---------------------------------------------------------------------------


class TestApplyAttemptTransition:
    def test_valid_transition_persisted(self, conn):
        issue_id = _insert_issue(conn)
        _insert_attempt(conn, "a-1", issue_id, status="created")
        new_status = apply_attempt_transition(conn, "a-1", "running")
        assert new_status == "running"
        row = conn.execute(
            "SELECT status FROM attempts WHERE attempt_id = ?", ("a-1",)
        ).fetchone()
        assert row["status"] == "running"

    def test_invalid_transition_raises_and_does_not_mutate(self, conn):
        issue_id = _insert_issue(conn)
        _insert_attempt(conn, "a-2", issue_id, status="completed")
        with pytest.raises(InvalidTransitionError):
            apply_attempt_transition(conn, "a-2", "running")
        row = conn.execute(
            "SELECT status FROM attempts WHERE attempt_id = ?", ("a-2",)
        ).fetchone()
        assert row["status"] == "completed"

    def test_missing_attempt_raises_value_error(self, conn):
        with pytest.raises(ValueError, match="not found"):
            apply_attempt_transition(conn, "ghost-id", "running")


# ---------------------------------------------------------------------------
# StaleStateError — concurrent modification detection
# ---------------------------------------------------------------------------


class TestStaleStateError:
    def test_is_distinct_from_invalid_transition_error(self):
        """StaleStateError must not be caught by InvalidTransitionError handlers."""
        err = StaleStateError("concurrent modification")
        assert not isinstance(err, InvalidTransitionError)

    def test_message_preserved(self):
        msg = "Issue id=1 state changed concurrently (read 'pending', attempted 'dispatched')"
        err = StaleStateError(msg)
        assert msg in str(err)

    def test_concurrent_write_triggers_zero_rowcount(self, tmp_path: Path):
        """Demonstrate the DB scenario that triggers StaleStateError.

        apply_issue_transition raises StaleStateError when the UPDATE predicate
        (WHERE id=? AND state=?) matches 0 rows because a concurrent writer
        already changed the state between SELECT and UPDATE.
        """
        from orchctl.db.connection import init_db as _init
        from orchctl.state_machine import transition_issue

        db_path = tmp_path / "stale.db"
        conn, _ = _init(db_path)

        cur = conn.execute(
            "INSERT INTO issues (area, number, state, dependency_type) VALUES (?, ?, ?, ?)",
            ("client", 99, "pending", "none"),
        )
        conn.commit()
        issue_id = cur.lastrowid

        # Simulate concurrent write: another process dispatches the issue
        conn.execute(
            "UPDATE issues SET state = 'dispatched' WHERE id = ?", (issue_id,)
        )
        conn.commit()

        # Now simulate what apply_issue_transition would do if it had read "pending"
        # before the concurrent write — validates ok, but UPDATE returns 0 rows.
        old_state = "pending"
        validated = transition_issue(old_state, "dispatched")  # logically valid
        update = conn.execute(
            "UPDATE issues SET state = ? WHERE id = ? AND state = ?",
            (validated, issue_id, old_state),
        )
        conn.close()
        # rowcount==0 is exactly the condition that raises StaleStateError
        assert update.rowcount == 0


# ---------------------------------------------------------------------------
# can_dispatch — dispatch eligibility
# ---------------------------------------------------------------------------


class TestCanDispatch:
    def test_pending_issue_can_be_dispatched(self, conn):
        issue_id = _insert_issue(conn, state="pending")
        assert can_dispatch(conn, issue_id) is True

    def test_dispatched_issue_cannot_be_dispatched(self, conn):
        issue_id = _insert_issue(conn, state="dispatched")
        assert can_dispatch(conn, issue_id) is False

    def test_completed_issue_cannot_be_dispatched(self, conn):
        issue_id = _insert_issue(conn, state="completed")
        assert can_dispatch(conn, issue_id) is False

    def test_blocked_issue_cannot_be_dispatched(self, conn):
        issue_id = _insert_issue(conn, state="blocked")
        assert can_dispatch(conn, issue_id) is False

    def test_nonexistent_issue_cannot_be_dispatched(self, conn):
        assert can_dispatch(conn, 9999) is False


# ---------------------------------------------------------------------------
# Duplicate dispatch prevention
# ---------------------------------------------------------------------------


class TestDuplicateDispatch:
    def test_dispatch_once_succeeds(self, conn):
        issue_id = _insert_issue(conn, state="pending")
        assert can_dispatch(conn, issue_id) is True
        apply_issue_transition(conn, issue_id, "dispatched")

    def test_second_dispatch_rejected(self, conn):
        """Once dispatched, a second dispatch attempt is blocked by state check."""
        issue_id = _insert_issue(conn, state="pending")
        apply_issue_transition(conn, issue_id, "dispatched")
        # can_dispatch returns False — no state mutation should occur
        assert can_dispatch(conn, issue_id) is False
        with pytest.raises(InvalidTransitionError):
            apply_issue_transition(conn, issue_id, "dispatched")

    def test_reconcile_skips_already_dispatched(self, conn):
        """Simulate reconcile: only dispatch pending issues."""
        id1 = _insert_issue(conn, number=1, state="pending")
        id2 = _insert_issue(conn, number=2, state="dispatched")
        id3 = _insert_issue(conn, number=3, state="completed")

        dispatched = []
        for row in conn.execute("SELECT id, state FROM issues").fetchall():
            if can_dispatch(conn, row["id"]):
                apply_issue_transition(conn, row["id"], "dispatched")
                dispatched.append(row["id"])

        assert dispatched == [id1]  # only the pending one
        # id2 still dispatched (not re-dispatched), id3 still completed
        states = {
            r["id"]: r["state"]
            for r in conn.execute("SELECT id, state FROM issues").fetchall()
        }
        assert states[id2] == "dispatched"
        assert states[id3] == "completed"


# ---------------------------------------------------------------------------
# Reconcile idempotency
# ---------------------------------------------------------------------------


class TestReconcileIdempotency:
    def _run_reconcile(self, conn: sqlite3.Connection) -> list[int]:
        """Minimal reconcile: dispatch all pending issues. Returns list of dispatched IDs."""
        dispatched = []
        for row in conn.execute("SELECT id FROM issues WHERE state = 'pending'").fetchall():
            issue_id = row["id"]
            if can_dispatch(conn, issue_id):
                apply_issue_transition(conn, issue_id, "dispatched")
                dispatched.append(issue_id)
        return dispatched

    def test_first_reconcile_dispatches(self, conn):
        id1 = _insert_issue(conn, number=1, state="pending")
        result = self._run_reconcile(conn)
        assert id1 in result

    def test_second_reconcile_is_noop(self, conn):
        _insert_issue(conn, number=1, state="pending")
        self._run_reconcile(conn)
        # second pass: no pending issues remain
        result = self._run_reconcile(conn)
        assert result == []

    def test_reconcile_multiple_times_stable(self, conn):
        _insert_issue(conn, number=1, state="pending")
        _insert_issue(conn, number=2, state="blocked")
        _insert_issue(conn, number=3, state="completed")

        for _ in range(3):
            self._run_reconcile(conn)

        states = {
            r["number"]: r["state"]
            for r in conn.execute("SELECT number, state FROM issues").fetchall()
        }
        assert states[1] == "dispatched"
        assert states[2] == "blocked"
        assert states[3] == "completed"


# ---------------------------------------------------------------------------
# Golden-path integration: register -> dispatch -> complete -> unblock
# ---------------------------------------------------------------------------


class TestGoldenPathIntegration:
    def test_full_lifecycle(self, conn):
        # Register issue
        blocker_id = _insert_issue(conn, number=10, state="pending")
        blocked_id = _insert_issue(conn, number=11, state="blocked", dependency_type="hard")

        # Dispatch blocker
        assert can_dispatch(conn, blocker_id)
        apply_issue_transition(conn, blocker_id, "dispatched")

        # Create and run an attempt for the blocker
        _insert_attempt(conn, "att-1", blocker_id, status="created")
        apply_attempt_transition(conn, "att-1", "running")
        apply_attempt_transition(conn, "att-1", "completed")

        # Blocker completes
        apply_issue_transition(conn, blocker_id, "completed")
        blocker_row = conn.execute(
            "SELECT state FROM issues WHERE id = ?", (blocker_id,)
        ).fetchone()
        assert blocker_row["state"] == "completed"

        # Resolve blocked issue given dep is now complete
        dep_states = [blocker_row["state"]]
        new_state = resolve_blocked_issue(dep_states, DependencyType.HARD.value)
        assert new_state == "pending"

        # Apply unblock transition
        apply_issue_transition(conn, blocked_id, new_state)
        blocked_row = conn.execute(
            "SELECT state FROM issues WHERE id = ?", (blocked_id,)
        ).fetchone()
        assert blocked_row["state"] == "pending"

        # Now the unblocked issue can be dispatched
        assert can_dispatch(conn, blocked_id)

    def test_hard_dep_failure_blocks_dependent_permanently(self, conn):
        blocker_id = _insert_issue(conn, number=20, state="pending")
        blocked_id = _insert_issue(conn, number=21, state="blocked", dependency_type="hard")

        apply_issue_transition(conn, blocker_id, "dispatched")
        apply_issue_transition(conn, blocker_id, "failed-terminal")

        dep_states = ["failed-terminal"]
        new_state = resolve_blocked_issue(dep_states, DependencyType.HARD.value)
        assert new_state == "blocked-failed-dependency"

        apply_issue_transition(conn, blocked_id, "blocked-failed-dependency")
        assert not can_dispatch(conn, blocked_id)

    def test_soft_dep_failure_unblocks_dependent(self, conn):
        blocker_id = _insert_issue(conn, number=30, state="pending")
        blocked_id = _insert_issue(conn, number=31, state="blocked", dependency_type="soft")

        apply_issue_transition(conn, blocker_id, "dispatched")
        apply_issue_transition(conn, blocker_id, "failed-terminal")

        dep_states = ["failed-terminal"]
        new_state = resolve_blocked_issue(dep_states, DependencyType.SOFT.value)
        assert new_state == "pending"

        apply_issue_transition(conn, blocked_id, new_state)
        assert can_dispatch(conn, blocked_id)


# ---------------------------------------------------------------------------
# Lease conflict tests
# ---------------------------------------------------------------------------


class TestLeaseConflicts:
    def test_acquire_lease_succeeds_when_free(self, conn):
        assert try_acquire_lease(conn, "client", holder_pid=1001) is True

    def test_acquire_lease_fails_when_held(self, conn):
        assert try_acquire_lease(conn, "client", holder_pid=1001) is True
        assert try_acquire_lease(conn, "client", holder_pid=1002) is False

    def test_same_pid_can_reacquire(self, conn):
        """A process that already holds the lease can re-acquire (idempotent)."""
        try_acquire_lease(conn, "client", holder_pid=1001)
        assert try_acquire_lease(conn, "client", holder_pid=1001) is True

    def test_different_areas_independent(self, conn):
        assert try_acquire_lease(conn, "client", holder_pid=1001) is True
        assert try_acquire_lease(conn, "server", holder_pid=1002) is True

    def test_release_frees_lease(self, conn):
        try_acquire_lease(conn, "client", holder_pid=1001)
        released = release_lease(conn, "client", holder_pid=1001)
        assert released is True
        # Another PID can now acquire
        assert try_acquire_lease(conn, "client", holder_pid=1002) is True

    def test_release_by_wrong_pid_fails(self, conn):
        try_acquire_lease(conn, "client", holder_pid=1001)
        released = release_lease(conn, "client", holder_pid=9999)
        assert released is False
        # Original holder still owns it
        row = conn.execute("SELECT holder_pid FROM leases WHERE area = ?", ("client",)).fetchone()
        assert row["holder_pid"] == 1001

    def test_expired_lease_is_cleared_on_next_acquire(self, conn):
        # Insert a stale lease manually
        conn.execute(
            "INSERT INTO leases (area, holder_pid, acquired_at, expires_at) VALUES (?, ?, ?, ?)",
            ("client", 9999, "2020-01-01T00:00:00", "2020-01-01T00:01:00"),
        )
        conn.commit()
        # New PID should be able to take over
        result = try_acquire_lease(conn, "client", holder_pid=1001)
        assert result is True
        row = conn.execute("SELECT holder_pid FROM leases WHERE area = ?", ("client",)).fetchone()
        assert row["holder_pid"] == 1001

    def test_holder_can_renew_ttl(self, conn):
        """Holder re-acquires with long TTL; another PID still cannot steal it."""
        try_acquire_lease(conn, "client", holder_pid=1001, ttl_seconds=60)
        # Renew with extended TTL
        renewed = try_acquire_lease(conn, "client", holder_pid=1001, ttl_seconds=300)
        assert renewed is True
        # A different PID cannot take over the live lease
        stolen = try_acquire_lease(conn, "client", holder_pid=1002, ttl_seconds=300)
        assert stolen is False
        row = conn.execute("SELECT holder_pid FROM leases WHERE area = ?", ("client",)).fetchone()
        assert row["holder_pid"] == 1001
