"""Collection layer - reads sidecar v2, tmux panes, and orchestrator state.

Produces a Snapshot with fully separated collection and rendering.
"""

from __future__ import annotations

import re
import time
from datetime import datetime
from pathlib import Path

from .contract import (
    AgentStatus,
    Engine,
    ORCHCTL_EXPORT_DIR,
    ProvenanceSource,
    STALE_THRESHOLD_SECS,
    TokenSource,
)
from .models import (
    AgentState,
    BatchState,
    Freshness,
    Liveness,
    Provenance,
    Snapshot,
    SourceInfo,
    TokenState,
)
from .adapters import file_adapter, tmux_adapter
from .adapters.orchctl_adapter import load_exports


def collect(
    session: str,
    sidecar_dir: str | Path,
    orch_dir: str | Path,
    pipeline_dir: str | Path,
    export_dir: str | Path | None = None,
) -> Snapshot:
    """Collect a full snapshot from sidecar files and orchestrator state.

    *export_dir* is the directory containing per-area orchctl export files
    (``<export_dir>/<area>/current.json``).  Defaults to
    ``ORCHCTL_EXPORT_DIR`` relative to the monorepo root (auto-detected via
    ``.agents/``).  The adapter falls back to the built-in fixture when no
    export files are found.
    """
    snap = Snapshot()
    sock_hash = tmux_adapter.socket_hash()

    agents, agent_source = _collect_agents(session, sidecar_dir, sock_hash)
    snap.agents = agents
    snap.sources.append(agent_source)

    resolved_export_dir = _resolve_export_dir(export_dir, orch_dir)
    orchestrators, orch_source = _collect_orchestrators(resolved_export_dir, pipeline_dir)
    snap.orchestrators = orchestrators
    snap.sources.append(orch_source)

    return snap


def _resolve_export_dir(
    export_dir: str | Path | None,
    orch_dir: str | Path,
) -> Path:
    """Return the export directory to use.

    Priority:
    1. Explicit *export_dir* argument.
    2. ``ORCHCTL_EXPORT_DIR`` relative to the monorepo root (found by walking
       up from *orch_dir* looking for a ``.agents/`` directory).
    3. ``export/`` sibling of *orch_dir* as a last-resort fallback.
    """
    if export_dir is not None:
        return Path(export_dir)
    # Walk up to find monorepo root
    for parent in Path(orch_dir).resolve().parents:
        if (parent / ".agents").is_dir():
            return parent / ORCHCTL_EXPORT_DIR
    # Fallback: export/ next to orch_dir
    return Path(orch_dir).parent / "export"


# ── Agent collection ──────────────────────────────────────────────────────────

def _collect_agents(
    session: str,
    sidecar_dir: str | Path,
    sock_hash: str,
) -> tuple[list[AgentState], SourceInfo]:
    agents: list[AgentState] = []
    sidecar_files_found = 0

    panes = tmux_adapter.list_panes(session)

    for pane in panes:
        engine = _detect_engine(pane)
        if engine is None:
            continue

        if engine == Engine.CLAUDE:
            agent = _collect_claude_pane(pane, sidecar_dir, sock_hash, session)
        else:
            agent = _collect_codex_pane(pane)

        if agent is not None:
            if agent.provenance.source == ProvenanceSource.SIDECAR_V2:
                sidecar_files_found += 1
            agents.append(agent)

    source = SourceInfo(
        type="sidecar_v2",
        details={
            "sidecar_dir": str(sidecar_dir),
            "socket_hash": sock_hash,
            "session": session,
            "panes_scanned": len(panes),
            "agents_found": len(agents),
            "sidecar_files_found": sidecar_files_found,
        },
    )
    return agents, source


def _detect_engine(pane: tmux_adapter.PaneInfo) -> str | None:
    if pane.command == "claude":
        return Engine.CLAUDE
    if pane.command == "codex":
        return Engine.CODEX
    return None


