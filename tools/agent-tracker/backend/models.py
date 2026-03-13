"""Normalized domain model for agent-tracker.

Collection and rendering are fully separated - this module contains
only the data model, not collection or rendering logic.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from .contract import (
    AgentStatus,
    BatchStatus,  # noqa: F401 - exported for type annotations
    Engine,
    EXPORT_SCHEMA_VERSION,
    ProvenanceSource,
    STALE_THRESHOLD_SECS,
    TokenSource,
)


@dataclass
class TokenState:
    used: int = 0
    total: int = 0
    pct: int = 0
    source: str = TokenSource.UNKNOWN
    fresh: bool = True

    def to_dict(self) -> dict:
        return {
            "used": self.used,
            "total": self.total,
            "pct": self.pct,
            "source": self.source,
            "fresh": self.fresh,
        }


@dataclass
class Liveness:
    """Process liveness and identity information."""
    is_alive: bool = False
    pid: int | None = None
    create_time: float | None = None

    def to_dict(self) -> dict:
        return {
            "is_alive": self.is_alive,
            "pid": self.pid,
            "create_time": self.create_time,
        }


@dataclass
class Freshness:
    """Data freshness relative to a staleness threshold."""
    is_fresh: bool = True
    age_secs: int | None = None
    threshold_secs: int = STALE_THRESHOLD_SECS

    def to_dict(self) -> dict:
        return {
            "is_fresh": self.is_fresh,
            "age_secs": self.age_secs,
            "threshold_secs": self.threshold_secs,
        }


@dataclass
class Provenance:
    """Where and how an agent record was collected."""
    source: str = ProvenanceSource.UNKNOWN
    path: str | None = None
    collected_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "path": self.path,
            "collected_at": self.collected_at,
        }


@dataclass
class AgentState:
    pane_id: str
    pane_addr: str
    engine: str
    model: str = "unknown"
    status: str = AgentStatus.IDLE
    tokens: TokenState = field(default_factory=TokenState)
    task: str = "-"
    activity: str | None = None
    liveness: Liveness = field(default_factory=Liveness)
    freshness: Freshness = field(default_factory=Freshness)
    provenance: Provenance = field(default_factory=Provenance)

    def to_dict(self) -> dict:
        return {
            "pane_id": self.pane_id,
            "pane_addr": self.pane_addr,
            "engine": self.engine,
            "model": self.model,
            "status": self.status,
            "tokens": self.tokens.to_dict(),
            "task": self.task,
            "activity": self.activity,
            "liveness": self.liveness.to_dict(),
            "freshness": self.freshness.to_dict(),
            "provenance": self.provenance.to_dict(),
        }


@dataclass
class DispatchedIssue:
    issue: str
    alive: bool
    step: str = "-"
    pr_num: int = 0
    elapsed: str = ""

    def to_dict(self) -> dict:
        return {
            "issue": self.issue,
            "alive": self.alive,
            "step": self.step,
            "pr_num": self.pr_num,
            "elapsed": self.elapsed,
        }


@dataclass
class BatchState:
    area: str
    batch_id: str
    batch_status: BatchStatus
    n_done: int = 0
    n_failed: int = 0
    n_total: int = 0
    created_at: str = ""
    elapsed: str = ""
    dispatched: list[DispatchedIssue] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "area": self.area,
            "batch_id": self.batch_id,
            "batch_status": self.batch_status,
            "n_done": self.n_done,
            "n_failed": self.n_failed,
            "n_total": self.n_total,
            "created_at": self.created_at,
            "elapsed": self.elapsed,
            "dispatched": [d.to_dict() for d in self.dispatched],
        }


@dataclass
class SourceInfo:
    """Describes a data source used during collection."""
    type: str
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"type": self.type, "details": self.details}


@dataclass
class Snapshot:
    schema_version: str = EXPORT_SCHEMA_VERSION
    generated_at: float = field(default_factory=time.time)
    agents: list[AgentState] = field(default_factory=list)
    orchestrators: list[BatchState] = field(default_factory=list)
    diagnostics: list[dict] = field(default_factory=list)
    sources: list[SourceInfo] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at,
            "agents": [a.to_dict() for a in self.agents],
            "orchestrators": [o.to_dict() for o in self.orchestrators],
            "diagnostics": self.diagnostics,
            "sources": [s.to_dict() for s in self.sources],
        }
