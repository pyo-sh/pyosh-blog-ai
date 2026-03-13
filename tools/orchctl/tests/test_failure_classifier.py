"""Unit tests for orchctl.failure_classifier."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from orchctl.db.connection import init_db
from orchctl.failure_classifier import (
    classify,
    classify_and_record,
    next_action_for_class,
    record_failure_class,
)
from orchctl.models import FailureClass, NextAction


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def conn(tmp_path: Path):
    db_path = tmp_path / "test.db"
    c, _ = init_db(db_path)
    # Insert a test issue and attempt for DB-write tests.
    c.execute(
        "INSERT INTO issues (area, number, state) VALUES ('workspace', 1, 'dispatched')"
    )
    c.execute(
        "INSERT INTO attempts (attempt_id, issue_id, status) VALUES ('a-001', 1, 'failed')"
    )
    c.commit()
    yield c
    c.close()


# ---------------------------------------------------------------------------
# classify() — parametrized table-driven tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "attempt_status, terminal_json, expected",
    [
        # timed-out short-circuit
        ("timed-out", None, FailureClass.TIMEOUT),
        ("timed-out", '{"reason": "rate limit exceeded"}', FailureClass.TIMEOUT),
        # rate_limit
        ("failed", '{"reason": "rate limit exceeded"}', FailureClass.RATE_LIMIT),
        ("failed", '{"reason": "HTTP 429 Too Many Requests"}', FailureClass.RATE_LIMIT),
        # permission_auth
        ("failed", '{"reason": "permission denied on push"}', FailureClass.PERMISSION_AUTH),
        ("failed", '{"reason": "authentication failed: bad token"}', FailureClass.PERMISSION_AUTH),
        ("failed", '{"reason": "HTTP 401 Unauthorized"}', FailureClass.PERMISSION_AUTH),
        ("failed", '{"reason": "HTTP 403 Forbidden"}', FailureClass.PERMISSION_AUTH),
        # git_conflict
        ("failed", '{"reason": "CONFLICT (content): Merge conflict in src/foo.ts"}', FailureClass.GIT_CONFLICT),
        ("failed", '{"reason": "rebase failed due to conflict"}', FailureClass.GIT_CONFLICT),
        # ci_external_outage
        ("failed", '{"reason": "service unavailable"}', FailureClass.CI_EXTERNAL_OUTAGE),
        ("failed", '{"reason": "HTTP 503 Service Unavailable"}', FailureClass.CI_EXTERNAL_OUTAGE),
        ("failed", '{"reason": "connection refused"}', FailureClass.CI_EXTERNAL_OUTAGE),
        # dependency_unresolved
        ("failed", '{"reason": "module not found: react"}', FailureClass.DEPENDENCY_UNRESOLVED),
        ("failed", '{"reason": "cannot find module \'lodash\'"}', FailureClass.DEPENDENCY_UNRESOLVED),
        # issue_spec_ambiguous
        ("failed", '{"reason": "ambiguous issue: missing requirements"}', FailureClass.ISSUE_SPEC_AMBIGUOUS),
        ("failed", '{"reason": "needs-spec: unclear specification"}', FailureClass.ISSUE_SPEC_AMBIGUOUS),
        # flaky_test
        ("failed", '{"reason": "flaky test detected"}', FailureClass.FLAKY_TEST),
        ("failed", '{"reason": "intermittent test failure"}', FailureClass.FLAKY_TEST),
        # deterministic_test_failure
        ("failed", '{"reason": "test failed: 3 assertions"}', FailureClass.DETERMINISTIC_TEST_FAILURE),
        ("failed", '{"reason": "jest failed with exit code 1"}', FailureClass.DETERMINISTIC_TEST_FAILURE),
        ("failed", '{"reason": "pnpm test failed with error"}', FailureClass.DETERMINISTIC_TEST_FAILURE),
        # infra_crash
        ("failed", '{"reason": "segmentation fault (core dump)"}', FailureClass.INFRA_CRASH),
        ("failed", '{"reason": "killed by signal 9 (OOM)"}', FailureClass.INFRA_CRASH),
        # unknown fallback
        ("failed", '{"reason": "pipeline exited with rc=1"}', FailureClass.UNKNOWN),
        ("failed", None, FailureClass.UNKNOWN),
        ("failed", "", FailureClass.UNKNOWN),
        ("failed", '{"reason": ""}', FailureClass.UNKNOWN),
    ],
)
def test_classify(attempt_status: str, terminal_json: str | None, expected: FailureClass) -> None:
    assert classify(attempt_status, terminal_json) == expected


def test_classify_invalid_json_falls_back() -> None:
    # Malformed JSON: raw text is used as signal; falls to UNKNOWN if no pattern matches.
    result = classify("failed", "not-json-at-all")
    assert result == FailureClass.UNKNOWN


def test_classify_invalid_json_with_pattern() -> None:
    result = classify("failed", "rate limit exceeded (raw log)")
    assert result == FailureClass.RATE_LIMIT


def test_pnpm_test_log_prefix_does_not_match() -> None:
    """'Starting: pnpm test' should not trigger DETERMINISTIC_TEST_FAILURE."""
    result = classify("failed", '{"reason": "Starting: pnpm test"}')
    assert result == FailureClass.UNKNOWN


def test_infra_crash_not_shadowed_by_test_failure() -> None:
    """OOM/signal in a test log should be INFRA_CRASH, not DETERMINISTIC_TEST_FAILURE."""
    result = classify("failed", '{"reason": "pytest failed: process killed by signal 9"}')
    assert result == FailureClass.INFRA_CRASH

    result = classify("failed", '{"reason": "jest failed with rc=137"}')
    assert result == FailureClass.INFRA_CRASH


def test_oom_word_boundary_no_false_positive() -> None:
    """Substrings like 'bloom' and 'room' must not match INFRA_CRASH."""
    assert classify("failed", '{"reason": "bloom filter error"}') == FailureClass.UNKNOWN
    assert classify("failed", '{"reason": "looming deadline missed"}') == FailureClass.UNKNOWN
    assert classify("failed", '{"reason": "out of memory: rc=137"}') == FailureClass.INFRA_CRASH
    assert classify("failed", '{"reason": "oom killer invoked"}') == FailureClass.INFRA_CRASH


# ---------------------------------------------------------------------------
# next_action_for_class()
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "failure_class, expected_action",
    [
        (FailureClass.INFRA_CRASH, NextAction.RETRY),
        (FailureClass.TIMEOUT, NextAction.RETRY),
        (FailureClass.FLAKY_TEST, NextAction.RETRY),
        (FailureClass.GIT_CONFLICT, NextAction.REPAIR),
        (FailureClass.DEPENDENCY_UNRESOLVED, NextAction.REPAIR),
        (FailureClass.DETERMINISTIC_TEST_FAILURE, NextAction.ESCALATE),
        (FailureClass.PERMISSION_AUTH, NextAction.ESCALATE),
        (FailureClass.ISSUE_SPEC_AMBIGUOUS, NextAction.ESCALATE),
        (FailureClass.UNKNOWN, NextAction.ESCALATE),
        (FailureClass.CI_EXTERNAL_OUTAGE, NextAction.PAUSE),
        (FailureClass.RATE_LIMIT, NextAction.PAUSE),
    ],
)
def test_next_action_for_class(failure_class: FailureClass, expected_action: NextAction) -> None:
    assert next_action_for_class(failure_class) == expected_action


# ---------------------------------------------------------------------------
# record_failure_class() / classify_and_record() — DB writes
# ---------------------------------------------------------------------------


def test_record_failure_class_writes_to_db(conn: sqlite3.Connection) -> None:
    record_failure_class(conn, 1, "a-001", FailureClass.TIMEOUT)
    conn.commit()

    attempt = conn.execute(
        "SELECT failure_class FROM attempts WHERE attempt_id = 'a-001'"
    ).fetchone()
    issue = conn.execute(
        "SELECT failure_class FROM issues WHERE id = 1"
    ).fetchone()

    assert attempt["failure_class"] == "timeout"
    assert issue["failure_class"] == "timeout"


def test_classify_and_record_returns_class_and_action(conn: sqlite3.Connection) -> None:
    fc, na = classify_and_record(
        conn, 1, "a-001", "timed-out", None
    )
    assert fc == FailureClass.TIMEOUT
    assert na == NextAction.RETRY

    conn.commit()
    row = conn.execute(
        "SELECT failure_class FROM attempts WHERE attempt_id = 'a-001'"
    ).fetchone()
    assert row["failure_class"] == "timeout"
