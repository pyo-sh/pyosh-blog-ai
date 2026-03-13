"""Tests for orchctl merge-gate command and evaluation logic."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from orchctl.cli import cli
from orchctl.commands.merge_gate import evaluate_merge_gate
from orchctl.db.config import set_config
from orchctl.db.connection import get_db, init_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def db_path(tmp_path: Path) -> str:
    path = str(tmp_path / "test.db")
    runner_ = CliRunner()
    runner_.invoke(cli, ["--db", path, "init"])
    return path


@pytest.fixture
def conn(tmp_path: Path):
    db_path = tmp_path / "test.db"
    c, _ = init_db(db_path)
    yield c
    c.close()


def _insert_issue_with_attempt(
    conn,
    area: str = "client",
    number: int = 1,
    terminal_json: dict | None = None,
) -> int:
    cur = conn.execute(
        "INSERT INTO issues (area, number, state) VALUES (?, ?, 'completed')",
        (area, number),
    )
    conn.commit()
    issue_id = cur.lastrowid
    if terminal_json is not None:
        conn.execute(
            "INSERT INTO attempts (attempt_id, issue_id, status, terminal_json) "
            "VALUES (?, ?, 'completed', ?)",
            (f"att-{number}", issue_id, json.dumps(terminal_json)),
        )
        conn.commit()
    return issue_id


_FULL_PASS_TERMINAL = {
    "attemptId": "att-1",
    "status": "completed",
    "prNumber": 10,
    "mergeEligible": True,
    "mergeEligibilityChecks": {
        "checksPass": True,
        "shaMatch": True,
        "noConflict": True,
        "noBlockingLabels": True,
    },
    "targetBranch": "feature/xyz",  # not a protected branch
}


# ---------------------------------------------------------------------------
# evaluate_merge_gate — unit tests
# ---------------------------------------------------------------------------


class TestEvaluateMergeGate:
    def test_passes_when_all_checks_true(self, conn):
        set_config(conn, "merge_enabled", "true")
        set_config(conn, "protected_branches", "main")
        _insert_issue_with_attempt(conn, terminal_json=_FULL_PASS_TERMINAL)

        result = evaluate_merge_gate(conn, "client", 1)
        assert result["eligible"] is True
        assert result["reason"] is None

    def test_fails_when_merge_disabled(self, conn):
        set_config(conn, "merge_enabled", "false")
        _insert_issue_with_attempt(conn, terminal_json=_FULL_PASS_TERMINAL)

        result = evaluate_merge_gate(conn, "client", 1)
        assert result["eligible"] is False
        assert result["checks"]["branch_protection"] is False
        assert result["reason"] == "merge_disabled"

    def test_fails_when_target_branch_is_protected(self, conn):
        set_config(conn, "merge_enabled", "true")
        set_config(conn, "protected_branches", "main,feature/xyz")

        terminal = dict(_FULL_PASS_TERMINAL)
        terminal["targetBranch"] = "feature/xyz"
        _insert_issue_with_attempt(conn, terminal_json=terminal)

        result = evaluate_merge_gate(conn, "client", 1)
        assert result["eligible"] is False
        assert result["checks"]["branch_protection"] is False

    def test_fails_when_checks_pass_is_false(self, conn):
        set_config(conn, "merge_enabled", "true")
        set_config(conn, "protected_branches", "main")
        terminal = dict(_FULL_PASS_TERMINAL)
        terminal["mergeEligibilityChecks"] = dict(_FULL_PASS_TERMINAL["mergeEligibilityChecks"])
        terminal["mergeEligibilityChecks"]["checksPass"] = False
        _insert_issue_with_attempt(conn, terminal_json=terminal)

        result = evaluate_merge_gate(conn, "client", 1)
        assert result["eligible"] is False
        assert result["checks"]["checks_pass"] is False

    def test_fails_when_sha_mismatch(self, conn):
        set_config(conn, "merge_enabled", "true")
        set_config(conn, "protected_branches", "main")
        terminal = dict(_FULL_PASS_TERMINAL)
        terminal["mergeEligibilityChecks"] = dict(_FULL_PASS_TERMINAL["mergeEligibilityChecks"])
        terminal["mergeEligibilityChecks"]["shaMatch"] = False
        _insert_issue_with_attempt(conn, terminal_json=terminal)

        result = evaluate_merge_gate(conn, "client", 1)
        assert result["eligible"] is False
        assert result["checks"]["sha_match"] is False

    def test_fails_when_conflict(self, conn):
        set_config(conn, "merge_enabled", "true")
        set_config(conn, "protected_branches", "main")
        terminal = dict(_FULL_PASS_TERMINAL)
        terminal["mergeEligibilityChecks"] = dict(_FULL_PASS_TERMINAL["mergeEligibilityChecks"])
        terminal["mergeEligibilityChecks"]["noConflict"] = False
        _insert_issue_with_attempt(conn, terminal_json=terminal)

        result = evaluate_merge_gate(conn, "client", 1)
        assert result["eligible"] is False
        assert result["checks"]["no_conflict"] is False

    def test_fails_when_blocking_labels(self, conn):
        set_config(conn, "merge_enabled", "true")
        set_config(conn, "protected_branches", "main")
        terminal = dict(_FULL_PASS_TERMINAL)
        terminal["mergeEligibilityChecks"] = dict(_FULL_PASS_TERMINAL["mergeEligibilityChecks"])
        terminal["mergeEligibilityChecks"]["noBlockingLabels"] = False
        _insert_issue_with_attempt(conn, terminal_json=terminal)

        result = evaluate_merge_gate(conn, "client", 1)
        assert result["eligible"] is False
        assert result["checks"]["no_blocking_labels"] is False

    def test_null_checks_fail(self, conn):
        """If terminal_json is missing, all checks are None and gate fails."""
        set_config(conn, "merge_enabled", "true")
        set_config(conn, "protected_branches", "main")
        _insert_issue_with_attempt(conn, terminal_json=None)

        result = evaluate_merge_gate(conn, "client", 1)
        assert result["eligible"] is False
        for check in ("checks_pass", "sha_match", "no_conflict", "no_blocking_labels"):
            assert result["checks"][check] is None

    def test_issue_not_found(self, conn):
        result = evaluate_merge_gate(conn, "client", 9999)
        assert result["eligible"] is False
        assert result["reason"] == "issue_not_found"

    def test_no_completed_attempt(self, conn):
        conn.execute(
            "INSERT INTO issues (area, number, state) VALUES ('client', 1, 'dispatched')"
        )
        conn.commit()
        result = evaluate_merge_gate(conn, "client", 1)
        # All checks are None, gate fails
        assert result["eligible"] is False

    def test_default_target_branch_is_main(self, conn):
        """If terminal.json has no targetBranch, default to 'main' (protected)."""
        set_config(conn, "merge_enabled", "true")
        set_config(conn, "protected_branches", "main")
        terminal = dict(_FULL_PASS_TERMINAL)
        terminal.pop("targetBranch", None)
        _insert_issue_with_attempt(conn, terminal_json=terminal)

        result = evaluate_merge_gate(conn, "client", 1)
        # main is protected, so branch_protection fails
        assert result["checks"]["branch_protection"] is False
        assert result["eligible"] is False

    def test_multiple_protected_branches(self, conn):
        set_config(conn, "merge_enabled", "true")
        set_config(conn, "protected_branches", "main,develop,release")
        terminal = dict(_FULL_PASS_TERMINAL)
        terminal["targetBranch"] = "develop"
        _insert_issue_with_attempt(conn, terminal_json=terminal)

        result = evaluate_merge_gate(conn, "client", 1)
        assert result["checks"]["branch_protection"] is False


# ---------------------------------------------------------------------------
# CLI tests
# ---------------------------------------------------------------------------


class TestMergeGateCLI:
    def test_merge_gate_fails_when_disabled(self, runner, db_path):
        conn = get_db(db_path)
        cur = conn.execute(
            "INSERT INTO issues (area, number, state) VALUES ('client', 5, 'completed')"
        )
        conn.commit()
        issue_id = cur.lastrowid
        conn.execute(
            "INSERT INTO attempts (attempt_id, issue_id, status, terminal_json) "
            "VALUES ('att-5', ?, 'completed', ?)",
            (issue_id, json.dumps(_FULL_PASS_TERMINAL)),
        )
        conn.commit()
        conn.close()

        result = runner.invoke(
            cli,
            ["--db", db_path, "merge-gate", "--area", "client", "--issue", "5"],
        )
        # merge_enabled defaults to false, so exit code 1
        assert result.exit_code == 1
        assert "FAIL" in result.output

    def test_merge_gate_passes_when_all_ok(self, runner, db_path):
        conn = get_db(db_path)
        set_config(conn, "merge_enabled", "true")
        set_config(conn, "protected_branches", "main")
        conn.commit()

        cur = conn.execute(
            "INSERT INTO issues (area, number, state) VALUES ('client', 6, 'completed')"
        )
        conn.commit()
        issue_id = cur.lastrowid
        conn.execute(
            "INSERT INTO attempts (attempt_id, issue_id, status, terminal_json) "
            "VALUES ('att-6', ?, 'completed', ?)",
            (issue_id, json.dumps(_FULL_PASS_TERMINAL)),
        )
        conn.commit()
        conn.close()

        result = runner.invoke(
            cli,
            ["--db", db_path, "merge-gate", "--area", "client", "--issue", "6"],
        )
        assert result.exit_code == 0
        assert "PASS" in result.output

    def test_merge_gate_json_output(self, runner, db_path):
        result = runner.invoke(
            cli,
            ["--db", db_path, "merge-gate", "--area", "client", "--issue", "999", "--json"],
        )
        data = json.loads(result.output)
        assert "eligible" in data
        assert "checks" in data
        assert data["eligible"] is False

    def test_merge_gate_requires_init(self, runner, tmp_path):
        db = str(tmp_path / "new.db")
        result = runner.invoke(
            cli, ["--db", db, "merge-gate", "--area", "client", "--issue", "1"]
        )
        assert result.exit_code != 0
        assert "not initialised" in result.output


# ---------------------------------------------------------------------------
# Guardrail integration: repo allowlist blocks dispatch
# ---------------------------------------------------------------------------


class TestRepoAllowlistGuardrail:
    def test_dispatch_blocked_when_repo_not_in_allowlist(self, runner, db_path):
        conn = get_db(db_path)
        set_config(conn, "repo_allowlist", "pyo-sh/pyosh-blog-fe")
        set_config(conn, "workspace.repo", "pyo-sh/pyosh-blog-ai")
        conn.commit()
        conn.execute(
            "INSERT INTO issues (area, number, state) VALUES ('workspace', 1, 'pending')"
        )
        conn.commit()
        conn.close()

        result = runner.invoke(cli, ["--db", db_path, "reconcile", "--area", "workspace"])
        assert result.exit_code == 0, result.output
        assert "not in allowlist" in result.output
        assert "ready to dispatch" not in result.output

    def test_dispatch_allowed_when_repo_in_allowlist(self, runner, db_path):
        conn = get_db(db_path)
        set_config(conn, "repo_allowlist", "pyo-sh/pyosh-blog-ai")
        set_config(conn, "workspace.repo", "pyo-sh/pyosh-blog-ai")
        conn.commit()
        conn.execute(
            "INSERT INTO issues (area, number, state) VALUES ('workspace', 2, 'pending')"
        )
        conn.commit()
        conn.close()

        result = runner.invoke(cli, ["--db", db_path, "reconcile", "--area", "workspace"])
        assert result.exit_code == 0, result.output
        assert "ready to dispatch" in result.output

    def test_dispatch_allowed_when_allowlist_empty(self, runner, db_path):
        """Empty allowlist means no restriction."""
        conn = get_db(db_path)
        conn.execute(
            "INSERT INTO issues (area, number, state) VALUES ('client', 3, 'pending')"
        )
        conn.commit()
        conn.close()

        result = runner.invoke(cli, ["--db", db_path, "reconcile", "--area", "client"])
        assert result.exit_code == 0, result.output
        assert "ready to dispatch" in result.output

    def test_dispatch_blocked_when_area_repo_not_configured(self, runner, db_path):
        """If repo_allowlist is set but area repo is not configured, fail closed."""
        conn = get_db(db_path)
        set_config(conn, "repo_allowlist", "pyo-sh/pyosh-blog-fe")
        # workspace.repo is NOT set
        conn.execute(
            "INSERT INTO issues (area, number, state) VALUES ('workspace', 4, 'pending')"
        )
        conn.commit()
        conn.close()

        result = runner.invoke(cli, ["--db", db_path, "reconcile", "--area", "workspace"])
        assert result.exit_code == 0, result.output
        # Fails closed: area_repo not configured → no dispatches
        assert "workspace.repo is not configured" in result.output
        assert "ready to dispatch" not in result.output


# ---------------------------------------------------------------------------
# apply-policy CLI
# ---------------------------------------------------------------------------


class TestApplyPolicyCLI:
    def test_apply_policy_updates_config(self, runner, db_path, tmp_path):
        policy_file = tmp_path / "policy.yaml"
        policy_file.write_text(
            "concurrency:\n  area_max: 8\nmerge:\n  enabled: true\n"
        )
        result = runner.invoke(
            cli,
            ["--db", db_path, "apply-policy", "--policy-file", str(policy_file)],
        )
        assert result.exit_code == 0, result.output
        assert "max_concurrent" in result.output
        assert "merge_enabled" in result.output

        conn = get_db(db_path)
        from orchctl.db.config import get_config
        assert get_config(conn, "max_concurrent") == "8"
        assert get_config(conn, "merge_enabled") == "true"
        conn.close()

    def test_apply_policy_reports_no_changes_on_second_run(self, runner, db_path, tmp_path):
        policy_file = tmp_path / "policy.yaml"
        policy_file.write_text("concurrency:\n  area_max: 4\n")

        runner.invoke(cli, ["--db", db_path, "apply-policy", "--policy-file", str(policy_file)])
        result = runner.invoke(
            cli, ["--db", db_path, "apply-policy", "--policy-file", str(policy_file)]
        )
        assert result.exit_code == 0, result.output
        assert "no changes" in result.output

    def test_apply_policy_fails_without_policy_file(self, runner, db_path, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("ORCHCTL_POLICY", raising=False)
        result = runner.invoke(cli, ["--db", db_path, "apply-policy"])
        assert result.exit_code != 0
        assert "No policy file found" in result.output

    def test_apply_policy_requires_init(self, runner, tmp_path):
        db = str(tmp_path / "new.db")
        policy_file = tmp_path / "p.yaml"
        policy_file.write_text("")
        result = runner.invoke(
            cli, ["--db", db, "apply-policy", "--policy-file", str(policy_file)]
        )
        assert result.exit_code != 0
        assert "not initialised" in result.output
