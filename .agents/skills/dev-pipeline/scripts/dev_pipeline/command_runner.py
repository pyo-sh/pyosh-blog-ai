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
    replace_env: bool = False,
) -> RunResult:
    """Run a subprocess and return a structured result.

    When replace_env=True, env is used as-is (caller built the full environment).
    When replace_env=False (default), env is merged on top of os.environ.
    """
    final_env = None
    if env is not None:
        if replace_env:
            final_env = dict(env)
        else:
            final_env = {**os.environ, **env}

    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            env=final_env,
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
