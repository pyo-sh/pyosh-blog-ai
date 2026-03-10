import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .paths import pipeline_state_path


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def state_exists(issue: int, area: str, monorepo_root: Path) -> bool:
    return pipeline_state_path(issue, area, monorepo_root).exists()


def state_read(issue: int, area: str, monorepo_root: Path) -> dict:
    path = pipeline_state_path(issue, area, monorepo_root)
    return json.loads(path.read_text())


def state_write(issue: int, area: str, monorepo_root: Path, data: dict) -> None:
    """Atomic write to prevent half-written JSON on crash."""
    path = pipeline_state_path(issue, area, monorepo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".tmp.")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def state_update(issue: int, area: str, monorepo_root: Path, updates: dict) -> None:
    """Shallow-merge updates into state dict, set updatedAt."""
    data = state_read(issue, area, monorepo_root)
    # Deep merge for nested dicts
    for k, v in updates.items():
        if isinstance(v, dict) and isinstance(data.get(k), dict):
            data[k] = {**data[k], **v}
        else:
            data[k] = v
    data["updatedAt"] = _now_iso()
    state_write(issue, area, monorepo_root, data)


def state_delete(issue: int, area: str, monorepo_root: Path) -> None:
    path = pipeline_state_path(issue, area, monorepo_root)
    path.unlink(missing_ok=True)


def log_transition(
    issue: int,
    area: str,
    monorepo_root: Path,
    from_step: str,
    to_step: str,
    reason: str = "",
) -> None:
    """Append a transition log entry (non-fatal)."""
    print(
        f"[pipeline:transition] {from_step} -> {to_step} "
        f"(reason: {reason or '(none)'}) issue=#{issue} area={area}",
        file=sys.stderr,
    )
    entry = {"from": from_step, "to": to_step, "reason": reason, "ts": _now_iso()}
    try:
        data = state_read(issue, area, monorepo_root)
        data.setdefault("transitionLog", []).append(entry)
        data["updatedAt"] = _now_iso()
        state_write(issue, area, monorepo_root, data)
    except Exception:
        pass


def recovery_log_append(
    issue: int,
    area: str,
    monorepo_root: Path,
    stage: str,
    error: str,
    action: str,
    result: str,
) -> None:
    entry = {
        "stage": stage,
        "error": error,
        "action": action,
        "result": result,
        "timestamp": _now_iso(),
    }
    try:
        data = state_read(issue, area, monorepo_root)
        data.setdefault("recoveryLog", []).append(entry)
        data["updatedAt"] = _now_iso()
        state_write(issue, area, monorepo_root, data)
    except Exception:
        pass


def stage_retry(issue: int, area: str, monorepo_root: Path, stage: str) -> bool:
    """Increment retry counter. Returns True if retry is allowed, False if max reached."""
    data = state_read(issue, area, monorepo_root)
    retries = data.get("stageRetries", {}).get(stage, 0)
    max_retries = data.get("maxStageRetries", 3)
    if retries >= max_retries:
        return False
    data.setdefault("stageRetries", {})[stage] = retries + 1
    data["updatedAt"] = _now_iso()
    state_write(issue, area, monorepo_root, data)
    return True
