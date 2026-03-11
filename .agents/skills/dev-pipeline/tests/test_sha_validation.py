"""Regression tests for SHA validation in state_store.

Full 40-char hex SHA must be enforced when setting lastCommitSha.
Abbreviated SHAs (e.g. 7-char git default) must be rejected immediately.
"""
import json

import pytest

from dev_pipeline.state_store import state_update


VALID_SHA = "a" * 40
VALID_SHA_UPPER = "A" * 40
ABBREVIATED_SHA = "abc1234"
SHORT_SHA = "abc123"
EMPTY_SHA = ""


@pytest.fixture
def state_file(monorepo_root, sample_state):
    """Write sample_state to the expected state file location."""
    from dev_pipeline.models import PipelineState
    from dev_pipeline.state_store import state_write

    area = sample_state["area"]
    issue = sample_state["issue"]
    state = PipelineState.from_dict(sample_state)
    state_write(issue, area, monorepo_root, state)
    return monorepo_root


def test_valid_40char_sha_accepted(state_file, sample_state):
    """Full 40-char lowercase hex SHA is accepted."""
    state_update(
        sample_state["issue"], sample_state["area"], state_file,
        {"lastCommitSha": VALID_SHA},
    )
    # verify it was written
    from dev_pipeline.state_store import state_read
    state = state_read(sample_state["issue"], sample_state["area"], state_file)
    assert state.last_commit_sha == VALID_SHA


def test_valid_40char_sha_uppercase_accepted(state_file, sample_state):
    """Full 40-char uppercase hex SHA is accepted."""
    state_update(
        sample_state["issue"], sample_state["area"], state_file,
        {"lastCommitSha": VALID_SHA_UPPER},
    )
    from dev_pipeline.state_store import state_read
    state = state_read(sample_state["issue"], sample_state["area"], state_file)
    assert state.last_commit_sha == VALID_SHA_UPPER


def test_abbreviated_sha_rejected(state_file, sample_state):
    """Abbreviated SHA (7 chars) must be rejected.

    REGRESSION: manual state-update with abbreviated SHA caused
    check_new_commits() to always return 'new commit' even when there
    was none, leading to infinite resolve loops.
    """
    with pytest.raises(ValueError, match="40-char"):
        state_update(
            sample_state["issue"], sample_state["area"], state_file,
            {"lastCommitSha": ABBREVIATED_SHA},
        )


def test_short_sha_rejected(state_file, sample_state):
    """Any SHA shorter than 40 chars must be rejected."""
    with pytest.raises(ValueError, match="40-char"):
        state_update(
            sample_state["issue"], sample_state["area"], state_file,
            {"lastCommitSha": SHORT_SHA},
        )


def test_empty_sha_is_allowed(state_file, sample_state):
    """Empty string SHA is allowed (used for resetting / initial state)."""
    state_update(
        sample_state["issue"], sample_state["area"], state_file,
        {"lastCommitSha": EMPTY_SHA},
    )
    from dev_pipeline.state_store import state_read
    state = state_read(sample_state["issue"], sample_state["area"], state_file)
    assert state.last_commit_sha == EMPTY_SHA


def test_none_sha_is_allowed(state_file, sample_state):
    """None SHA is allowed (treated as absent/reset)."""
    state_update(
        sample_state["issue"], sample_state["area"], state_file,
        {"lastCommitSha": None},
    )


def test_other_fields_unaffected_by_sha_validation(state_file, sample_state):
    """Updating non-SHA fields still works normally."""
    state_update(
        sample_state["issue"], sample_state["area"], state_file,
        {"step": "resolve"},
    )
    from dev_pipeline.state_store import state_read
    state = state_read(sample_state["issue"], sample_state["area"], state_file)
    assert state.step.value == "resolve"
