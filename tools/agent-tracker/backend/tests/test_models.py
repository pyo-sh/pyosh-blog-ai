"""Tests for the normalized domain model: serialization and schema contract."""

from __future__ import annotations

import time

import pytest

from backend.contract import (
    AGENT_FIELDS,
    EXPORT_FIELDS,
    EXPORT_SCHEMA_VERSION,
    TOKEN_FIELDS,
    AgentStatus,
    BatchStatus,
    Engine,
    TokenSource,
)
from backend.models import (
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


class TestSnapshotSchema:
    def test_all_export_fields_present(self) -> None:
        snap = Snapshot()
        d = snap.to_dict()
        assert EXPORT_FIELDS.issubset(set(d.keys())), (
            f"Missing fields: {EXPORT_FIELDS - set(d.keys())}"
        )

    def test_schema_version(self) -> None:
        snap = Snapshot()
        assert snap.to_dict()["schema_version"] == EXPORT_SCHEMA_VERSION

    def test_generated_at_is_float(self) -> None:
        snap = Snapshot()
        d = snap.to_dict()
        assert isinstance(d["generated_at"], float)
        assert d["generated_at"] > 0

    def test_empty_lists(self) -> None:
        snap = Snapshot()
        d = snap.to_dict()
        assert d["agents"] == []
        assert d["orchestrators"] == []
        assert d["diagnostics"] == []
        assert d["sources"] == []


class TestAgentStateSchema:
    def test_all_agent_fields_present(self) -> None:
        state = AgentState(pane_id="%0", pane_addr="0:0 %0", engine=Engine.CLAUDE)
        d = state.to_dict()
        assert AGENT_FIELDS.issubset(set(d.keys())), (
            f"Missing agent fields: {AGENT_FIELDS - set(d.keys())}"
        )

    def test_all_token_fields_present(self) -> None:
        state = AgentState(pane_id="%0", pane_addr="0:0 %0", engine=Engine.CLAUDE)
        token_dict = state.to_dict()["tokens"]
        assert TOKEN_FIELDS.issubset(set(token_dict.keys())), (
            f"Missing token fields: {TOKEN_FIELDS - set(token_dict.keys())}"
        )

    def test_default_status_is_idle(self) -> None:
        state = AgentState(pane_id="%0", pane_addr="0:0 %0", engine=Engine.CLAUDE)
        assert state.status == AgentStatus.IDLE

    def test_default_tokens_fresh(self) -> None:
        state = AgentState(pane_id="%0", pane_addr="0:0 %0", engine=Engine.CLAUDE)
        assert state.tokens.fresh is True
        assert state.tokens.used == 0


class TestTokenState:
    def test_to_dict(self) -> None:
        t = TokenState(used=90000, total=200000, pct=45, source=TokenSource.SIDECAR, fresh=True)
        d = t.to_dict()
        assert d["used"] == 90000
        assert d["total"] == 200000
        assert d["pct"] == 45
        assert d["source"] == TokenSource.SIDECAR
        assert d["fresh"] is True

    def test_defaults(self) -> None:
        t = TokenState()
        assert t.used == 0
        assert t.total == 0
        assert t.pct == 0
        assert t.source == TokenSource.UNKNOWN
        assert t.fresh is True


class TestBatchStateSerialization:
    def test_to_dict_structure(self) -> None:
        batch = BatchState(
            area="workspace",
            batch_id="20260313-abc",
            batch_status=BatchStatus.ACTIVE,
            n_done=1,
            n_failed=0,
            n_total=3,
            created_at="2026-03-13T09:00:00Z",
            elapsed="1h00m",
        )
        d = batch.to_dict()
        assert d["area"] == "workspace"
        assert d["batch_status"] == BatchStatus.ACTIVE
        assert d["n_done"] == 1
        assert d["n_total"] == 3
        assert d["dispatched"] == []

    def test_dead_status_serialized(self) -> None:
        batch = BatchState(
            area="server",
            batch_id="test",
            batch_status=BatchStatus.DEAD,
        )
        d = batch.to_dict()
        assert d["batch_status"] == BatchStatus.DEAD


class TestDispatchedIssueSerialization:
    def test_to_dict(self) -> None:
        d = DispatchedIssue(issue="42", alive=True, step="review", pr_num=15, elapsed="5m30s")
        result = d.to_dict()
        assert result["issue"] == "42"
        assert result["alive"] is True
        assert result["step"] == "review"
        assert result["pr_num"] == 15
        assert result["elapsed"] == "5m30s"


class TestSnapshotWithData:
    def test_agents_serialized(self) -> None:
        snap = Snapshot()
        snap.agents.append(
            AgentState(pane_id="%0", pane_addr="0:0 %0", engine=Engine.CLAUDE)
        )
        d = snap.to_dict()
        assert len(d["agents"]) == 1
        assert d["agents"][0]["engine"] == Engine.CLAUDE

    def test_sources_serialized(self) -> None:
        snap = Snapshot()
        snap.sources.append(SourceInfo(type="sidecar_v2", details={"count": 2}))
        d = snap.to_dict()
        assert len(d["sources"]) == 1
        assert d["sources"][0]["type"] == "sidecar_v2"
