"""Tests for orchctl policy YAML loader."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from orchctl.db.connection import init_db
from orchctl.db.config import get_config
from orchctl.policy import apply_policy, find_policy_file, load_policy


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def conn(tmp_path: Path):
    db_path = tmp_path / "test.db"
    conn, _ = init_db(db_path)
    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# find_policy_file
# ---------------------------------------------------------------------------


def test_find_policy_file_returns_none_when_missing(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("ORCHCTL_POLICY", raising=False)
    assert find_policy_file() is None


def test_find_policy_file_returns_path_when_present(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("ORCHCTL_POLICY", raising=False)
    policy_path = tmp_path / ".workspace" / "orchestrate" / "policy.yaml"
    policy_path.parent.mkdir(parents=True)
    policy_path.write_text("concurrency:\n  area_max: 2\n")
    result = find_policy_file()
    assert result == policy_path


def test_find_policy_file_respects_env_var(tmp_path: Path, monkeypatch):
    custom = tmp_path / "custom.yaml"
    custom.write_text("")
    monkeypatch.setenv("ORCHCTL_POLICY", str(custom))
    assert find_policy_file() == custom


def test_find_policy_file_env_var_missing_file_returns_none(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("ORCHCTL_POLICY", str(tmp_path / "nonexistent.yaml"))
    assert find_policy_file() is None


# ---------------------------------------------------------------------------
# load_policy
# ---------------------------------------------------------------------------


def test_load_policy_empty_file(tmp_path: Path):
    p = tmp_path / "policy.yaml"
    p.write_text("")
    assert load_policy(p) == {}


def test_load_policy_minimal(tmp_path: Path):
    p = tmp_path / "policy.yaml"
    p.write_text("concurrency:\n  area_max: 3\n")
    result = load_policy(p)
    assert result["concurrency"]["area_max"] == 3


def test_load_policy_full(tmp_path: Path):
    p = tmp_path / "policy.yaml"
    p.write_text(
        """
concurrency:
  area_max: 2
  global_max: 6
merge:
  enabled: true
  require_checks: true
  require_clean_rebase: false
retry:
  budget_by_class:
    transient: 3
    default: 1
scope:
  include_labels:
    - feature
  exclude_labels:
    - blocked
  milestone: "v1.0"
guardrails:
  repo_allowlist:
    - pyo-sh/pyosh-blog-ai
  protected_branches:
    - main
    - release
  max_concurrent_repair: 2
  scheduler_overlap: false
  dangerous_tools: []
"""
    )
    result = load_policy(p)
    assert result["concurrency"]["area_max"] == 2
    assert result["merge"]["enabled"] is True
    assert result["retry"]["budget_by_class"]["transient"] == 3
    assert "feature" in result["scope"]["include_labels"]
    assert result["guardrails"]["max_concurrent_repair"] == 2


# ---------------------------------------------------------------------------
# apply_policy
# ---------------------------------------------------------------------------


def test_apply_policy_concurrency(conn):
    policy = {"concurrency": {"area_max": 6, "global_max": 12}}
    changed = apply_policy(conn, policy)
    assert "max_concurrent" in changed
    assert "max_open_pr" in changed
    assert get_config(conn, "max_concurrent") == "6"
    assert get_config(conn, "max_open_pr") == "12"


def test_apply_policy_merge(conn):
    policy = {
        "merge": {
            "enabled": True,
            "require_checks": False,
            "require_clean_rebase": True,
        }
    }
    changed = apply_policy(conn, policy)
    assert "merge_enabled" in changed
    assert get_config(conn, "merge_enabled") == "true"
    assert get_config(conn, "merge_require_checks") == "false"
    assert get_config(conn, "merge_require_clean_rebase") == "true"


def test_apply_policy_retry_budget(conn):
    policy = {"retry": {"budget_by_class": {"default": 2, "transient": 4}}}
    changed = apply_policy(conn, policy)
    assert "retry_budget" in changed
    assert get_config(conn, "retry_budget") == "2"
    budget_map = json.loads(get_config(conn, "retry_budget_by_class"))
    assert budget_map["transient"] == 4


def test_apply_policy_scope(conn):
    policy = {
        "scope": {
            "include_labels": ["feat", "bug"],
            "exclude_labels": ["blocked"],
            "milestone": "v2.0",
        }
    }
    changed = apply_policy(conn, policy)
    assert "scope_include_labels" in changed
    assert get_config(conn, "scope_include_labels") == "feat,bug"
    assert get_config(conn, "scope_exclude_labels") == "blocked"
    assert get_config(conn, "scope_milestone") == "v2.0"


def test_apply_policy_guardrails(conn):
    policy = {
        "guardrails": {
            "repo_allowlist": ["pyo-sh/pyosh-blog-ai"],
            "protected_branches": ["main", "release"],
            "max_concurrent_repair": 2,
            "scheduler_overlap": True,
            "dangerous_tools": ["rm -rf"],
        }
    }
    changed = apply_policy(conn, policy)
    assert "repo_allowlist" in changed
    assert get_config(conn, "repo_allowlist") == "pyo-sh/pyosh-blog-ai"
    assert get_config(conn, "protected_branches") == "main,release"
    assert get_config(conn, "max_concurrent_repair") == "2"
    assert get_config(conn, "scheduler_overlap") == "true"
    assert "rm -rf" in get_config(conn, "dangerous_tools")


def test_apply_policy_no_changes_when_same_values(conn):
    """If policy matches existing config, no keys are reported as changed."""
    # First apply sets the values.
    policy = {"concurrency": {"area_max": 4}}
    apply_policy(conn, policy)
    # Second apply with same values returns empty list.
    changed = apply_policy(conn, policy)
    assert changed == []


def test_apply_policy_empty_policy_changes_nothing(conn):
    changed = apply_policy(conn, {})
    assert changed == []


def test_apply_policy_null_lists(conn):
    """None values for lists should store empty string."""
    policy = {
        "scope": {"include_labels": None, "exclude_labels": []},
        "guardrails": {"repo_allowlist": None},
    }
    apply_policy(conn, policy)
    assert get_config(conn, "scope_include_labels") == ""
    assert get_config(conn, "scope_exclude_labels") == ""
    assert get_config(conn, "repo_allowlist") == ""
