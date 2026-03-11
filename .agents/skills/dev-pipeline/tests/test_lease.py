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


def test_acquire_uses_excl_atomic_create(monorepo_root, tmp_path):
    """Verify that O_EXCL-based acquire raises ConflictError, not silently overwrites.

    Simulates two processes: first holds the lease, second tries to acquire with
    a different owner. The conflict must be detected even when the file already exists.
    """
    # First process acquires
    lease_acquire(10, "client", monorepo_root, owner="pipeline")
    # Second process with different owner must conflict
    with pytest.raises(LeaseConflictError):
        lease_acquire(10, "client", monorepo_root, owner="orchestrator")
    # The original owner must still hold the lease
    data = lease_read(10, "client", monorepo_root)
    assert data["owner"] == "pipeline"


def test_acquire_same_owner_updates_timestamp(monorepo_root):
    """Same owner re-acquiring overwrites (idempotent) without error."""
    lease_acquire(42, "client", monorepo_root, owner="pipeline")
    first = lease_read(42, "client", monorepo_root)
    lease_acquire(42, "client", monorepo_root, owner="pipeline", batch_id="new-batch")
    second = lease_read(42, "client", monorepo_root)
    assert second["owner"] == "pipeline"
    assert second["batchId"] == "new-batch"


def test_acquire_returns_true_on_new_acquisition(monorepo_root):
    """lease_acquire() returns True when it creates a new lease."""
    result = lease_acquire(42, "client", monorepo_root, owner="pipeline")
    assert result is True


def test_acquire_returns_false_on_same_owner_reacquire(monorepo_root):
    """lease_acquire() returns False when confirming an existing same-owner lease.

    CRITICAL: callers must only call lease_release() when acquired=True.
    If acquired=False, releasing would drop the lease of a concurrent same-owner
    process that is still running, re-opening the issue to other owners mid-run.
    """
    lease_acquire(42, "client", monorepo_root, owner="pipeline")  # first: True
    result = lease_acquire(42, "client", monorepo_root, owner="pipeline")  # second: False
    assert result is False


def test_acquired_false_rc3_does_not_release(monorepo_root):
    """acquired=False + rc=3 (active runner detected): must NOT release.

    Process 1 acquired and is still running (simulated by rc=3 from duplicate guard).
    Process 2 same owner gets acquired=False and rc=3; must leave the lease intact.
    """
    acquired1 = lease_acquire(10, "client", monorepo_root, owner="pipeline")
    assert acquired1 is True

    acquired2 = lease_acquire(10, "client", monorepo_root, owner="pipeline")
    assert acquired2 is False

    rc2 = 3  # dispatch_review duplicate guard: another process is active
    if acquired2 or rc2 != 3:
        lease_release(10, "client", monorepo_root, owner="pipeline")

    data = lease_read(10, "client", monorepo_root)
    assert data is not None, (
        "REGRESSION: acquired=False + rc=3 must not release. "
        "Active first process's lease was removed mid-run."
    )
    assert data["owner"] == "pipeline"


def test_resume_after_crash_releases_lease(monorepo_root):
    """acquired=False + rc=0 (resume after crash): MUST release.

    Process 1 crashed — lease file remains but no active runner.
    Process 2 (resume/retry) gets acquired=False, runs successfully (rc=0),
    and must release the lease when done so the next owner can proceed.

    REGRESSION: if acquired=False always blocked release, a resume after a
    crash left the lease behind forever, permanently blocking other owners.
    """
    # Simulate crashed process 1: lease exists but process is gone
    lease_acquire(10, "client", monorepo_root, owner="manual")

    # Process 2 (resume) same owner — gets False
    acquired2 = lease_acquire(10, "client", monorepo_root, owner="manual")
    assert acquired2 is False

    rc2 = 0  # dispatch completed successfully
    if acquired2 or rc2 != 3:
        lease_release(10, "client", monorepo_root, owner="manual")

    assert lease_read(10, "client", monorepo_root) is None, (
        "REGRESSION: resume after crash (acquired=False, rc=0) must release. "
        "Lease was left behind, blocking the next owner permanently."
    )
