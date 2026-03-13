"""File adapter - Python stdlib (pathlib, os, json).

Responsibility: file I/O only.
No business logic, no subprocess calls.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


def read_json(path: str | Path) -> dict | None:
    """Read and parse a JSON file. Returns None on any error."""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def list_sidecar_files(
    sidecar_dir: str | Path,
    socket_hash: str,
    session: str,
) -> list[Path]:
    """List all sidecar JSON files for the given socket hash and session.

    Sidecar v2 namespace: <sidecar_dir>/<socket-hash>/<session>/<pane>.json
    """
    base = Path(sidecar_dir) / socket_hash / session
    if not base.is_dir():
        return []
    return sorted(f for f in base.glob("*.json") if not f.name.endswith(".lock"))


def list_batch_files(orch_dir: str | Path) -> list[Path]:
    """List all batch.state.json files under the orchestrator directory."""
    orch = Path(orch_dir)
    if not orch.is_dir():
        return []
    return sorted(orch.glob("*/batch.state.json"))


def read_pipeline_state(
    pipeline_dir: str | Path,
    area: str,
    issue: str,
) -> dict | None:
    """Read pipeline state for a specific area/issue."""
    path = Path(pipeline_dir) / area / f"issue-{issue}.state.json"
    return read_json(path)


def atomic_write(path: str | Path, data: str | bytes) -> None:
    """Atomically write data to path using tmp + rename.

    Creates parent directories as needed.
    Guarantees that readers never see a partial write.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    mode = "w" if isinstance(data, str) else "wb"
    encoding = "utf-8" if mode == "w" else None
    fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, mode, encoding=encoding) as f:
            f.write(data)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
