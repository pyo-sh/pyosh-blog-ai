import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Union


@dataclass
class RunResult:
    stdout: str
    stderr: str
    returncode: int


def run(
    cmd: List[str],
    *,
    cwd: Optional[Union[str, Path]] = None,
    check: bool = True,
    timeout: int = 120,
) -> RunResult:
    result = subprocess.run(
        cmd, capture_output=True, text=True, cwd=cwd, timeout=timeout
    )
    if check and result.returncode != 0:
        raise RuntimeError(
            f"Command failed (rc={result.returncode}): {' '.join(cmd)}\n{result.stderr}"
        )
    return RunResult(
        stdout=result.stdout or "",
        stderr=result.stderr or "",
        returncode=result.returncode,
    )
