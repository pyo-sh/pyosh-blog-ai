"""Tests for file_adapter: read_json, atomic_write, list_* helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.adapters.file_adapter import (
    atomic_write,
    list_batch_files,
    list_sidecar_files,
    read_json,
    read_pipeline_state,
)


class TestReadJson:
    def test_normal(self, tmp_path: Path) -> None:
        f = tmp_path / "ok.json"
        f.write_text('{"key": "value"}')
        assert read_json(f) == {"key": "value"}

    def test_missing_file(self, tmp_path: Path) -> None:
        assert read_json(tmp_path / "missing.json") is None

    def test_partial_write(self, tmp_path: Path) -> None:
        """Truncated JSON (partial write mid-object) → None, not an exception."""
        f = tmp_path / "partial.json"
        f.write_text('{"status": "working", "model":')
        assert read_json(f) is None

    def test_zero_bytes(self, tmp_path: Path) -> None:
        """Empty file → None."""
        f = tmp_path / "zero.json"
        f.write_bytes(b"")
        assert read_json(f) is None

    def test_not_json(self, tmp_path: Path) -> None:
        f = tmp_path / "corrupt.json"
        f.write_text("not json at all")
        assert read_json(f) is None

    def test_binary_garbage(self, tmp_path: Path) -> None:
        f = tmp_path / "garbage.json"
        f.write_bytes(b"\x00\x01\xff\xfe{bad")
        assert read_json(f) is None

    def test_valid_nested(self, tmp_path: Path) -> None:
        data = {"tokens": {"used": 90000, "max": 200000, "pct": 45}}
        f = tmp_path / "nested.json"
        f.write_text(json.dumps(data))
        assert read_json(f) == data


class TestAtomicWrite:
    def test_creates_file(self, tmp_path: Path) -> None:
        p = tmp_path / "out.json"
        atomic_write(p, '{"a": 1}')
        assert p.exists()
        assert p.read_text() == '{"a": 1}'

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        p = tmp_path / "deep" / "nested" / "file.json"
        atomic_write(p, "{}")
        assert p.exists()

    def test_overwrites_existing(self, tmp_path: Path) -> None:
        p = tmp_path / "out.json"
        p.write_text("old")
        atomic_write(p, "new")
        assert p.read_text() == "new"

    def test_bytes_mode(self, tmp_path: Path) -> None:
        p = tmp_path / "binary.json"
        atomic_write(p, b'{"b": 2}')
        assert p.read_bytes() == b'{"b": 2}'

    def test_no_tmp_file_left_on_success(self, tmp_path: Path) -> None:
        p = tmp_path / "clean.json"
        atomic_write(p, "{}")
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert tmp_files == [], f"stray tmp files: {tmp_files}"


class TestListSidecarFiles:
    def test_lists_json_only(self, tmp_path: Path) -> None:
        base = tmp_path / "abc123" / "lab"
        base.mkdir(parents=True)
        (base / "0.json").write_text("{}")
        (base / "1.json").write_text("{}")
        (base / "0.lock").write_text("")  # lock file must be excluded

        files = list_sidecar_files(tmp_path, "abc123", "lab")
        names = {f.name for f in files}
        assert names == {"0.json", "1.json"}

    def test_missing_dir(self, tmp_path: Path) -> None:
        assert list_sidecar_files(tmp_path, "nohash", "nosess") == []

    def test_empty_dir(self, tmp_path: Path) -> None:
        base = tmp_path / "hhh" / "sess"
        base.mkdir(parents=True)
        assert list_sidecar_files(tmp_path, "hhh", "sess") == []

    def test_sorted(self, tmp_path: Path) -> None:
        base = tmp_path / "h" / "s"
        base.mkdir(parents=True)
        (base / "10.json").write_text("{}")
        (base / "2.json").write_text("{}")
        (base / "1.json").write_text("{}")
        files = list_sidecar_files(tmp_path, "h", "s")
        names = [f.name for f in files]
        assert names == sorted(names)


class TestListBatchFiles:
    def test_finds_batch_files(self, tmp_path: Path) -> None:
        for batch in ("batch1", "batch2"):
            d = tmp_path / batch
            d.mkdir()
            (d / "batch.state.json").write_text("{}")

        files = list_batch_files(tmp_path)
        assert len(files) == 2

    def test_missing_dir(self, tmp_path: Path) -> None:
        assert list_batch_files(tmp_path / "nonexistent") == []

    def test_empty_dir(self, tmp_path: Path) -> None:
        assert list_batch_files(tmp_path) == []

    def test_ignores_non_batch_files(self, tmp_path: Path) -> None:
        d = tmp_path / "batch1"
        d.mkdir()
        (d / "other.json").write_text("{}")
        # No batch.state.json
        assert list_batch_files(tmp_path) == []


class TestReadPipelineState:
    def test_normal(self, tmp_path: Path) -> None:
        area_dir = tmp_path / "workspace"
        area_dir.mkdir()
        state = {"step": "review", "pr": 15}
        (area_dir / "issue-42.state.json").write_text(json.dumps(state))

        result = read_pipeline_state(tmp_path, "workspace", "42")
        assert result == state

    def test_missing(self, tmp_path: Path) -> None:
        assert read_pipeline_state(tmp_path, "workspace", "999") is None

    def test_corrupt(self, tmp_path: Path) -> None:
        area_dir = tmp_path / "server"
        area_dir.mkdir()
        (area_dir / "issue-1.state.json").write_text("{corrupt")
        assert read_pipeline_state(tmp_path, "server", "1") is None
