"""orchctl export adapter for agent-tracker.

Reads the normalized per-area export produced by `orchctl export` and maps
it to tracker domain models (BatchState, DispatchedIssue).

Usage modes
-----------
1. **Real export** (production):
   Call `read_exports(export_dir)` where *export_dir* is the path containing
   per-area subdirectories with `current.json` files:
     <export_dir>/<area>/current.json

2. **Fixture** (development / tests):
   Call `read_exports_from_fixture(fixture_path)` with a single export JSON
   file (see `backend/fixtures/orchctl_export.json`).

3. **Auto-detect** (recommended):
   Call `load_exports(export_dir)` - reads real exports if available, falls
   back to the built-in fixture when the directory is absent or empty.

Mapping rules
-------------
- One BatchState is produced per export file.
- DispatchedIssue entries correspond to `active_workers` in the export.
  The `step` field is not available in the export; it requires a pipeline
  state read which the caller (collector) may supply via `pipeline_dir`.
- `BatchStatus` is derived from the batch summary in the export.
- Process liveness for the batch uses `active_workers[].alive`.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from ..contract import (
    EXPORT_SCHEMA_VERSION,
    BatchStatus,
)
from ..models import BatchState, DispatchedIssue

# Active issue states (mirrors orchctl.contract.ACTIVE_ISSUE_STATES)
_ACTIVE_STATES: frozenset[str] = frozenset({
    "pending",
    "dispatched",
    "blocked",
    "blocked-external",
})

# Built-in fixture path
_FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "orchctl_export.json"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_exports(
    export_dir: str | Path,
    pipeline_dir: str | Path | None = None,
) -> list[BatchState]:
    """Load exports from *export_dir*, falling back to the built-in fixture.

    *export_dir* should contain subdirectories named after areas, each with
    a `current.json` file written by `orchctl export`.

    *pipeline_dir* is used to enrich DispatchedIssue.step from pipeline state
    when available. Pass None to skip (step will be '-').
    """
    export_dir = Path(export_dir)
    export_files = _discover_export_files(export_dir)
    if export_files:
        return _parse_export_files(export_files, pipeline_dir)
    return read_exports_from_fixture(_FIXTURE_PATH, pipeline_dir)


def read_exports(
    export_dir: str | Path,
    pipeline_dir: str | Path | None = None,
) -> list[BatchState]:
    """Read all per-area export files under *export_dir*.

    Returns an empty list if no export files are found (does not fall back
    to the fixture).
    """
    files = _discover_export_files(Path(export_dir))
    return _parse_export_files(files, pipeline_dir)


def read_exports_from_fixture(
    fixture_path: str | Path = _FIXTURE_PATH,
    pipeline_dir: str | Path | None = None,
) -> list[BatchState]:
    """Parse a single fixture/export JSON file into BatchState list."""
    path = Path(fixture_path)
    data = _read_json(path)
    if data is None:
        return []
    return [_parse_one(data, pipeline_dir)]


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def _discover_export_files(export_dir: Path) -> list[Path]:
    """Find all `current.json` files under *export_dir*/<area>/."""
    if not export_dir.is_dir():
        return []
    files = sorted(export_dir.glob("*/current.json"))
    return [f for f in files if f.is_file()]


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def _parse_export_files(
    files: list[Path],
    pipeline_dir: str | Path | None,
) -> list[BatchState]:
    batches: list[BatchState] = []
    for f in files:
        data = _read_json(f)
        if data is None:
            continue
        if data.get("schema_version") != EXPORT_SCHEMA_VERSION:
            # Skip incompatible versions rather than crashing.
            continue
        try:
            batch = _parse_one(data, pipeline_dir)
        except (KeyError, TypeError, ValueError):
            continue
        batches.append(batch)
    return batches


def _parse_one(data: dict, pipeline_dir: str | Path | None) -> BatchState:
    """Map one export document to a BatchState."""
    area = data["area"]
    now = time.time()

    # --- Batch summary ---
    batch_list = data.get("batches") or []
    if batch_list:
        b = batch_list[0]
        n_total = int(b.get("n_total") or 0)
        n_done = int(b.get("n_done") or 0)
        n_failed = int(b.get("n_failed") or 0)
        n_dispatched = int(b.get("n_dispatched") or 0)
    else:
        # Derive counts from issues list directly.
        issues = data.get("issues") or []
        n_total = len(issues)
        n_done = sum(1 for i in issues if i.get("state") == "completed")
        n_failed = sum(1 for i in issues if i.get("state") == "failed-terminal")
        n_dispatched = sum(1 for i in issues if i.get("state") == "dispatched")

    # --- Batch status ---
    active_workers = data.get("active_workers") or []
    any_alive = any(w.get("alive") for w in active_workers)

    if n_total > 0 and (n_done + n_failed) >= n_total:
        batch_status = BatchStatus.DONE
    elif any_alive or n_dispatched > 0:
        batch_status = BatchStatus.ACTIVE
    else:
        batch_status = BatchStatus.DEAD

    # --- Elapsed / created_at ---
    generated_at = float(data.get("generated_at") or now)
    elapsed = _format_elapsed(int(now - generated_at)) if generated_at else ""

    # --- Dispatched issues (active workers only) ---
    dispatched: list[DispatchedIssue] = []
    for worker in active_workers:
        issue_num = str(worker.get("issue_number") or "")
        if not issue_num:
            continue

        alive = bool(worker.get("alive"))
        started_at = worker.get("started_at") or ""
        worker_elapsed = _elapsed_from_iso(started_at, now)

        # Enrich with pipeline step if available.
        step = _read_pipeline_step(pipeline_dir, area, issue_num) if pipeline_dir else "-"
        pr_num = _read_pipeline_pr(pipeline_dir, area, issue_num) if pipeline_dir else 0

        dispatched.append(DispatchedIssue(
            issue=issue_num,
            alive=alive,
            step=step,
            pr_num=pr_num,
            elapsed=worker_elapsed,
        ))

    return BatchState(
        area=area,
        batch_id=f"{area}-export",
        batch_status=batch_status,
        n_done=n_done,
        n_failed=n_failed,
        n_total=n_total,
        created_at="",
        elapsed=elapsed,
        dispatched=dispatched,
    )


# ---------------------------------------------------------------------------
# Pipeline state enrichment
# ---------------------------------------------------------------------------

def _read_pipeline_step(
    pipeline_dir: str | Path,
    area: str,
    issue: str,
) -> str:
    ps = _read_pipeline_state(pipeline_dir, area, issue)
    return (ps.get("step") or "-") if ps else "-"


def _read_pipeline_pr(
    pipeline_dir: str | Path,
    area: str,
    issue: str,
) -> int:
    ps = _read_pipeline_state(pipeline_dir, area, issue)
    if not ps:
        return 0
    try:
        return int(ps.get("pr") or 0)
    except (TypeError, ValueError):
        return 0


def _read_pipeline_state(
    pipeline_dir: str | Path,
    area: str,
    issue: str,
) -> dict | None:
    path = Path(pipeline_dir) / area / f"issue-{issue}.state.json"
    return _read_json(path)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_json(path: Path) -> dict | None:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _elapsed_from_iso(iso_str: str, now: float) -> str:
    if not iso_str:
        return ""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        secs = int(now - dt.timestamp())
        return _format_elapsed(secs)
    except (ValueError, TypeError):
        return ""


def _format_elapsed(secs: int) -> str:
    if secs < 0:
        secs = 0
    if secs >= 3600:
        return f"{secs // 3600}h{(secs % 3600) // 60:02d}m"
    if secs >= 60:
        return f"{secs // 60}m{secs % 60:02d}s"
    return f"{secs}s"
