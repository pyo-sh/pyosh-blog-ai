"""State enums and transition maps for orchctl."""

from enum import Enum


class IssueState(str, Enum):
    PENDING = "pending"
    DISPATCHED = "dispatched"
    COMPLETED = "completed"
    FAILED_TERMINAL = "failed-terminal"
    NEEDS_HUMAN = "needs-human"
    BLOCKED_EXTERNAL = "blocked-external"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"
    BLOCKED_FAILED_DEP = "blocked-failed-dependency"


class AttemptStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMED_OUT = "timed-out"


class DependencyType(str, Enum):
    NONE = "none"
    SOFT = "soft"
    HARD = "hard"


# Valid transitions: from_state -> set of reachable to_states
ISSUE_TRANSITIONS: dict[IssueState, frozenset[IssueState]] = {
    IssueState.PENDING: frozenset({
        IssueState.DISPATCHED,
        IssueState.BLOCKED,
        IssueState.CANCELLED,
    }),
    IssueState.DISPATCHED: frozenset({
        IssueState.COMPLETED,
        IssueState.FAILED_TERMINAL,
        IssueState.NEEDS_HUMAN,
        IssueState.BLOCKED_EXTERNAL,
        IssueState.CANCELLED,
    }),
    IssueState.BLOCKED: frozenset({
        IssueState.PENDING,
        IssueState.BLOCKED_FAILED_DEP,
        IssueState.CANCELLED,
    }),
    IssueState.BLOCKED_EXTERNAL: frozenset({
        IssueState.PENDING,
        IssueState.CANCELLED,
    }),
    # Terminal states
    IssueState.COMPLETED: frozenset(),
    IssueState.FAILED_TERMINAL: frozenset(),
    IssueState.NEEDS_HUMAN: frozenset(),
    IssueState.BLOCKED_FAILED_DEP: frozenset(),
    IssueState.CANCELLED: frozenset(),
}

ATTEMPT_TRANSITIONS: dict[AttemptStatus, frozenset[AttemptStatus]] = {
    AttemptStatus.CREATED: frozenset({AttemptStatus.RUNNING}),
    AttemptStatus.RUNNING: frozenset({
        AttemptStatus.COMPLETED,
        AttemptStatus.FAILED,
        AttemptStatus.TIMED_OUT,
    }),
    # Terminal states
    AttemptStatus.COMPLETED: frozenset(),
    AttemptStatus.FAILED: frozenset(),
    AttemptStatus.TIMED_OUT: frozenset(),
}

TERMINAL_ISSUE_STATES: frozenset[IssueState] = frozenset({
    IssueState.COMPLETED,
    IssueState.FAILED_TERMINAL,
    IssueState.NEEDS_HUMAN,
    IssueState.BLOCKED_FAILED_DEP,
    IssueState.CANCELLED,
})

TERMINAL_ATTEMPT_STATUSES: frozenset[AttemptStatus] = frozenset({
    AttemptStatus.COMPLETED,
    AttemptStatus.FAILED,
    AttemptStatus.TIMED_OUT,
})
