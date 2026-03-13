"""Multi-signal heartbeat collection and stall detection for orchctl.

Signals collected per running attempt:
  1. pr_activity  - PR had any activity recently (GitHub API, updatedAt)
  2. state_mtime  - pipeline state file was recently modified
  3. log_mtime    - worker log file was recently modified
  4. cpu_delta    - /proc/{pid}/stat CPU jiffies changed since last sample

Stall rule: absent_count >= STALL_MIN_ABSENT (default 2).
A single absent signal is ignored; two or more absent signals indicate a stall.
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

# Seconds within which a signal must show activity to be considered "present".
SIGNAL_THRESHOLD_S: int = 600  # 10 minutes

# Stall when this many or more signals are absent.
STALL_MIN_ABSENT: int = 2


@dataclass
class SignalSnapshot:
    pr_activity: bool  # True = PR had recent activity (updatedAt within threshold)
    state_mtime: bool  # True = pipeline state file recently modified
    log_mtime: bool    # True = worker log recently modified
    cpu_delta: bool    # True = CPU jiffies changed since last sample
    cpu_jiffies: Optional[int] = None  # raw current value for next-cycle compare

    @property
    def absent_count(self) -> int:
        """Number of absent (False) signals."""
        return sum(
            1 for v in (self.pr_activity, self.state_mtime, self.log_mtime, self.cpu_delta)
            if not v
        )

    def is_stalled(self, min_absent: int = STALL_MIN_ABSENT) -> bool:
        """Return True when enough signals are absent to declare a stall."""
        return self.absent_count >= min_absent

    def to_json(self) -> str:
        return json.dumps({
            "pr_activity": self.pr_activity,
            "state_mtime": self.state_mtime,
            "log_mtime": self.log_mtime,
            "cpu_delta": self.cpu_delta,
            "cpu_jiffies": self.cpu_jiffies,
        })


# ---------------------------------------------------------------------------
# Low-level signal readers
# ---------------------------------------------------------------------------

def _read_cpu_jiffies(pid: int) -> Optional[int]:
    """Read utime + stime from /proc/{pid}/stat. Returns None on any error.

    Parses after the closing ')' of the comm field to handle process names
    that contain spaces (e.g. kernel threads like "(kworker/0:1)").
    After the last ')': state ppid pgrp ... utime(at+11) stime(at+12).
    """
    try:
        with open(f"/proc/{pid}/stat") as f:
            raw = f.read()
        # The comm field is enclosed in parentheses and may contain spaces.
        # Split on the last ')' to skip it entirely.
        comm_end = raw.rfind(")")
        if comm_end == -1:
            return None
        fields = raw[comm_end + 1:].split()
        # After the closing ')': state(0) ppid(1) pgrp(2) ... utime(11) stime(12)
        return int(fields[11]) + int(fields[12])
    except (OSError, IndexError, ValueError):
        return None


def _recent_mtime(path: str, now: float, threshold_s: int) -> bool:
    """Return True if the file at *path* was modified within *threshold_s* seconds."""
    try:
        mtime = os.path.getmtime(path)
        return (now - mtime) < threshold_s
    except OSError:
        return False


def _check_pr_activity(
    area: str,
    issue_number: int,
    state_file: str,
    threshold_s: int,
) -> bool:
    """Return True if the issue's PR has had any activity within *threshold_s* seconds.

    Activity is defined as `updatedAt` being within the threshold: this includes
    new commits, comments, label changes, and status updates.  The field name
    `pr_activity` reflects this broader semantics (not just commits).

    Reads the PR number from the pipeline state file to avoid an extra gh API
    call.  Returns False if the state file is missing, the PR is not yet
    created, or the gh call fails.
    """
    from .github import AREA_REPOS

    pr_number: Optional[int] = None
    try:
        with open(state_file) as f:
            state = json.load(f)
        pr_raw = state.get("pr")
        if pr_raw:
            pr_number = int(pr_raw)
    except (OSError, json.JSONDecodeError, ValueError):
        pass

    if not pr_number:
        return False

    repo = AREA_REPOS.get(area)
    if not repo:
        return False

    try:
        result = subprocess.run(
            [
                "gh", "pr", "view", str(pr_number),
                "-R", repo,
                "--json", "updatedAt",
                "--jq", ".updatedAt",
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            return False
        updated_str = result.stdout.strip()
        if not updated_str:
            return False
        updated_at = datetime.fromisoformat(updated_str.replace("Z", "+00:00"))
        elapsed = (datetime.now(timezone.utc) - updated_at).total_seconds()
        return elapsed < threshold_s
    except Exception:  # noqa: BLE001
        return False


# ---------------------------------------------------------------------------
# Signal collection
# ---------------------------------------------------------------------------

def collect_signals(
    *,
    area: str,
    issue_number: int,
    pid: Optional[int],
    attempt_dir: str,
    monorepo_root: str,
    prev_cpu_jiffies: Optional[int],
    threshold_s: int = SIGNAL_THRESHOLD_S,
) -> SignalSnapshot:
    """Collect all four heartbeat signals for one running attempt.

    Args:
        area: Orchestrator area (client, server, workspace).
        issue_number: GitHub issue number.
        pid: Worker process PID (from attempts.pid). May be None.
        attempt_dir: Absolute path to the attempt artifact directory
            (contains worker.log written by orch-dispatch-wrapper.sh).
        monorepo_root: Absolute path to the monorepo root.
        prev_cpu_jiffies: CPU jiffies value from the previous heartbeat.
            Pass None on the first call (treated as active — benefit of doubt).
        threshold_s: Activity window in seconds.

    Returns:
        SignalSnapshot with per-signal boolean activity flags.
    """
    now = datetime.now(timezone.utc).timestamp()

    # Signal 2: pipeline state file mtime
    state_file = os.path.join(
        monorepo_root, ".workspace", "pipeline", area,
        f"issue-{issue_number}.state.json",
    )
    state_mtime = _recent_mtime(state_file, now, threshold_s)

    # Signal 1: PR activity (reads pr number from state file)
    pr_activity = _check_pr_activity(area, issue_number, state_file, threshold_s)

    # Signal 3: log file mtime
    log_file = os.path.join(attempt_dir, "worker.log")
    log_mtime = _recent_mtime(log_file, now, threshold_s)

    # Signal 4: CPU jiffies delta
    cpu_jiffies: Optional[int] = None
    cpu_delta: bool
    if pid is not None:
        cpu_jiffies = _read_cpu_jiffies(pid)
        if cpu_jiffies is None:
            # Process not found — signal absent.
            cpu_delta = False
        elif prev_cpu_jiffies is None:
            # First sample: no baseline to compare; give benefit of doubt.
            cpu_delta = True
        else:
            cpu_delta = cpu_jiffies != prev_cpu_jiffies
    else:
        # No PID recorded — signal absent.
        cpu_delta = False

    return SignalSnapshot(
        pr_activity=pr_activity,
        state_mtime=state_mtime,
        log_mtime=log_mtime,
        cpu_delta=cpu_delta,
        cpu_jiffies=cpu_jiffies,
    )


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def record_heartbeat(
    conn: sqlite3.Connection,
    attempt_id: str,
    snapshot: SignalSnapshot,
) -> None:
    """Insert a heartbeat row for *attempt_id*."""
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO heartbeats (attempt_id, timestamp, signals) VALUES (?, ?, ?)",
        (attempt_id, now, snapshot.to_json()),
    )
    conn.commit()


def get_last_cpu_jiffies(conn: sqlite3.Connection, attempt_id: str) -> Optional[int]:
    """Return cpu_jiffies from the most recent heartbeat for *attempt_id*, or None."""
    row = conn.execute(
        """
        SELECT signals FROM heartbeats
        WHERE attempt_id = ?
        ORDER BY timestamp DESC
        LIMIT 1
        """,
        (attempt_id,),
    ).fetchone()
    if row is None:
        return None
    try:
        data = json.loads(row[0] or "{}")
        val = data.get("cpu_jiffies")
        return int(val) if val is not None else None
    except (json.JSONDecodeError, ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Attempt directory path convention
# ---------------------------------------------------------------------------

def attempt_dir_path(
    monorepo_root: str, area: str, issue_number: int, attempt_id: str
) -> str:
    """Return the conventional attempt artifact directory path.

    Matches the convention used by orch-dispatch-wrapper.sh:
      {monorepo_root}/.workspace/orchestrate/{area}/issues/{N}/attempts/{attempt_id}/
    """
    return os.path.join(
        monorepo_root,
        ".workspace", "orchestrate", area,
        "issues", str(issue_number),
        "attempts", attempt_id,
    )


# ---------------------------------------------------------------------------
# Combined check
# ---------------------------------------------------------------------------

def check_stall(
    conn: sqlite3.Connection,
    *,
    area: str,
    issue_number: int,
    attempt_id: str,
    pid: Optional[int],
    monorepo_root: str,
    threshold_s: int = SIGNAL_THRESHOLD_S,
    min_absent: int = STALL_MIN_ABSENT,
) -> tuple[bool, SignalSnapshot]:
    """Collect signals, record a heartbeat, and return stall status.

    Collects all four signals, writes a heartbeat row to the DB, then
    evaluates whether the absent signal count meets the stall threshold.

    Returns:
        (stalled, snapshot) where stalled is True when absent_count >= min_absent.
    """
    a_dir = attempt_dir_path(monorepo_root, area, issue_number, attempt_id)
    prev_cpu = get_last_cpu_jiffies(conn, attempt_id)
    snapshot = collect_signals(
        area=area,
        issue_number=issue_number,
        pid=pid,
        attempt_dir=a_dir,
        monorepo_root=monorepo_root,
        prev_cpu_jiffies=prev_cpu,
        threshold_s=threshold_s,
    )
    record_heartbeat(conn, attempt_id, snapshot)
    return snapshot.is_stalled(min_absent), snapshot
