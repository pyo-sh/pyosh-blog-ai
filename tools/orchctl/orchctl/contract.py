"""orchctl normalized export contract.

Defines the schema for the per-area export written to
  .workspace/orchestrate/export/{area}/current.json

This file is the single source of truth for the export format.
Tracker-side adapters and orchctl producers both import from here.

Schema version history:
  v1 - initial release: schema_version, generated_at, area, issues[],
       batches[], active_workers[], diagnostics[]
"""

from __future__ import annotations

# Export schema version bumped when breaking fields are added or removed.
EXPORT_SCHEMA_VERSION = "v1"

# Default output path template (relative to monorepo root).
# {area} is substituted by the exporter.
EXPORT_PATH_TEMPLATE = ".workspace/orchestrate/export/{area}/current.json"

# ---------------------------------------------------------------------------
# Required top-level fields
# ---------------------------------------------------------------------------

EXPORT_TOP_LEVEL_FIELDS: frozenset[str] = frozenset({
    "schema_version",
    "generated_at",
    "area",
    "issues",
    "batches",
    "active_workers",
    "diagnostics",
})

# ---------------------------------------------------------------------------
# Required per-item fields
# ---------------------------------------------------------------------------

EXPORT_ISSUE_FIELDS: frozenset[str] = frozenset({
    "number",
    "area",
    "state",
    "dependency_type",
    "attempt_id",
    "pid",
    "started_at",
    "liveness",
})

EXPORT_BATCH_FIELDS: frozenset[str] = frozenset({
    "area",
    "n_total",
    "n_done",
    "n_failed",
    "n_pending",
    "n_dispatched",
    "started_at",
})

EXPORT_WORKER_FIELDS: frozenset[str] = frozenset({
    "attempt_id",
    "issue_number",
    "area",
    "pid",
    "alive",
    "started_at",
})

# ---------------------------------------------------------------------------
# Liveness values for exported issues/workers
# ---------------------------------------------------------------------------

LIVENESS_ALIVE = "alive"
LIVENESS_DEAD = "dead"
LIVENESS_UNKNOWN = "unknown"

VALID_LIVENESS: frozenset[str] = frozenset({
    LIVENESS_ALIVE,
    LIVENESS_DEAD,
    LIVENESS_UNKNOWN,
})

# ---------------------------------------------------------------------------
# Issue state values (mirrors orchctl.models.IssueState)
# Duplicated here so the tracker contract module has no orchctl dependency.
# ---------------------------------------------------------------------------

ISSUE_STATES: frozenset[str] = frozenset({
    "pending",
    "dispatched",
    "completed",
    "failed-terminal",
    "needs-human",
    "blocked-external",
    "cancelled",
    "blocked",
    "blocked-failed-dependency",
})

ACTIVE_ISSUE_STATES: frozenset[str] = frozenset({
    "pending",
    "dispatched",
    "blocked",
    "blocked-external",
})

TERMINAL_ISSUE_STATES: frozenset[str] = frozenset({
    "completed",
    "failed-terminal",
    "needs-human",
    "blocked-failed-dependency",
    "cancelled",
})


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class ExportValidationError(ValueError):
    """Raised when an export document fails schema validation."""


def validate_export(data: dict) -> None:
    """Validate that *data* conforms to the v1 export schema.

    Raises ExportValidationError describing all violations found.
    The check is intentionally lenient on extra fields (forward-compatibility).
    """
    errors: list[str] = []

    # Top-level
    missing_top = EXPORT_TOP_LEVEL_FIELDS - data.keys()
    if missing_top:
        errors.append(f"missing top-level fields: {sorted(missing_top)}")

    schema_ver = data.get("schema_version")
    if schema_ver != EXPORT_SCHEMA_VERSION:
        errors.append(
            f"schema_version must be '{EXPORT_SCHEMA_VERSION}', got {schema_ver!r}"
        )

    area = data.get("area")
    if not isinstance(area, str) or not area:
        errors.append("'area' must be a non-empty string")

    if not isinstance(data.get("generated_at"), (int, float)):
        errors.append("'generated_at' must be a number (Unix timestamp)")

    # issues[]
    for i, issue in enumerate(data.get("issues") or []):
        missing = EXPORT_ISSUE_FIELDS - issue.keys()
        if missing:
            errors.append(f"issues[{i}] missing fields: {sorted(missing)}")
        liveness = issue.get("liveness")
        if liveness not in VALID_LIVENESS:
            errors.append(
                f"issues[{i}].liveness must be one of {sorted(VALID_LIVENESS)},"
                f" got {liveness!r}"
            )

    # batches[]
    for i, batch in enumerate(data.get("batches") or []):
        missing = EXPORT_BATCH_FIELDS - batch.keys()
        if missing:
            errors.append(f"batches[{i}] missing fields: {sorted(missing)}")

    # active_workers[]
    for i, worker in enumerate(data.get("active_workers") or []):
        missing = EXPORT_WORKER_FIELDS - worker.keys()
        if missing:
            errors.append(f"active_workers[{i}] missing fields: {sorted(missing)}")

    if errors:
        raise ExportValidationError("; ".join(errors))
