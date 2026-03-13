"""Process adapter - psutil-based.

Responsibility: process liveness and identity only.
No tmux, no file I/O, no business logic.
"""

from __future__ import annotations

import os

try:
    import psutil
    _PSUTIL_AVAILABLE = True
except ImportError:
    _PSUTIL_AVAILABLE = False


def is_running(pid: int, create_time: float | None = None) -> bool:
    """Check if a process is running.

    If create_time is provided, also verifies process identity to protect
    against PID reuse: returns False if the process creation time differs
    by more than 1 second from the stored value.
    """
    if not pid or pid <= 0:
        return False

    if _PSUTIL_AVAILABLE:
        return _is_running_psutil(pid, create_time)
    return _is_running_proc(pid, create_time)


def get_create_time(pid: int) -> float | None:
    """Return process creation time for identity tracking.

    Used with is_running() to detect PID reuse.
    Returns None if the process does not exist or is not accessible.
    """
    if not pid or pid <= 0:
        return None

    if _PSUTIL_AVAILABLE:
        return _get_create_time_psutil(pid)
    return _get_create_time_proc(pid)


# ── psutil implementations ────────────────────────────────────────────────────

def _is_running_psutil(pid: int, create_time: float | None) -> bool:
    try:
        proc = psutil.Process(pid)
        if not proc.is_running() or proc.status() == psutil.STATUS_ZOMBIE:
            return False
        if create_time is not None:
            actual_ct = proc.create_time()
            if abs(actual_ct - create_time) > 1.0:
                return False
        return True
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return False


def _get_create_time_psutil(pid: int) -> float | None:
    try:
        return psutil.Process(pid).create_time()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return None


# ── /proc fallback (Linux only) ───────────────────────────────────────────────

def _is_running_proc(pid: int, create_time: float | None) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False

    if create_time is not None:
        actual_ct = _get_create_time_proc(pid)
        if actual_ct is None or abs(actual_ct - create_time) > 1.0:
            return False

    return True


def _get_create_time_proc(pid: int) -> float | None:
    """Read process creation time from /proc/<pid>/stat (field 22, clock ticks since boot)."""
    try:
        with open(f"/proc/{pid}/stat") as f:
            fields = f.read().split()
        starttime_ticks = int(fields[21])
        hz = os.sysconf("SC_CLK_TCK")
        boot_time = _boot_time_proc()
        if boot_time is None:
            return None
        return boot_time + starttime_ticks / hz
    except (OSError, IndexError, ValueError):
        return None


def _boot_time_proc() -> float | None:
    try:
        with open("/proc/stat") as f:
            for line in f:
                if line.startswith("btime "):
                    return float(line.split()[1])
    except OSError:
        pass
    return None
