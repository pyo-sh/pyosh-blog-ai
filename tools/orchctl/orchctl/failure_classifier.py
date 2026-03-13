"""Failure classification for orchestrator attempts.

Classifies a failed or timed-out attempt into one of 10 FailureClass values
based on the attempt status, terminal_json reason, and log text.

The result drives the next_action (retry / repair / escalate / pause) and is
recorded on both the attempt row and the parent issue row.
"""

from __future__ import annotations

import json
import re
import sqlite3

from .models import FAILURE_CLASS_NEXT_ACTION, FailureClass, NextAction


# ---------------------------------------------------------------------------
# Pattern tables
# ---------------------------------------------------------------------------

# Ordered list of (pattern, FailureClass).  First match wins.
# Patterns are matched case-insensitively against the combined signal text.
_PATTERNS: list[tuple[re.Pattern[str], FailureClass]] = [
    (re.compile(r"rate.?limit", re.IGNORECASE), FailureClass.RATE_LIMIT),
    (re.compile(r"\b429\b"), FailureClass.RATE_LIMIT),
    (re.compile(
        r"permission denied|authentication failed|unauthorized"
        r"|\b401\b|\b403\b|invalid token|bad credential",
        re.IGNORECASE,
    ), FailureClass.PERMISSION_AUTH),
    (re.compile(
        r"merge conflict|CONFLICT \(|conflict in |rebase failed"
        r"|cannot rebase|git conflict",
        re.IGNORECASE,
    ), FailureClass.GIT_CONFLICT),
    (re.compile(
        r"service unavailable|\b503\b|connection refused|connection timed out"
        r"|external outage|could not connect|network unreachable",
        re.IGNORECASE,
    ), FailureClass.CI_EXTERNAL_OUTAGE),
    (re.compile(
        r"module not found|package not found|dependency.*not.*found"
        r"|unresolved dependency|cannot find module|no such package"
        r"|import.*error.*no module",
        re.IGNORECASE,
    ), FailureClass.DEPENDENCY_UNRESOLVED),
    (re.compile(
        r"ambiguous.*issue|unclear.*spec|needs.?spec|specification.*ambiguous"
        r"|issue.*incomplete|missing.*requirements",
        re.IGNORECASE,
    ), FailureClass.ISSUE_SPEC_AMBIGUOUS),
    (re.compile(
        r"flaky|non.?deterministic|intermittent.*test|test.*intermittent"
        r"|randomly.*fail",
        re.IGNORECASE,
    ), FailureClass.FLAKY_TEST),
    (re.compile(
        r"test.*fail|assert.*error|assertion.*fail|spec.*fail"
        r"|jest.*fail|pytest.*fail|pnpm test",
        re.IGNORECASE,
    ), FailureClass.DETERMINISTIC_TEST_FAILURE),
    (re.compile(
        r"segfault|segmentation fault|killed.*signal|signal \d+|out of memory"
        r"|oom|process crash|core dump|rc=139|rc=137",
        re.IGNORECASE,
    ), FailureClass.INFRA_CRASH),
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def classify(
    attempt_status: str,
    terminal_json_text: str | None,
    log_text: str | None = None,
) -> FailureClass:
    """Classify a failed attempt into a FailureClass.

    Args:
        attempt_status: The attempts.status value (e.g. "timed-out", "failed").
        terminal_json_text: Raw JSON string from attempts.terminal_json, or None.
        log_text: Optional worker log/stderr text for additional signal.

    Returns:
        The best-matching FailureClass (never None; falls back to UNKNOWN).
    """
    if attempt_status == "timed-out":
        return FailureClass.TIMEOUT

    signal = _build_signal(terminal_json_text, log_text)
    if not signal:
        return FailureClass.UNKNOWN

    for pattern, failure_class in _PATTERNS:
        if pattern.search(signal):
            return failure_class

    return FailureClass.UNKNOWN


def next_action_for_class(failure_class: FailureClass) -> NextAction:
    """Return the default NextAction for a given FailureClass."""
    return FAILURE_CLASS_NEXT_ACTION.get(failure_class, NextAction.ESCALATE)


def record_attempt_failure_class(
    conn: sqlite3.Connection,
    attempt_id: str,
    failure_class: FailureClass,
) -> None:
    """Write failure_class to the attempt row."""
    conn.execute(
        "UPDATE attempts SET failure_class = ? WHERE attempt_id = ?",
        (failure_class.value, attempt_id),
    )


def record_issue_failure_class(
    conn: sqlite3.Connection,
    issue_id: int,
    failure_class: FailureClass,
) -> None:
    """Write failure_class to the issue row (reflects the most recent attempt)."""
    conn.execute(
        "UPDATE issues SET failure_class = ? WHERE id = ?",
        (failure_class.value, issue_id),
    )


def classify_and_record(
    conn: sqlite3.Connection,
    issue_id: int,
    attempt_id: str,
    attempt_status: str,
    terminal_json_text: str | None,
) -> tuple[FailureClass, NextAction]:
    """Classify the attempt, write results to DB, and return (class, next_action).

    Does NOT commit — caller owns the transaction.

    Note: log_text is not forwarded here because worker log files are not stored
    in the DB.  If richer log-based classification is needed in the future,
    callers can pass the log content to classify() directly.
    """
    fc = classify(attempt_status, terminal_json_text)
    na = next_action_for_class(fc)
    record_attempt_failure_class(conn, attempt_id, fc)
    record_issue_failure_class(conn, issue_id, fc)
    return fc, na


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_signal(terminal_json_text: str | None, log_text: str | None) -> str:
    """Combine available text sources into a single classification signal."""
    parts: list[str] = []

    if terminal_json_text:
        try:
            tj = json.loads(terminal_json_text)
            reason = tj.get("reason") or ""
            if reason:
                parts.append(reason)
        except (json.JSONDecodeError, AttributeError):
            parts.append(terminal_json_text[:500])

    if log_text:
        # Use only the tail — failures are typically at the end.
        parts.append(log_text[-2000:])

    return "\n".join(parts)
