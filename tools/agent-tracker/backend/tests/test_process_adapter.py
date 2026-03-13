"""Tests for process_adapter: is_running, get_create_time."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from backend.adapters.process_adapter import get_create_time, is_running


class TestIsRunningBoundaryValues:
    def test_zero_pid(self) -> None:
        assert is_running(0) is False

    def test_negative_pid(self) -> None:
        assert is_running(-1) is False

    def test_large_nonexistent_pid(self) -> None:
        assert is_running(99_999_999) is False

    def test_own_pid_is_running(self) -> None:
        assert is_running(os.getpid()) is True


class TestIsRunningWithCreateTime:
    def test_own_pid_correct_create_time(self) -> None:
        """Own PID + correct create_time → running."""
        ct = get_create_time(os.getpid())
        assert ct is not None
        assert is_running(os.getpid(), create_time=ct) is True

    def test_own_pid_wrong_create_time(self) -> None:
        """PID reuse protection: wrong create_time → not running."""
        assert is_running(os.getpid(), create_time=0.0) is False

    def test_own_pid_far_future_create_time(self) -> None:
        assert is_running(os.getpid(), create_time=1e15) is False


class TestGetCreateTime:
    def test_own_process(self) -> None:
        ct = get_create_time(os.getpid())
        assert ct is not None
        assert isinstance(ct, float)
        assert ct > 0.0

    def test_invalid_pids(self) -> None:
        assert get_create_time(0) is None
        assert get_create_time(-1) is None

    def test_nonexistent_pid(self) -> None:
        assert get_create_time(99_999_999) is None


class TestIsRunningPsutilPath:
    """Unit tests for the psutil code path (mocked to run without psutil installed)."""

    def test_no_such_process(self) -> None:
        with patch("backend.adapters.process_adapter._PSUTIL_AVAILABLE", True):
            with patch(
                "backend.adapters.process_adapter._is_running_psutil",
                return_value=False,
            ):
                assert is_running(99_999_999) is False

    def test_psutil_access_denied_treated_as_not_running(self) -> None:
        with patch("backend.adapters.process_adapter._PSUTIL_AVAILABLE", True):
            with patch(
                "backend.adapters.process_adapter._is_running_psutil",
                return_value=False,
            ):
                assert is_running(1) is False  # PID 1 may deny access


class TestIsRunningProcFallback:
    """Unit tests for the /proc fallback path."""

    def test_proc_path_own_pid(self) -> None:
        with patch("backend.adapters.process_adapter._PSUTIL_AVAILABLE", False):
            assert is_running(os.getpid()) is True

    def test_proc_path_nonexistent(self) -> None:
        with patch("backend.adapters.process_adapter._PSUTIL_AVAILABLE", False):
            assert is_running(99_999_999) is False
