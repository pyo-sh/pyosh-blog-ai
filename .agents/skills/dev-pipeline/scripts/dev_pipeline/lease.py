"""Issue lease mechanism.

A lease file at .workspace/pipeline/{area}/issue-{N}.lease.json records which
owner (manual / pipeline / orchestrator) currently holds an issue. All dispatch,
quarantine, cleanup, and resume operations should check the lease first to
prevent concurrent access conflicts.
"""
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class LeaseConflictError(Exception):
    """Raised when a lease is held by a different owner."""


def lease_path(issue: int, area: str, monorepo_root: Path) -> Path:
    return monorepo_root / ".workspace" / "pipeline" / area / f"issue-{issue}.lease.json"


def lease_acquire(
    issue: int,
    area: str,
    monorepo_root: Path,
    owner: str,
    batch_id: str = "",
) -> None:
    """Acquire lease for an issue.

    owner: "manual" | "pipeline" | "orchestrator"
    batch_id: optional orchestrator batch identifier

    Raises LeaseConflictError if the issue is already held by a different owner.
    """
    path = lease_path(issue, area, monorepo_root)
    if path.exists():
        try:
            existing = json.loads(path.read_text())
            existing_owner = existing.get("owner", "")
            if existing_owner and existing_owner != owner:
                raise LeaseConflictError(
                    f"[lease] issue #{issue} area={area} is held by "
                    f"'{existing_owner}' "
                    f"(batchId={existing.get('batchId', '')!r}, "
                    f"startedAt={existing.get('startedAt', '')})"
                )
        except (json.JSONDecodeError, OSError):
            pass  # corrupted lease - overwrite

    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "issue": issue,
        "area": area,
        "owner": owner,
        "batchId": batch_id,
        "startedAt": _now_iso(),
    }
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".tmp.")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
        os.replace(tmp, str(path))
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def lease_release(issue: int, area: str, monorepo_root: Path, owner: str) -> None:
    """Release lease if currently held by owner. Silent if no lease exists."""
    path = lease_path(issue, area, monorepo_root)
    if not path.exists():
        return
    try:
        existing = json.loads(path.read_text())
        if existing.get("owner") == owner:
            path.unlink(missing_ok=True)
    except (json.JSONDecodeError, OSError):
        path.unlink(missing_ok=True)


def lease_read(issue: int, area: str, monorepo_root: Path) -> Optional[dict]:
    """Return current lease dict, or None if no lease exists."""
    path = lease_path(issue, area, monorepo_root)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def lease_check_owner(
    issue: int,
    area: str,
    monorepo_root: Path,
    expected_owner: str,
) -> bool:
    """Return True if lease is held by expected_owner (or no lease exists)."""
    current = lease_read(issue, area, monorepo_root)
    if current is None:
        return True
    return current.get("owner") == expected_owner
