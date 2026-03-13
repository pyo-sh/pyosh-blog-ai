"""Collection layer - reads sidecar v2, tmux panes, and orchestrator state.

Produces a Snapshot with fully separated collection and rendering.
"""

from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from pathlib import Path

from .contract import (
    AgentStatus,
    Engine,
    ProvenanceSource,
    STALE_THRESHOLD_SECS,
    TokenSource,
)
from .models import (
    AgentState,
    BatchState,
    DispatchedIssue,
    Freshness,
    Liveness,
    Provenance,
    Snapshot,
    SourceInfo,
    TokenState,
)
from .adapters import file_adapter, process_adapter, tmux_adapter


def collect(
    session: str,
    sidecar_dir: str | Path,
    orch_dir: str | Path,
    pipeline_dir: str | Path,
) -> Snapshot:
    """Collect a full snapshot from sidecar files and orchestrator state."""
    snap = Snapshot()
    sock_hash = tmux_adapter.socket_hash()

    agents, agent_source = _collect_agents(session, sidecar_dir, sock_hash)
    snap.agents = agents
    snap.sources.append(agent_source)

    orchestrators, orch_source = _collect_orchestrators(orch_dir, pipeline_dir)
    snap.orchestrators = orchestrators
    snap.sources.append(orch_source)

    return snap


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
    )

    if not sidecar_path.exists():
        state.provenance = Provenance(source=ProvenanceSource.SCRAPING, collected_at=now)
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
    state.status = data.get("status") or AgentStatus.IDLE
    state.task = _normalize_text(data.get("task") or "-")
    raw_activity = _normalize_text(data.get("activity") or "")
    state.activity = raw_activity if raw_activity else None

    # Tokens
    tokens_data = data.get("tokens") or {}
    tok_used = int(tokens_data.get("used") or 0)
    tok_total = int(tokens_data.get("max") or tokens_data.get("total") or 0)
    tok_pct = int(tokens_data.get("pct") or 0)
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
    )
    state.provenance = Provenance(source=ProvenanceSource.UNKNOWN, collected_at=now)
    return state


# ── Orchestrator collection ───────────────────────────────────────────────────

def _collect_orchestrators(
    orch_dir: str | Path,
    pipeline_dir: str | Path,
) -> tuple[list[BatchState], SourceInfo]:
    batch_files = file_adapter.list_batch_files(orch_dir)
    batches: list[BatchState] = []
    now = time.time()

    for batch_file in batch_files:
        data = file_adapter.read_json(batch_file)
        if not data:
            continue
        batch = _parse_batch(data, pipeline_dir, now)
        if batch is not None:
            batches.append(batch)

    source = SourceInfo(
        type="orchestrator",
        details={
            "orch_dir": str(orch_dir),
            "batch_files_found": len(batch_files),
            "batches_parsed": len(batches),
        },
    )
    return batches, source


def _parse_batch(
    data: dict,
    pipeline_dir: str | Path,
    now: float,
) -> BatchState | None:
    area = data.get("area") or ""
    batch_id = data.get("batchId") or ""
    if not area or not batch_id:
        return None

    status_map: dict[str, str] = data.get("status") or {}
    n_done = sum(1 for v in status_map.values() if v == "completed")
    n_failed = sum(1 for v in status_map.values() if v == "failed")
    n_total = len(data.get("issues") or [])

    orch_pid = int(data.get("orchestratorPid") or 0)
    orch_started_at = data.get("orchestratorStartedAt")
    created_at = data.get("createdAt") or ""

    # Liveness check via process adapter
    create_time = None
    if orch_pid and orch_started_at:
        create_time = process_adapter.get_create_time(orch_pid)
    batch_alive = process_adapter.is_running(orch_pid, create_time) if orch_pid else False

    liveness = Liveness(is_alive=batch_alive, pid=orch_pid or None, create_time=create_time)

    n_terminal = n_done + n_failed
    if not batch_alive:
        batch_status = "dead"
    elif n_total > 0 and n_terminal >= n_total:
        batch_status = "done"
    else:
        batch_status = "active"

    elapsed = _elapsed_from_iso(created_at, now)

    # Dispatched issues
    dispatched_raw: dict = data.get("dispatched") or {}
    dispatched: list[DispatchedIssue] = []

    for issue_key, dispatch_info in dispatched_raw.items():
        if status_map.get(issue_key) != "dispatched":
            continue

        pid = int(dispatch_info.get("pid") or 0)
        alive = process_adapter.is_running(pid) if pid else False

        ps = file_adapter.read_pipeline_state(pipeline_dir, area, issue_key)
        step = (ps.get("step") or "-") if ps else "-"
        pr_num = int((ps.get("pr") or 0)) if ps else 0

        issue_elapsed = _elapsed_from_iso(dispatch_info.get("dispatchedAt") or "", now)

        dispatched.append(DispatchedIssue(
            issue=issue_key,
            alive=alive,
            step=step,
            pr_num=pr_num,
            elapsed=issue_elapsed,
        ))

    return BatchState(
        area=area,
        batch_id=batch_id,
        batch_status=batch_status,
        n_done=n_done,
        n_failed=n_failed,
        n_total=n_total,
        created_at=created_at,
        elapsed=elapsed,
        dispatched=dispatched,
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

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
