"""Exporter - generates normalized current.json with atomic write."""

from __future__ import annotations

import json
from pathlib import Path

from .adapters.file_adapter import atomic_write
from .collector import collect
from .models import Snapshot


def export(snapshot: Snapshot, output_path: str | Path) -> None:
    """Write snapshot to output_path atomically as JSON."""
    data = json.dumps(snapshot.to_dict(), indent=2, ensure_ascii=False)
    atomic_write(output_path, data)


def run_once(
    session: str,
    sidecar_dir: str | Path,
    orch_dir: str | Path,
    pipeline_dir: str | Path,
    output_path: str | Path,
) -> Snapshot:
    """Collect a snapshot and export it. Returns the snapshot."""
    snap = collect(session, sidecar_dir, orch_dir, pipeline_dir)
    export(snap, output_path)
    return snap
