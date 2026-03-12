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
    """Raised when a state transition is not allowed."""

    def __init__(self, from_state: str, to_state: str, entity: str = "issue") -> None:
        self.from_state = from_state
        self.to_state = to_state
        super().__init__(
            f"Invalid {entity} transition: {from_state!r} -> {to_state!r}"
        )


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
        dependency_type: 'soft' or 'hard'.

    Returns:
        New IssueState value ('pending', 'blocked', or 'blocked-failed-dependency').
    """
    if not dep_states:
        return IssueState.PENDING.value

    has_failure = any(
        s in (IssueState.FAILED_TERMINAL.value, IssueState.CANCELLED.value)
        for s in dep_states
    )
    all_done = all(s in [s.value for s in TERMINAL_ISSUE_STATES] for s in dep_states)

    if not all_done:
        return IssueState.BLOCKED.value  # deps still running

    if has_failure and dependency_type == DependencyType.HARD.value:
        return IssueState.BLOCKED_FAILED_DEP.value

    return IssueState.PENDING.value


def try_acquire_lease(
    conn: sqlite3.Connection,
    area: str,
    holder_pid: int,
    ttl_seconds: int = 60,
) -> bool:
    """Attempt to acquire the area lease. Returns True on success, False if held.

    Uses INSERT OR IGNORE so only one writer wins per area.
    Clears expired leases before attempting acquisition.
    """
    conn.execute(
        "DELETE FROM leases WHERE area = ? AND expires_at < datetime('now')",
        (area,),
    )
    conn.execute(
        """
        INSERT OR IGNORE INTO leases (area, holder_pid, acquired_at, expires_at)
        VALUES (?, ?, datetime('now'), datetime('now', ? || ' seconds'))
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
    validated = transition_issue(row["state"], new_state)
    conn.execute(
        "UPDATE issues SET state = ? WHERE id = ?",
        (validated, issue_id),
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
    Raises InvalidTransitionError or ValueError if attempt not found.
    """
    row = conn.execute(
        "SELECT status FROM attempts WHERE attempt_id = ?", (attempt_id,)
    ).fetchone()
    if row is None:
        raise ValueError(f"Attempt id={attempt_id!r} not found")
    validated = transition_attempt(row["status"], new_status)
    conn.execute(
        "UPDATE attempts SET status = ? WHERE attempt_id = ?",
        (validated, attempt_id),
    )
    conn.commit()
    return validated