def _collect_claude_pane(
    pane: tmux_adapter.PaneInfo,
    sidecar_dir: str | Path,
    sock_hash: str,
    session: str,
) -> AgentState | None:
    pane_file = pane.pane_id.lstrip("%")
    # Path traversal guard: pane file must be digits only
    if not re.match(r"^\d+$", pane_file):
        return None

    sidecar_path = Path(sidecar_dir) / sock_hash / session / f"{pane_file}.json"
    now = time.time()

    state = AgentState(
        pane_id=pane.pane_id,
        pane_addr=f"{pane.addr} {pane.pane_id}",
        engine=Engine.CLAUDE,
        # Pane is confirmed alive by tmux list-panes returning it.
        liveness=Liveness(is_alive=True),
    )

    if not sidecar_path.exists():
        # No sidecar yet (hooks not installed, pane just started, or sidecar cleaned up).
        # No pane scraping is performed here, so provenance is UNKNOWN.
        state.provenance = Provenance(source=ProvenanceSource.UNKNOWN, collected_at=now)
        return state

    data = file_adapter.read_json(sidecar_path)
    if data is None:
        state.status = AgentStatus.FAULT
        state.provenance = Provenance(
            source=ProvenanceSource.SIDECAR_V2,
            path=str(sidecar_path),
            collected_at=now,
        )
        return state

    state.model = data.get("model") or "unknown"
    _status_values = {s.value: s for s in AgentStatus}
    raw_status = data.get("status") or ""
    state.status = _status_values.get(raw_status, AgentStatus.UNKNOWN) if raw_status else AgentStatus.IDLE
    state.task = _normalize_text(data.get("task") or "-")
    raw_activity = _normalize_text(data.get("activity") or "")
    state.activity = raw_activity if raw_activity else None

    # Tokens
    tokens_data = data.get("tokens") or {}
    tok_used = _safe_int(tokens_data.get("used"))
    tok_total = _safe_int(tokens_data.get("max") or tokens_data.get("total"))
    tok_pct = _safe_int(tokens_data.get("pct"))
    tok_source = TokenSource.SIDECAR if (tok_used > 0 or tok_total > 0) else TokenSource.UNKNOWN

    # Token freshness: prefer tokens_updated_at, fall back to updated_at
    updated_at = float(data.get("updated_at") or 0)
    tokens_updated_at = float(data.get("tokens_updated_at") or 0)
    tok_ts = tokens_updated_at if tokens_updated_at > 0 else updated_at
    tok_age = int(now - tok_ts) if tok_ts > 0 else None
    tok_fresh = tok_age is None or tok_age <= STALE_THRESHOLD_SECS

    state.tokens = TokenState(
        used=tok_used,
        total=tok_total,
        pct=tok_pct,
        source=tok_source,
        fresh=tok_fresh,
    )

    # Status staleness: non-idle/non-done without recent update
    if state.status not in (AgentStatus.IDLE, AgentStatus.DONE) and updated_at > 0:
        age = int(now - updated_at)
        if age > STALE_THRESHOLD_SECS:
            state.status = AgentStatus.STALE
            state.activity = None

    # Done prefix detection (set by on-status.sh Stop hook)
    if state.task.startswith("(Done) "):
        state.status = AgentStatus.DONE

    # Data freshness
    data_age = int(now - updated_at) if updated_at > 0 else None
    state.freshness = Freshness(
        is_fresh=data_age is None or data_age <= STALE_THRESHOLD_SECS,
        age_secs=data_age,
    )

    state.provenance = Provenance(
        source=ProvenanceSource.SIDECAR_V2,
        path=str(sidecar_path),
        collected_at=now,
    )
    return state


def _collect_codex_pane(pane: tmux_adapter.PaneInfo) -> AgentState:
    now = time.time()
    state = AgentState(
        pane_id=pane.pane_id,
        pane_addr=f"{pane.addr} {pane.pane_id}",
        engine=Engine.CODEX,
        model="Codex",
        # No sidecar for Codex; status cannot be determined without session JSONL parsing.
        status=AgentStatus.UNKNOWN,
        liveness=Liveness(is_alive=True),
    )
    state.provenance = Provenance(source=ProvenanceSource.UNKNOWN, collected_at=now)
    return state


# ── Orchestrator collection ───────────────────────────────────────────────────

def _collect_orchestrators(
    export_dir: str | Path,
    pipeline_dir: str | Path,
) -> tuple[list[BatchState], SourceInfo]:
    """Collect orchestrator state from the orchctl normalized export.

    Reads per-area `current.json` files under *export_dir*.  Falls back to
    the built-in fixture when no export files are found, so the tracker
    always has data to display during development.

    Legacy batch.state.json files are not read here; the orchctl export is
    the sole orchestrator data source in production.
    """
    export_dir = Path(export_dir)
    batches = load_exports(export_dir, pipeline_dir)

    source = SourceInfo(
        type="orchctl_export",
        details={
            "export_dir": str(export_dir),
            "batches_loaded": len(batches),
        },
    )
    return batches, source


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe_int(v: object, default: int = 0) -> int:
    """Cast v to int, returning default on None or conversion error.

    Uses explicit None check so that a valid stored value of 0 is preserved.
    """
    if v is None:
        return default
    try:
        return int(v)
    except (ValueError, TypeError):
        return default


def _normalize_text(s: str) -> str:
    if not s:
        return ""
    return " ".join(s.replace("\n", " ").replace("\t", " ").replace("\r", " ").split())


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
