import os
import subprocess
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class RunResult:
    command: List[str]
    rc: int
    stdout: str
    stderr: str
    timed_out: bool


def run(
    cmd: List[str],
    *,
    cwd: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
    timeout: Optional[int] = None,
    capture_output: bool = True,
) -> RunResult:
    """Run a subprocess and return a structured result."""
    merged_env = None
    if env is not None:
        merged_env = {**os.environ, **env}

    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            env=merged_env,
            timeout=timeout,
            capture_output=capture_output,
            text=True,
        )
        return RunResult(
            command=cmd,
            rc=result.returncode,
            stdout=result.stdout or "",
            stderr=result.stderr or "",
            timed_out=False,
        )
    except subprocess.TimeoutExpired:
        return RunResult(
            command=cmd,
            rc=124,
            stdout="",
            stderr=f"[command_runner] timed out after {timeout}s",
            timed_out=True,
        )
    except Exception as e:
        return RunResult(
            command=cmd,
            rc=1,
            stdout="",
            stderr=str(e),
            timed_out=False,
        )
