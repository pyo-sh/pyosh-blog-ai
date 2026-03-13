"""Policy YAML loader for orchctl.

Reads .workspace/orchestrate/policy.yaml and syncs settings to the DB config
table so that the next reconcile pass picks them up automatically.

Policy file location (first match wins):
  1. Path from ORCHCTL_POLICY env var
  2. .workspace/orchestrate/policy.yaml relative to cwd
"""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

try:
    import yaml

    _YAML_AVAILABLE = True
except ImportError:  # pragma: no cover
    _YAML_AVAILABLE = False

from .db.config import get_config, set_config

POLICY_FILENAME = "policy.yaml"
_DEFAULT_POLICY_PATH = Path(".workspace") / "orchestrate" / POLICY_FILENAME


def find_policy_file(cwd: Path | None = None) -> Path | None:
    """Return the policy file path if it exists, else None."""
    env_path = os.environ.get("ORCHCTL_POLICY")
    if env_path:
        p = Path(env_path)
        return p if p.exists() else None
    base = cwd or Path.cwd()
    candidate = base / _DEFAULT_POLICY_PATH
    return candidate if candidate.exists() else None


def load_policy(path: Path) -> dict:
    """Parse policy.yaml. Returns a dict (empty if file is blank)."""
    if not _YAML_AVAILABLE:  # pragma: no cover
        raise RuntimeError(
            "PyYAML is required to load policy files. "
            "Install with: pip install PyYAML"
        )
    with path.open() as fh:
        return yaml.safe_load(fh) or {}


def apply_policy(conn: sqlite3.Connection, policy: dict) -> list[str]:
    """Sync policy dict to DB config. Returns list of config keys that changed."""
    changed: list[str] = []

    concurrency = policy.get("concurrency") or {}
    if "area_max" in concurrency:
        _maybe_set(conn, "max_concurrent", str(int(concurrency["area_max"])), changed)
    if "global_max" in concurrency:
        _maybe_set(conn, "max_open_pr", str(int(concurrency["global_max"])), changed)

    merge = policy.get("merge") or {}
    if "enabled" in merge:
        _maybe_set(conn, "merge_enabled", _bool_str(merge["enabled"]), changed)
    if "require_checks" in merge:
        _maybe_set(conn, "merge_require_checks", _bool_str(merge["require_checks"]), changed)
    if "require_clean_rebase" in merge:
        _maybe_set(
            conn, "merge_require_clean_rebase", _bool_str(merge["require_clean_rebase"]), changed
        )

    retry = policy.get("retry") or {}
    budgets = retry.get("budget_by_class") or {}
    if budgets:
        _maybe_set(conn, "retry_budget_by_class", json.dumps(budgets), changed)

    scope = policy.get("scope") or {}
    if "include_labels" in scope:
        _maybe_set(conn, "scope_include_labels", _list_str(scope["include_labels"]), changed)
    if "exclude_labels" in scope:
        _maybe_set(conn, "scope_exclude_labels", _list_str(scope["exclude_labels"]), changed)
    if "milestone" in scope:
        _maybe_set(conn, "scope_milestone", str(scope["milestone"] or ""), changed)

    guardrails = policy.get("guardrails") or {}
    if "repo_allowlist" in guardrails:
        _maybe_set(conn, "repo_allowlist", _list_str(guardrails["repo_allowlist"]), changed)
    if "protected_branches" in guardrails:
        _maybe_set(
            conn, "protected_branches", _list_str(guardrails["protected_branches"]), changed
        )
    if "max_concurrent_repair" in guardrails:
        _maybe_set(
            conn,
            "max_concurrent_repair",
            str(int(guardrails["max_concurrent_repair"])),
            changed,
        )
    if "scheduler_overlap" in guardrails:
        _maybe_set(
            conn, "scheduler_overlap", _bool_str(guardrails["scheduler_overlap"]), changed
        )
    if "dangerous_tools" in guardrails:
        _maybe_set(
            conn, "dangerous_tools", _list_str(guardrails["dangerous_tools"]), changed
        )
    if "max_awaiting_merge" in guardrails:
        _maybe_set(
            conn,
            "max_awaiting_merge",
            str(int(guardrails["max_awaiting_merge"])),
            changed,
        )

    scheduling = policy.get("scheduling") or {}
    if "priority_weight" in scheduling:
        _maybe_set(
            conn,
            "scheduling_priority_weight",
            str(float(scheduling["priority_weight"])),
            changed,
        )
    if "age_weight" in scheduling:
        _maybe_set(
            conn,
            "scheduling_age_weight",
            str(float(scheduling["age_weight"])),
            changed,
        )
    if "retry_weight" in scheduling:
        _maybe_set(
            conn,
            "scheduling_retry_weight",
            str(float(scheduling["retry_weight"])),
            changed,
        )

    return changed


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _maybe_set(
    conn: sqlite3.Connection, key: str, new_val: str, changed: list[str]
) -> None:
    if get_config(conn, key) != new_val:
        set_config(conn, key, new_val)
        changed.append(key)


def _bool_str(val: object) -> str:
    return "true" if val else "false"


def _list_str(val: object) -> str:
    if not val:
        return ""
    if isinstance(val, list):
        return ",".join(str(v) for v in val if v)
    return str(val)
