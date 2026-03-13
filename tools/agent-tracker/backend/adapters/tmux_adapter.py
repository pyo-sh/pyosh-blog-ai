"""tmux adapter - CLI wrapping.

Responsibility: pane/session/server discovery via tmux CLI.
No business logic, no file I/O beyond subprocess calls.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
from dataclasses import dataclass


@dataclass
class PaneInfo:
    addr: str       # "window_index:pane_index"
    pane_id: str    # "%N"
    command: str    # pane_current_command



def socket_hash() -> str:
    """Compute the socket hash used in sidecar v2 namespace.

    Format: first 6 hex chars of MD5 of the tmux socket path.
    Matches the logic in on-statusline.sh and collect.sh.
    Returns "default" when $TMUX is not set.
    """
    tmux_env = os.environ.get("TMUX", "")
    if not tmux_env:
        return "default"
    socket_path = tmux_env.split(",")[0]
    return hashlib.md5(socket_path.encode()).hexdigest()[:6]


def list_panes(session: str) -> list[PaneInfo]:
    """List all panes in the given tmux session."""
    try:
        result = subprocess.run(
            [
                "tmux", "list-panes", "-s", "-t", session,
                "-F", "#{window_index}:#{pane_index} #{pane_id} #{pane_current_command}",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []

    panes = []
    for line in result.stdout.strip().splitlines():
        parts = line.split(" ", 2)
        if len(parts) == 3:
            panes.append(PaneInfo(addr=parts[0], pane_id=parts[1], command=parts[2]))
    return panes


def capture_pane(pane_id: str, lines: int = 8) -> str:
    """Capture the last N lines of a pane's visible content."""
    try:
        result = subprocess.run(
            ["tmux", "capture-pane", "-p", "-t", pane_id, "-S", f"-{lines}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""


def pane_tty(pane_id: str) -> str | None:
    """Get the TTY device path of a pane."""
    try:
        result = subprocess.run(
            ["tmux", "display-message", "-t", pane_id, "-p", "#{pane_tty}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        tty = result.stdout.strip()
        return tty if tty else None
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None
