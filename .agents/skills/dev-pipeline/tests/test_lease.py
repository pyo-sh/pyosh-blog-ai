"""Tests for issue lease mechanism.

Covers: acquire, conflict detection, release, check-owner, read.
"""
import pytest

from dev_pipeline.lease import (
    LeaseConflictError,
    lease_acquire,
    lease_check_owner,
    lease_read,
    lease_release,
    lease_path,
)


def test_acquire_creates_lease_file(monorepo_root):
    lease_acquire(42, "client", monorepo_root, owner="pipeline")
    path = lease_path(42, "client", monorepo_root)
    assert path.exists()


def test_acquire_writes_owner(monorepo_root):
    lease_acquire(42, "client", monorepo_root, owner="pipeline")
    data = lease_read(42, "client", monorepo_root)
    assert data is not None
    assert data["owner"] == "pipeline"
    assert data["issue"] == 42
    assert data["area"] == "client"


def test_acquire_same_owner_is_idempotent(monorepo_root):
    """Same owner acquiring twice should not raise."""
    lease_acquire(42, "client", monorepo_root, owner="pipeline")
    lease_acquire(42, "client", monorepo_root, owner="pipeline")
    data = lease_read(42, "client", monorepo_root)
    assert data["owner"] == "pipeline"


def test_acquire_different_owner_raises_conflict(monorepo_root):
    """Second owner must be rejected when a different owner holds the lease.

    REGRESSION: without lease enforcement, pipeline and orchestrator ran
    concurrently on the same issue, causing worktree corruption.
    """
    lease_acquire(42, "client", monorepo_root, owner="pipeline")
    with pytest.raises(LeaseConflictError, match="pipeline"):
        lease_acquire(42, "client", monorepo_root, owner="orchestrator")


def test_release_removes_lease(monorepo_root):
    lease_acquire(42, "client", monorepo_root, owner="pipeline")
    lease_release(42, "client", monorepo_root, owner="pipeline")
    assert lease_read(42, "client", monorepo_root) is None


def test_release_wrong_owner_does_not_remove(monorepo_root):
    """Releasing with the wrong owner must not remove the lease."""
    lease_acquire(42, "client", monorepo_root, owner="pipeline")
    lease_release(42, "client", monorepo_root, owner="manual")
    data = lease_read(42, "client", monorepo_root)
    assert data is not None
    assert data["owner"] == "pipeline"


def test_release_nonexistent_is_silent(monorepo_root):
    """Releasing a non-existent lease must not raise."""
    lease_release(99, "client", monorepo_root, owner="pipeline")


def test_check_owner_no_lease_returns_true(monorepo_root):
    """No lease → any owner is acceptable (free slot)."""
    assert lease_check_owner(42, "client", monorepo_root, "pipeline") is True


def test_check_owner_matching_owner_returns_true(monorepo_root):
    lease_acquire(42, "client", monorepo_root, owner="pipeline")
    assert lease_check_owner(42, "client", monorepo_root, "pipeline") is True


def test_check_owner_mismatched_owner_returns_false(monorepo_root):
    lease_acquire(42, "client", monorepo_root, owner="pipeline")
    assert lease_check_owner(42, "client", monorepo_root, "orchestrator") is False


def test_acquire_with_batch_id(monorepo_root):
    lease_acquire(42, "client", monorepo_root, owner="orchestrator", batch_id="batch-001")
    data = lease_read(42, "client", monorepo_root)
    assert data["batchId"] == "batch-001"


def test_lease_isolation_across_issues(monorepo_root):
    """Leases for different issues in the same area are independent."""
    lease_acquire(1, "client", monorepo_root, owner="pipeline")
    lease_acquire(2, "client", monorepo_root, owner="orchestrator")
    assert lease_read(1, "client", monorepo_root)["owner"] == "pipeline"
    assert lease_read(2, "client", monorepo_root)["owner"] == "orchestrator"


def test_manual_orchestrator_conflict(monorepo_root):
    """Manual and orchestrator sessions conflict when lease is already held.

    REGRESSION: user started a manual pipeline session while the orchestrator
    had already dispatched the same issue, causing state corruption.
    """
    lease_acquire(42, "server", monorepo_root, owner="orchestrator", batch_id="batch-007")
    with pytest.raises(LeaseConflictError, match="orchestrator"):
        lease_acquire(42, "server", monorepo_root, owner="manual")
