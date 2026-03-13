"""Agent-tracker shared contract module.

Contains only: enums, JSON schema definitions, and export field names.
No business logic.
"""

from enum import Enum


class AgentStatus(str, Enum):
    IDLE = "idle"
    WORKING = "working"
    PLAN = "plan"
    NEEDS_INPUT = "needs-input"
    DONE = "done"
    ERROR = "error"
    STALE = "stale"
    FAULT = "fault"
    UNKNOWN = "unknown"


class TokenSource(str, Enum):
    SIDECAR = "sidecar"
    SCRAPING = "scraping"
    SESSION = "session"
    UNKNOWN = "unknown"


class BatchStatus(str, Enum):
    ACTIVE = "active"
    DONE = "done"
    DEAD = "dead"


class Engine(str, Enum):
    CLAUDE = "claude"
    CODEX = "codex"


class ProvenanceSource(str, Enum):
    SIDECAR_V2 = "sidecar_v2"
    SCRAPING = "scraping"
    SESSION_JSONL = "session_jsonl"
    UNKNOWN = "unknown"


# Export schema version
EXPORT_SCHEMA_VERSION = "v1"

# Required top-level fields in the normalized export
EXPORT_FIELDS = frozenset({
    "schema_version",
    "generated_at",
    "agents",
    "orchestrators",
    "diagnostics",
    "sources",
})

# Required agent fields
AGENT_FIELDS = frozenset({
    "pane_id",
    "pane_addr",
    "engine",
    "model",
    "status",
    "tokens",
    "task",
    "activity",
    "liveness",
    "freshness",
    "provenance",
})

# Required token fields
TOKEN_FIELDS = frozenset({
    "used",
    "total",
    "pct",
    "source",
    "fresh",
})

# Status staleness threshold in seconds
STALE_THRESHOLD_SECS = 30

# ---------------------------------------------------------------------------
# orchctl normalized export contract (tracker-side view)
# Full contract lives in tools/orchctl/orchctl/contract.py.
# These constants let the tracker validate exports it receives without
# importing from the orchctl package.
# ---------------------------------------------------------------------------

# Schema version produced by orchctl export (must match orchctl.contract)
ORCHCTL_EXPORT_SCHEMA_VERSION = "v1"

# Default export directory relative to monorepo root
ORCHCTL_EXPORT_DIR = ".workspace/orchestrate/export"

# Required top-level fields in the orchctl per-area export
ORCHCTL_EXPORT_TOP_FIELDS: frozenset[str] = frozenset({
    "schema_version",
    "generated_at",
    "area",
    "issues",
    "batches",
    "active_workers",
    "diagnostics",
})
