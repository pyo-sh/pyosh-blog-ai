"""Tests for the collection layer: helper functions and pane/batch collection.

tmux calls are mocked throughout — tests run without a real tmux session.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from backend.adapters.tmux_adapter import PaneInfo
from backend.collector import (
    _collect_claude_pane,
    _format_elapsed,
    _normalize_text,
    _parse_batch,
    _safe_int,
)
from backend.contract import AgentStatus, BatchStatus, TokenSource


# ── Pure helpers ───────────────────────────────────────────────────────────────

class TestNormalizeText:
    def test_newlines_replaced(self) -> None:
        assert _normalize_text("line1\nline2") == "line1 line2"

    def test_tabs_replaced(self) -> None:
        assert _normalize_text("col1\tcol2") == "col1 col2"

    def test_carriage_return_replaced(self) -> None:
        assert _normalize_text("a\rb") == "a b"

    def test_double_spaces_collapsed(self) -> None:
        assert _normalize_text("  two  spaces  ") == "two spaces"

    def test_empty_string(self) -> None:
        assert _normalize_text("") == ""

    def test_no_change_needed(self) -> None:
        assert _normalize_text("plain text") == "plain text"


class TestFormatElapsed:
    def test_seconds(self) -> None:
        assert _format_elapsed(45) == "45s"

    def test_zero(self) -> None:
        assert _format_elapsed(0) == "0s"

    def test_negative_treated_as_zero(self) -> None:
        assert _format_elapsed(-10) == "0s"

    def test_one_minute(self) -> None:
        assert _format_elapsed(60) == "1m00s"

    def test_minutes_and_seconds(self) -> None:
        assert _format_elapsed(90) == "1m30s"

    def test_one_hour(self) -> None:
        assert _format_elapsed(3600) == "1h00m"

    def test_hours_and_minutes(self) -> None:
        assert _format_elapsed(3661) == "1h01m"


class TestSafeInt:
    def test_int_value(self) -> None:
        assert _safe_int(42) == 42

    def test_none_returns_default(self) -> None:
        assert _safe_int(None) == 0

    def test_string_int(self) -> None:
        assert _safe_int("100") == 100

    def test_invalid_string(self) -> None:
        assert _safe_int("abc") == 0

    def test_zero_preserved(self) -> None:
        assert _safe_int(0) == 0

    def test_float_truncated(self) -> None:
        assert _safe_int(3.9) == 3


# ── Claude pane collection ─────────────────────────────────────────────────────

class TestCollectClaudePanePathTraversal:
    """Path traversal guard: non-numeric pane IDs must be rejected."""

    def test_traversal_pane_id(self, tmp_path: Path) -> None:
        pane = PaneInfo(addr="0:0", pane_id="%../../../etc", command="claude")
        state = _collect_claude_pane(pane, tmp_path, "abc123", "lab")
        assert state is None

    def test_empty_pane_id(self, tmp_path: Path) -> None:
        pane = PaneInfo(addr="0:0", pane_id="%", command="claude")
        state = _collect_claude_pane(pane, tmp_path, "abc123", "lab")
        assert state is None

    def test_shell_injection_pane_id(self, tmp_path: Path) -> None:
        pane = PaneInfo(addr="0:0", pane_id="%; rm -rf /", command="claude")
        state = _collect_claude_pane(pane, tmp_path, "abc123", "lab")
        assert state is None

    def test_valid_numeric_pane_id(self, tmp_path: Path) -> None:
        pane = PaneInfo(addr="0:0", pane_id="%0", command="claude")
        state = _collect_claude_pane(pane, tmp_path, "abc123", "lab")
        # No sidecar exists → state returned with unknown provenance, not None
        assert state is not None
        assert state.pane_id == "%0"


class TestCollectClaudePaneSidecarFault:
    """Partial/corrupt sidecar → status=fault."""

    def _write_sidecar(
        self, tmp_path: Path, pane_num: int, content: str, sock_hash: str = "abc123", session: str = "lab"
    ) -> Path:
        sidecar_dir = tmp_path / "sidecar"
        path = sidecar_dir / sock_hash / session / f"{pane_num}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return sidecar_dir

    def test_truncated_json(self, tmp_path: Path) -> None:
        sidecar_dir = self._write_sidecar(tmp_path, 1, '{"status": "working",')
        pane = PaneInfo(addr="0:0", pane_id="%1", command="claude")
        state = _collect_claude_pane(pane, sidecar_dir, "abc123", "lab")
        assert state is not None
        assert state.status == AgentStatus.FAULT

    def test_zero_byte_file(self, tmp_path: Path) -> None:
        sidecar_dir = self._write_sidecar(tmp_path, 2, "")
        pane = PaneInfo(addr="0:0", pane_id="%2", command="claude")
        state = _collect_claude_pane(pane, sidecar_dir, "abc123", "lab")
        assert state is not None
        assert state.status == AgentStatus.FAULT

    def test_not_json(self, tmp_path: Path) -> None:
        sidecar_dir = self._write_sidecar(tmp_path, 3, "not json")
        pane = PaneInfo(addr="0:0", pane_id="%3", command="claude")
        state = _collect_claude_pane(pane, sidecar_dir, "abc123", "lab")
        assert state is not None
        assert state.status == AgentStatus.FAULT


class TestCollectClaudePaneSidecarValid:
    """Valid sidecar → correct fields populated."""

    def _write_sidecar(
        self, tmp_path: Path, pane_num: int, data: dict, sock_hash: str = "abc123", session: str = "lab"
    ) -> Path:
        sidecar_dir = tmp_path / "sidecar"
        path = sidecar_dir / sock_hash / session / f"{pane_num}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data))
        return sidecar_dir

    def test_model_status_task(self, tmp_path: Path) -> None:
        now = time.time()
        sidecar_dir = self._write_sidecar(tmp_path, 0, {
            "model": "Sonnet 4.6",
            "status": "working",
            "task": "Fix the bug",
            "tokens": {"used": 90000, "max": 200000, "pct": 45},
            "updated_at": now,
            "tokens_updated_at": now,
        })
        pane = PaneInfo(addr="0:0", pane_id="%0", command="claude")
        state = _collect_claude_pane(pane, sidecar_dir, "abc123", "lab")

        assert state is not None
        assert state.model == "Sonnet 4.6"
        assert state.status == AgentStatus.WORKING
        assert state.task == "Fix the bug"
        assert state.tokens.used == 90000
        assert state.tokens.total == 200000
        assert state.tokens.source == TokenSource.SIDECAR

    def test_done_prefix_sets_status_done(self, tmp_path: Path) -> None:
        now = time.time()
        sidecar_dir = self._write_sidecar(tmp_path, 1, {
            "model": "Claude",
            "status": "working",
            "task": "(Done) Fix the parser",
            "tokens": {"used": 0, "max": 0, "pct": 0},
            "updated_at": now,
        })
        pane = PaneInfo(addr="0:0", pane_id="%1", command="claude")
        state = _collect_claude_pane(pane, sidecar_dir, "abc123", "lab")

        assert state is not None
        assert state.status == AgentStatus.DONE

    def test_multiline_task_normalized(self, tmp_path: Path) -> None:
        now = time.time()
        sidecar_dir = self._write_sidecar(tmp_path, 2, {
            "model": "Claude",
            "status": "working",
            "task": "Line one\nLine two\nLine three",
            "tokens": {"used": 0, "max": 0, "pct": 0},
            "updated_at": now,
        })
        pane = PaneInfo(addr="0:0", pane_id="%2", command="claude")
        state = _collect_claude_pane(pane, sidecar_dir, "abc123", "lab")

        assert state is not None
        assert state.task == "Line one Line two Line three"


class TestCollectClaudePaneStaleToken:
    """Token freshness: tokens_updated_at > 30s → tokens.fresh=False."""

    def _write_sidecar(
        self, tmp_path: Path, pane_num: int, data: dict, sock_hash: str = "def456", session: str = "lab"
    ) -> Path:
        sidecar_dir = tmp_path / "sidecar"
        path = sidecar_dir / sock_hash / session / f"{pane_num}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data))
        return sidecar_dir

    def test_stale_tokens_updated_at(self, tmp_path: Path) -> None:
        now = time.time()
        old_tok = now - 60  # 60s ago → stale
        sidecar_dir = self._write_sidecar(tmp_path, 0, {
            "model": "Claude",
            "status": "working",
            "task": "Active task",
            "tokens": {"used": 60000, "max": 200000, "pct": 30},
            "updated_at": now,           # recently updated
            "tokens_updated_at": old_tok,  # but tokens are stale
        })
        pane = PaneInfo(addr="0:0", pane_id="%0", command="claude")
        state = _collect_claude_pane(pane, sidecar_dir, "def456", "lab")

        assert state is not None
        assert state.tokens.fresh is False
        assert state.status == AgentStatus.WORKING  # status is NOT stale

    def test_fresh_tokens_updated_at(self, tmp_path: Path) -> None:
        now = time.time()
        sidecar_dir = self._write_sidecar(tmp_path, 1, {
            "model": "Claude",
            "status": "working",
            "task": "Task",
            "tokens": {"used": 60000, "max": 200000, "pct": 30},
            "updated_at": now,
            "tokens_updated_at": now,  # fresh
        })
        pane = PaneInfo(addr="0:0", pane_id="%1", command="claude")
        state = _collect_claude_pane(pane, sidecar_dir, "def456", "lab")

        assert state is not None
        assert state.tokens.fresh is True

    def test_no_tokens_updated_at_falls_back_to_updated_at(self, tmp_path: Path) -> None:
        now = time.time()
        sidecar_dir = self._write_sidecar(tmp_path, 2, {
            "model": "Claude",
            "status": "working",
            "task": "Task",
            "tokens": {"used": 40000, "max": 200000, "pct": 20},
            "updated_at": now,  # recent — no tokens_updated_at
        })
        pane = PaneInfo(addr="0:0", pane_id="%2", command="claude")
        state = _collect_claude_pane(pane, sidecar_dir, "def456", "lab")

        assert state is not None
        assert state.tokens.fresh is True  # fallback to updated_at (recent)


# ── Orchestrator batch parsing ─────────────────────────────────────────────────

class TestParseBatch:
    def _batch(self, **kwargs: object) -> dict:
        base: dict = {
            "area": "workspace",
            "batchId": "20260313-abc",
            "issues": [1, 2, 3],
            "status": {"1": "completed", "2": "dispatched", "3": "pending"},
            "dispatched": {
                "2": {"pid": 99_999_999, "dispatchedAt": "2026-03-13T10:00:00Z"},
            },
            "orchestratorPid": 0,
            "orchestratorStartedAt": "",
            "createdAt": "2026-03-13T09:00:00Z",
        }
        base.update(kwargs)
        return base

    def test_dead_orchestrator_pid_not_running(self, tmp_path: Path) -> None:
        """PID 99999999 doesn't exist → batch_status=dead."""
        data = self._batch(orchestratorPid=99_999_999)
        batch = _parse_batch(data, tmp_path, time.time())
        assert batch is not None
        assert batch.batch_status == BatchStatus.DEAD

    def test_zero_pid_treated_as_dead(self, tmp_path: Path) -> None:
        data = self._batch(orchestratorPid=0)
        batch = _parse_batch(data, tmp_path, time.time())
        assert batch is not None
        # PID 0 → not alive → dead
        assert batch.batch_status == BatchStatus.DEAD

    def test_done_when_all_completed(self, tmp_path: Path) -> None:
        # Use own PID (alive) so the orchestrator is considered "still running"
        # while all issues are completed → batch_status=done.
        data = self._batch(
            issues=[1, 2],
            status={"1": "completed", "2": "completed"},
            dispatched={},
            orchestratorPid=os.getpid(),
            orchestratorStartedAt="",  # skip create_time check
        )
        batch = _parse_batch(data, tmp_path, time.time())
        assert batch is not None
        assert batch.batch_status == BatchStatus.DONE
        assert batch.n_done == 2
        assert batch.n_failed == 0

    def test_counts_done_failed_total(self, tmp_path: Path) -> None:
        data = self._batch(
            issues=[1, 2, 3, 4],
            status={
                "1": "completed",
                "2": "failed",
                "3": "dispatched",
                "4": "pending",
            },
            orchestratorPid=0,
        )
        batch = _parse_batch(data, tmp_path, time.time())
        assert batch is not None
        assert batch.n_done == 1
        assert batch.n_failed == 1
        assert batch.n_total == 4

    def test_missing_area_returns_none(self, tmp_path: Path) -> None:
        assert _parse_batch({"batchId": "x"}, tmp_path, time.time()) is None

    def test_missing_batch_id_returns_none(self, tmp_path: Path) -> None:
        assert _parse_batch({"area": "workspace"}, tmp_path, time.time()) is None

    def test_elapsed_format(self, tmp_path: Path) -> None:
        data = self._batch(createdAt="2026-03-13T09:00:00Z")
        now = time.time()
        batch = _parse_batch(data, tmp_path, now)
        assert batch is not None
        # elapsed should be a non-empty string (actual value depends on now vs createdAt)
        assert isinstance(batch.elapsed, str)

    def test_dispatched_scoped_to_issues_list(self, tmp_path: Path) -> None:
        """Orphaned dispatch entries not in .issues must be excluded."""
        data = self._batch(
            issues=[1, 2],  # issue 3 is NOT in issues list
            status={"1": "dispatched", "2": "dispatched", "3": "dispatched"},
            dispatched={
                "1": {"pid": 99_999_999, "dispatchedAt": "2026-03-13T10:00:00Z"},
                "2": {"pid": 99_999_998, "dispatchedAt": "2026-03-13T10:01:00Z"},
                "3": {"pid": 99_999_997, "dispatchedAt": "2026-03-13T10:02:00Z"},
            },
            orchestratorPid=0,
        )
        batch = _parse_batch(data, tmp_path, time.time())
        assert batch is not None
        assert batch.n_total == 2  # only issues 1 and 2 count
