"""State machine transition logic for issues and attempts."""

import sqlite3

from .models import (
    ATTEMPT_TRANSITIONS,
    ISSUE_TRANSITIONS,
    TERMINAL_ISSUE_STATES,
    AttemptStatus,
    DependencyType,
    IssueState,
)


class InvalidTransitionError(Exception):
    """Raised when a state transition is not allowed by the state machine rules."""

    def __init__(self, from_state: str, to_state: str, entity: str = "issue") -> None:
        self.from_state = from_state
        self.to_state = to_state
        super().__init__(
            f"Invalid {entity} transition: {from_state!r} -> {to_state!r}"
        )


class StaleStateError(Exception):
    """Raised when a DB transition fails because the row state changed concurrently.

    Distinct from InvalidTransitionError (which means the transition is logically
    forbidden). A StaleStateError means the transition was valid but lost an
    optimistic-lock race — the caller should re-read state and retry if appropriate.
    """


def transition_issue(current: str, new: str) -> str:
    """Validate an issue state transition. Returns new state on success.

    Raises InvalidTransitionError if the transition is not allowed.
    """
    try:
        from_state = IssueState(current)
        to_state = IssueState(new)
    except ValueError as exc:
        raise InvalidTransitionError(current, new) from exc

    if to_state not in ISSUE_TRANSITIONS[from_state]:
        raise InvalidTransitionError(current, new)
    return to_state.value


def transition_attempt(current: str, new: str) -> str:
    """Validate an attempt status transition. Returns new status on success.

    Raises InvalidTransitionError if the transition is not allowed.
    """
    try:
        from_status = AttemptStatus(current)
        to_status = AttemptStatus(new)
    except ValueError as exc:
        raise InvalidTransitionError(current, new, entity="attempt") from exc

    if to_status not in ATTEMPT_TRANSITIONS[from_status]:
        raise InvalidTransitionError(current, new, entity="attempt")
    return to_status.value


def resolve_blocked_issue(
    dep_states: list[str],
    dependency_type: str,
) -> str:
    """Determine what state a blocked issue should transition to given dep outcomes.

    Args:
        dep_states: List of terminal states of the blocking dependencies.
        dependency_type: 'soft', 'hard', or 'none'. 'none' behaves like 'soft'
            (no failure check applied) — issues with dependency_type='none' should
            not normally reach 'blocked' state, but are handled gracefully.

    Returns:
        New IssueState value ('pending', 'blocked', or 'blocked-failed-dependency').
    """
    if not dep_states:
        return IssueState.PENDING.value

    terminal_values = {st.value for st in TERMINAL_ISSUE_STATES}
    all_done = all(s in terminal_values for s in dep_states)

    if not all_done:
        return IssueState.BLOCKED.value  # deps still running

    # For hard deps, any terminal state other than 'completed' is a failure.
    if dependency_type == DependencyType.HARD.value:
        has_failure = any(s != IssueState.COMPLETED.value for s in dep_states)
        if has_failure:
            return IssueState.BLOCKED_FAILED_DEP.value

    return IssueState.PENDING.value


def try_acquire_lease(
    conn: sqlite3.Connection,
    area: str,
    holder_pid: int,
    ttl_seconds: int = 60,
) -> bool:
    """Attempt to acquire or renew the area lease. Returns True on success, False if held.

    Expired leases are cleared first so a new holder can take over. An existing
    holder can renew its own lease (resets expires_at). A different PID cannot
    acquire while a valid lease is held.
    """
    # Clear any expired lease to allow a new holder to acquire.
    conn.execute(
        "DELETE FROM leases WHERE area = ? AND expires_at < datetime('now')",
        (area,),
    )
    conn.execute(
        """
        INSERT INTO leases (area, holder_pid, acquired_at, expires_at)
        VALUES (?, ?, datetime('now'), datetime('now', ? || ' seconds'))
        ON CONFLICT(area) DO UPDATE SET
            expires_at = excluded.expires_at
        WHERE holder_pid = excluded.holder_pid
        """,
        (area, holder_pid, str(ttl_seconds)),
    )
    conn.commit()
    row = conn.execute(
        "SELECT holder_pid FROM leases WHERE area = ?", (area,)
    ).fetchone()
    return row is not None and row["holder_pid"] == holder_pid


def release_lease(conn: sqlite3.Connection, area: str, holder_pid: int) -> bool:
    """Release the lease for area if held by holder_pid. Returns True if released."""
    cur = conn.execute(
        "DELETE FROM leases WHERE area = ? AND holder_pid = ?",
        (area, holder_pid),
    )
    conn.commit()
    return cur.rowcount > 0


def can_dispatch(conn: sqlite3.Connection, issue_id: int) -> bool:
    """Return True if the issue is in a dispatchable state (pending only)."""
    row = conn.execute(
        "SELECT state FROM issues WHERE id = ?", (issue_id,)
    ).fetchone()
    if row is None:
        return False
    return row["state"] == IssueState.PENDING.value


def apply_issue_transition(
    conn: sqlite3.Connection,
    issue_id: int,
    new_state: str,
) -> str:
    """Validate and apply an issue state transition in the DB.

    Returns the new state string.
    Raises InvalidTransitionError or ValueError if issue not found.
    """
    row = conn.execute(
        "SELECT state FROM issues WHERE id = ?", (issue_id,)
    ).fetchone()
    if row is None:
        raise ValueError(f"Issue id={issue_id} not found")
    old_state = row["state"]
    validated = transition_issue(old_state, new_state)
    cur = conn.execute(
        "UPDATE issues SET state = ? WHERE id = ? AND state = ?",
        (validated, issue_id, old_state),
    )
    if cur.rowcount == 0:
        raise StaleStateError(
            f"Issue id={issue_id} state changed concurrently "
            f"(read {old_state!r}, attempted transition to {new_state!r})"
        )
    conn.commit()
    return validated


def apply_attempt_transition(
    conn: sqlite3.Connection,
    attempt_id: str,
    new_status: str,
) -> str:
    """Validate and apply an attempt status transition in the DB.

    Returns the new status string.
    Raises InvalidTransitionError, StaleStateError, or ValueError if not found.
    """
    row = conn.execute(
        "SELECT status FROM attempts WHERE attempt_id = ?", (attempt_id,)
    ).fetchone()
    if row is None:
        raise ValueError(f"Attempt id={attempt_id!r} not found")
    old_status = row["status"]
    validated = transition_attempt(old_status, new_status)
    cur = conn.execute(
        "UPDATE attempts SET status = ? WHERE attempt_id = ? AND status = ?",
        (validated, attempt_id, old_status),
    )
    if cur.rowcount == 0:
        raise StaleStateError(
            f"Attempt id={attempt_id!r} status changed concurrently "
            f"(read {old_status!r}, attempted transition to {new_status!r})"
        )
    conn.commit()
    return validated
