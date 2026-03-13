"""Shared fixtures for agent-tracker backend tests."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest


@pytest.fixture
def sidecar_dir(tmp_path: Path) -> Path:
    d = tmp_path / "sidecar"
    d.mkdir()
    return d


@pytest.fixture
def orch_dir(tmp_path: Path) -> Path:
    d = tmp_path / "orchestrate"
    d.mkdir()
    return d


@pytest.fixture
def pipeline_dir(tmp_path: Path) -> Path:
    d = tmp_path / "pipeline"
    d.mkdir()
    return d


@pytest.fixture
def mock_sidecar(tmp_path: Path):
    """Factory that writes a sidecar JSON file and returns its path."""

    def _make(
        sock_hash: str = "abc123",
        session: str = "lab",
        pane_num: int = 0,
        data: dict | None = None,
    ) -> Path:
        sidecar_root = tmp_path / "sidecar"
        path = sidecar_root / sock_hash / session / f"{pane_num}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = data if data is not None else {
            "model": "Sonnet 4.6",
            "status": "working",
            "task": "Test task",
            "tokens": {"used": 50000, "max": 200000, "pct": 25},
            "updated_at": time.time(),
            "tokens_updated_at": time.time(),
        }
        path.write_text(json.dumps(payload), encoding="utf-8")
        return sidecar_root

    return _make


@pytest.fixture
def mock_batch(tmp_path: Path):
    """Factory that writes a batch.state.json file and returns the orch_dir."""

    def _make(data: dict) -> Path:
        orch = tmp_path / "orchestrate"
        batch_dir = orch / data.get("batchId", "test-batch")
        batch_dir.mkdir(parents=True, exist_ok=True)
        (batch_dir / "batch.state.json").write_text(json.dumps(data), encoding="utf-8")
        return orch

    return _make
