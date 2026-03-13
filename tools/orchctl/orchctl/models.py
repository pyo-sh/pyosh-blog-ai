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


class FailureClass(str, Enum):
    INFRA_CRASH = "infra_crash"
    TIMEOUT = "timeout"
    GIT_CONFLICT = "git_conflict"
    FLAKY_TEST = "flaky_test"
    DETERMINISTIC_TEST_FAILURE = "deterministic_test_failure"
    PERMISSION_AUTH = "permission_auth"
    DEPENDENCY_UNRESOLVED = "dependency_unresolved"
    ISSUE_SPEC_AMBIGUOUS = "issue_spec_ambiguous"
    CI_EXTERNAL_OUTAGE = "ci_external_outage"
    RATE_LIMIT = "rate_limit"
    UNKNOWN = "unknown"


class NextAction(str, Enum):
    RETRY = "retry"
    REPAIR = "repair"
    ESCALATE = "escalate"
    PAUSE = "pause"


# Default next_action per failure class.
FAILURE_CLASS_NEXT_ACTION: dict[FailureClass, NextAction] = {
    FailureClass.INFRA_CRASH: NextAction.RETRY,
    FailureClass.TIMEOUT: NextAction.RETRY,
    FailureClass.GIT_CONFLICT: NextAction.REPAIR,
    FailureClass.FLAKY_TEST: NextAction.RETRY,
    FailureClass.DETERMINISTIC_TEST_FAILURE: NextAction.ESCALATE,
    FailureClass.PERMISSION_AUTH: NextAction.ESCALATE,
    FailureClass.DEPENDENCY_UNRESOLVED: NextAction.REPAIR,
    FailureClass.ISSUE_SPEC_AMBIGUOUS: NextAction.ESCALATE,
    FailureClass.CI_EXTERNAL_OUTAGE: NextAction.PAUSE,
    FailureClass.RATE_LIMIT: NextAction.PAUSE,
    FailureClass.UNKNOWN: NextAction.ESCALATE,
}


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
    # Re-openable terminal states: a GitHub issue re-open event drives these
    # back to pending so the orchestrator picks them up in the next cycle.
    # Operator requeue also allows returning operator-intervention states to pending.
    IssueState.COMPLETED: frozenset({IssueState.PENDING}),
    IssueState.FAILED_TERMINAL: frozenset({IssueState.PENDING}),
    IssueState.NEEDS_HUMAN: frozenset({IssueState.PENDING}),
    IssueState.BLOCKED_FAILED_DEP: frozenset({IssueState.PENDING}),
    IssueState.CANCELLED: frozenset({IssueState.PENDING}),
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
