import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .models import PipelineState
from .paths import pipeline_state_path


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def state_exists(issue: int, area: str, monorepo_root: Path) -> bool:
    return pipeline_state_path(issue, area, monorepo_root).exists()


def _read_raw(issue: int, area: str, monorepo_root: Path) -> dict:
    """Internal: read state as raw dict."""
    path = pipeline_state_path(issue, area, monorepo_root)
    return json.loads(path.read_text())


def _write_raw(issue: int, area: str, monorepo_root: Path, data: dict) -> None:
    """Internal: atomic write of raw dict."""
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


def state_read(issue: int, area: str, monorepo_root: Path) -> PipelineState:
    """Read pipeline state as a typed PipelineState."""
    raw = _read_raw(issue, area, monorepo_root)
    return PipelineState.from_dict(raw)


def state_write(issue: int, area: str, monorepo_root: Path, state: PipelineState) -> None:
    """Atomic write of typed PipelineState."""
    _write_raw(issue, area, monorepo_root, state.to_dict())


def state_update(issue: int, area: str, monorepo_root: Path, updates: dict) -> None:
    """Shallow-merge updates into state dict, set updatedAt."""
    data = _read_raw(issue, area, monorepo_root)
    # Deep merge for nested dicts
    for k, v in updates.items():
        if isinstance(v, dict) and isinstance(data.get(k), dict):
            data[k] = {**data[k], **v}
        else:
            data[k] = v
    data["updatedAt"] = _now_iso()
    _write_raw(issue, area, monorepo_root, data)


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
        data = _read_raw(issue, area, monorepo_root)
        data.setdefault("transitionLog", []).append(entry)
        data["updatedAt"] = _now_iso()
        _write_raw(issue, area, monorepo_root, data)
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
        data = _read_raw(issue, area, monorepo_root)
        data.setdefault("recoveryLog", []).append(entry)
        data["updatedAt"] = _now_iso()
        _write_raw(issue, area, monorepo_root, data)
    except Exception:
        pass


def stage_retry(issue: int, area: str, monorepo_root: Path, stage: str) -> bool:
    """Increment retry counter. Returns True if retry is allowed, False if max reached."""
    data = _read_raw(issue, area, monorepo_root)
    retries = data.get("stageRetries", {}).get(stage, 0)
    max_retries = data.get("maxStageRetries", 3)
    if retries >= max_retries:
        return False
    data.setdefault("stageRetries", {})[stage] = retries + 1
    data["updatedAt"] = _now_iso()
    _write_raw(issue, area, monorepo_root, data)
    return True
