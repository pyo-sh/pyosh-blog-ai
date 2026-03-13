"""Tests for issue discovery: GitHub client filters and reconcile discovery pass."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from orchctl.cli import cli
from orchctl.db.connection import get_db, init_db
from orchctl.github import GitHubError, GitHubIssue, _apply_scope_filters


# ---------------------------------------------------------------------------
# _apply_scope_filters — pure filter logic
# ---------------------------------------------------------------------------


def _make_issue(number: int, labels: list[str], assignees: list[str] | None = None) -> GitHubIssue:
    return GitHubIssue(
        number=number,
        title=f"Issue #{number}",
        labels=labels,
        assignees=assignees or [],
    )


class TestApplyScopeFilters:
    def test_no_filters_returns_all(self):
        issues = [_make_issue(1, []), _make_issue(2, ["feat"])]
        result = _apply_scope_filters(
            issues,
            include_labels=[],
            exclude_labels=[],
            allow_unassigned=True,
        )
        assert [i.number for i in result] == [1, 2]

    def test_include_labels_or_semantics(self):
        issues = [
            _make_issue(1, ["stage-2"]),
            _make_issue(2, ["orchestrator"]),
            _make_issue(3, ["unrelated"]),
        ]
        result = _apply_scope_filters(
            issues,
            include_labels=["stage-2", "orchestrator"],
            exclude_labels=[],
            allow_unassigned=True,
        )
        assert {i.number for i in result} == {1, 2}

    def test_include_labels_empty_passes_all(self):
        issues = [_make_issue(1, []), _make_issue(2, ["x"])]
        result = _apply_scope_filters(
            issues,
            include_labels=[],
            exclude_labels=[],
            allow_unassigned=True,
        )
        assert len(result) == 2

    def test_exclude_labels_removes_matching(self):
        issues = [
            _make_issue(1, ["feat"]),
            _make_issue(2, ["manual-hold"]),
            _make_issue(3, ["needs-human"]),
        ]
        result = _apply_scope_filters(
            issues,
            include_labels=[],
            exclude_labels=["manual-hold", "needs-human"],
            allow_unassigned=True,
        )
        assert [i.number for i in result] == [1]

    def test_exclude_takes_precedence_over_include(self):
        issues = [_make_issue(1, ["stage-2", "manual-hold"])]
        result = _apply_scope_filters(
            issues,
            include_labels=["stage-2"],
            exclude_labels=["manual-hold"],
            allow_unassigned=True,
        )
        assert result == []

    def test_allow_unassigned_false_removes_unassigned(self):
        issues = [
            _make_issue(1, [], assignees=[]),
            _make_issue(2, [], assignees=["alice"]),
        ]
        result = _apply_scope_filters(
            issues,
            include_labels=[],
            exclude_labels=[],
            allow_unassigned=False,
        )
        assert [i.number for i in result] == [2]

    def test_allow_unassigned_true_keeps_unassigned(self):
        issues = [_make_issue(1, [], assignees=[])]
        result = _apply_scope_filters(
            issues,
            include_labels=[],
            exclude_labels=[],
            allow_unassigned=True,
        )
        assert len(result) == 1


# ---------------------------------------------------------------------------
# _enqueue_or_reopen — DB-level enqueue logic
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_db(tmp_path: Path):
    return tmp_path / "test.db"


@pytest.fixture
def db_conn(tmp_db):
    conn, _ = init_db(tmp_db)
    yield conn
    conn.close()


class TestEnqueueOrReopen:
    def test_new_issue_inserted_as_pending(self, db_conn):
        from orchctl.commands.reconcile import _enqueue_or_reopen

        _enqueue_or_reopen(db_conn, "client", 42, dry_run=False)

        row = db_conn.execute(
            "SELECT state FROM issues WHERE area='client' AND number=42"
        ).fetchone()
        assert row["state"] == "pending"

    def test_new_issue_dry_run_no_insert(self, db_conn):
        from orchctl.commands.reconcile import _enqueue_or_reopen

        _enqueue_or_reopen(db_conn, "client", 43, dry_run=True)

        row = db_conn.execute(
            "SELECT id FROM issues WHERE area='client' AND number=43"
        ).fetchone()
        assert row is None

    def test_already_pending_issue_not_duplicated(self, db_conn):
        db_conn.execute(
            "INSERT INTO issues (area, number, state) VALUES ('client', 10, 'pending')"
        )
        db_conn.commit()

        from orchctl.commands.reconcile import _enqueue_or_reopen

        _enqueue_or_reopen(db_conn, "client", 10, dry_run=False)

        count = db_conn.execute(
            "SELECT COUNT(*) FROM issues WHERE area='client' AND number=10"
        ).fetchone()[0]
        assert count == 1

    def test_already_dispatched_issue_not_touched(self, db_conn):
        db_conn.execute(
            "INSERT INTO issues (area, number, state) VALUES ('client', 11, 'dispatched')"
        )
        db_conn.commit()

        from orchctl.commands.reconcile import _enqueue_or_reopen

        _enqueue_or_reopen(db_conn, "client", 11, dry_run=False)

        state = db_conn.execute(
            "SELECT state FROM issues WHERE area='client' AND number=11"
        ).fetchone()["state"]
        assert state == "dispatched"

    @pytest.mark.parametrize("terminal_state", ["completed", "failed-terminal", "cancelled"])
    def test_reopened_terminal_issue_becomes_pending(self, db_conn, terminal_state):
        db_conn.execute(
            "INSERT INTO issues (area, number, state) VALUES ('client', 20, ?)",
            (terminal_state,),
        )
        db_conn.commit()

        from orchctl.commands.reconcile import _enqueue_or_reopen

        _enqueue_or_reopen(db_conn, "client", 20, dry_run=False)

        state = db_conn.execute(
            "SELECT state FROM issues WHERE area='client' AND number=20"
        ).fetchone()["state"]
        assert state == "pending"

    @pytest.mark.parametrize("terminal_state", ["completed", "failed-terminal", "cancelled"])
    def test_reopened_terminal_dry_run_no_change(self, db_conn, terminal_state):
        db_conn.execute(
            "INSERT INTO issues (area, number, state) VALUES ('client', 21, ?)",
            (terminal_state,),
        )
        db_conn.commit()

        from orchctl.commands.reconcile import _enqueue_or_reopen

        _enqueue_or_reopen(db_conn, "client", 21, dry_run=True)

        state = db_conn.execute(
            "SELECT state FROM issues WHERE area='client' AND number=21"
        ).fetchone()["state"]
        assert state == terminal_state

    @pytest.mark.parametrize("non_reopen_state", ["needs-human", "blocked-failed-dependency"])
    def test_non_reopen_terminal_not_touched(self, db_conn, non_reopen_state):
        db_conn.execute(
            "INSERT INTO issues (area, number, state) VALUES ('client', 22, ?)",
            (non_reopen_state,),
        )
        db_conn.commit()

        from orchctl.commands.reconcile import _enqueue_or_reopen

        _enqueue_or_reopen(db_conn, "client", 22, dry_run=False)

        state = db_conn.execute(
            "SELECT state FROM issues WHERE area='client' AND number=22"
        ).fetchone()["state"]
        assert state == non_reopen_state


# ---------------------------------------------------------------------------
# _discovery_pass — reconcile integration
# ---------------------------------------------------------------------------


def _make_gh_list_fn(*issue_numbers: int) -> MagicMock:
    """Return a mock gh_list_fn that yields GitHubIssue objects for given numbers."""
    issues = [GitHubIssue(number=n, title=f"Issue #{n}") for n in issue_numbers]
    return MagicMock(return_value=issues)


class TestDiscoveryPass:
    def test_disabled_by_default_noop(self, tmp_db):
        """Discovery is off by default — gh_list_fn is never called."""
        runner = CliRunner()
        runner.invoke(cli, ["--db", str(tmp_db), "init"])

        gh_fn = _make_gh_list_fn(100)
        from orchctl.commands.reconcile import _run_pass
        from orchctl.db.connection import get_db

        conn = get_db(str(tmp_db))
        from orchctl.db.lease import acquire, release

        pid = 1234
        acquire(conn, "client", pid)
        _run_pass(conn, "client", pid, dry_run=False, gh_list_fn=gh_fn)
        release(conn, "client", pid)
        conn.close()

        gh_fn.assert_not_called()

    def test_discovery_enqueues_new_issues(self, tmp_db):
        """With discovery_enabled=true, new GitHub issues are inserted as pending.

        max_concurrent=0 blocks the dispatch pass so we can observe the pending state.
        """
        runner = CliRunner()
        runner.invoke(cli, ["--db", str(tmp_db), "init"])

        conn_setup = get_db(str(tmp_db))
        conn_setup.execute("UPDATE config SET value='true' WHERE key='discovery_enabled'")
        conn_setup.execute("UPDATE config SET value='0' WHERE key='max_concurrent'")
        conn_setup.commit()
        conn_setup.close()

        gh_fn = _make_gh_list_fn(55, 56)
        from orchctl.commands.reconcile import _run_pass
        from orchctl.db.lease import acquire, release

        conn = get_db(str(tmp_db))
        pid = 1234
        acquire(conn, "client", pid)
        _run_pass(conn, "client", pid, dry_run=False, gh_list_fn=gh_fn)
        release(conn, "client", pid)

        rows = conn.execute(
            "SELECT number, state FROM issues WHERE area='client' ORDER BY number"
        ).fetchall()
        conn.close()

        numbers = {r["number"]: r["state"] for r in rows}
        assert numbers[55] == "pending"
        assert numbers[56] == "pending"

    def test_discovery_reenqueues_reopened_issue(self, tmp_db):
        """Completed issue that GitHub shows open is re-enqueued (dispatched in same cycle).

        max_concurrent=0 blocks dispatch so the pending state is observable.
        """
        runner = CliRunner()
        runner.invoke(cli, ["--db", str(tmp_db), "init"])

        conn_setup = get_db(str(tmp_db))
        conn_setup.execute("UPDATE config SET value='true' WHERE key='discovery_enabled'")
        conn_setup.execute("UPDATE config SET value='0' WHERE key='max_concurrent'")
        conn_setup.execute(
            "INSERT INTO issues (area, number, state) VALUES ('client', 77, 'completed')"
        )
        conn_setup.commit()
        conn_setup.close()

        gh_fn = _make_gh_list_fn(77)
        from orchctl.commands.reconcile import _run_pass
        from orchctl.db.lease import acquire, release

        conn = get_db(str(tmp_db))
        pid = 1234
        acquire(conn, "client", pid)
        _run_pass(conn, "client", pid, dry_run=False, gh_list_fn=gh_fn)
        release(conn, "client", pid)

        state = conn.execute(
            "SELECT state FROM issues WHERE area='client' AND number=77"
        ).fetchone()["state"]
        conn.close()
        assert state == "pending"

    def test_discovery_github_error_is_nonfatal(self, tmp_db):
        """A GitHubError from the gh CLI does not abort the reconcile pass."""
        runner = CliRunner()
        runner.invoke(cli, ["--db", str(tmp_db), "init"])

        conn_setup = get_db(str(tmp_db))
        conn_setup.execute("UPDATE config SET value='true' WHERE key='discovery_enabled'")
        conn_setup.execute(
            "INSERT INTO issues (area, number, state) VALUES ('client', 1, 'pending')"
        )
        conn_setup.commit()
        conn_setup.close()

        gh_fn = MagicMock(side_effect=GitHubError("network error"))
        dispatched = []
        from orchctl.commands.reconcile import _run_pass
        from orchctl.db.lease import acquire, release

        conn = get_db(str(tmp_db))
        pid = 1234
        acquire(conn, "client", pid)
        _run_pass(
            conn,
            "client",
            pid,
            dry_run=False,
            dispatch_fn=lambda area, iid, num, aid: dispatched.append(num),
            gh_list_fn=gh_fn,
        )
        release(conn, "client", pid)
        conn.close()

        # Dispatch still ran despite the GitHub error
        assert 1 in dispatched

    def test_discovery_lease_loss_aborts(self, tmp_db):
        """Lease loss during discovery returns False and stops the pass."""
        runner = CliRunner()
        runner.invoke(cli, ["--db", str(tmp_db), "init"])

        conn_setup = get_db(str(tmp_db))
        conn_setup.execute("UPDATE config SET value='true' WHERE key='discovery_enabled'")
        conn_setup.commit()
        conn_setup.close()

        gh_fn = _make_gh_list_fn(10)

        with patch("orchctl.commands.reconcile.renew", return_value=False):
            from orchctl.commands.reconcile import _discovery_pass
            from orchctl.db.connection import get_db as _gdb

            conn = _gdb(str(tmp_db))
            config = {
                "discovery_enabled": True,
                "scope_include_labels": [],
                "scope_exclude_labels": [],
                "scope_milestone": "",
                "scope_allow_unassigned": True,
            }
            result = _discovery_pass(conn, "client", 9999, dry_run=False, config=config, gh_list_fn=gh_fn)
            conn.close()

        assert result is False

    def test_discovery_dry_run_does_not_insert(self, tmp_db):
        """--dry-run reports new issues but does not write to DB."""
        runner = CliRunner()
        runner.invoke(cli, ["--db", str(tmp_db), "init"])

        conn_setup = get_db(str(tmp_db))
        conn_setup.execute("UPDATE config SET value='true' WHERE key='discovery_enabled'")
        conn_setup.commit()
        conn_setup.close()

        gh_fn = _make_gh_list_fn(99)
        from orchctl.commands.reconcile import _run_pass
        from orchctl.db.lease import acquire, release

        conn = get_db(str(tmp_db))
        pid = 1234
        acquire(conn, "client", pid)
        _run_pass(conn, "client", pid, dry_run=True, gh_list_fn=gh_fn)
        release(conn, "client", pid)

        row = conn.execute(
            "SELECT id FROM issues WHERE area='client' AND number=99"
        ).fetchone()
        conn.close()
        assert row is None

    def test_discovery_skips_unmapped_area(self, tmp_db):
        """When an area has no AREA_REPOS entry, discovery logs a warning and continues."""
        runner = CliRunner()
        runner.invoke(cli, ["--db", str(tmp_db), "init"])

        conn_setup = get_db(str(tmp_db))
        conn_setup.execute("UPDATE config SET value='true' WHERE key='discovery_enabled'")
        conn_setup.commit()
        conn_setup.close()

        gh_fn = MagicMock(return_value=[])
        from orchctl.commands.reconcile import _discovery_pass
        from orchctl.db.connection import get_db as _gdb

        conn = _gdb(str(tmp_db))
        config = {
            "discovery_enabled": True,
            "scope_include_labels": [],
            "scope_exclude_labels": [],
            "scope_milestone": "",
            "scope_allow_unassigned": True,
        }
        # "unknown-area" is not in AREA_REPOS — should return True (non-fatal) without
        # calling gh_fn.
        result = _discovery_pass(conn, "unknown-area", 9999, dry_run=False, config=config, gh_list_fn=gh_fn)
        conn.close()

        assert result is True
        gh_fn.assert_not_called()

    def test_discovery_passes_scope_config_to_gh_fn(self, tmp_db):
        """scope config values are forwarded as kwargs to the gh list function."""
        runner = CliRunner()
        runner.invoke(cli, ["--db", str(tmp_db), "init"])

        conn_setup = get_db(str(tmp_db))
        conn_setup.execute("UPDATE config SET value='true' WHERE key='discovery_enabled'")
        conn_setup.execute("UPDATE config SET value='[\"stage-2\"]' WHERE key='scope_include_labels'")
        conn_setup.execute("UPDATE config SET value='[\"manual-hold\"]' WHERE key='scope_exclude_labels'")
        conn_setup.execute("UPDATE config SET value='v1' WHERE key='scope_milestone'")
        conn_setup.execute("UPDATE config SET value='false' WHERE key='scope_allow_unassigned'")
        conn_setup.commit()
        conn_setup.close()

        gh_fn = MagicMock(return_value=[])
        from orchctl.commands.reconcile import _run_pass
        from orchctl.db.lease import acquire, release

        conn = get_db(str(tmp_db))
        pid = 1234
        acquire(conn, "client", pid)
        _run_pass(conn, "client", pid, dry_run=False, gh_list_fn=gh_fn)
        release(conn, "client", pid)
        conn.close()

        gh_fn.assert_called_once()
        _, kwargs = gh_fn.call_args
        assert kwargs["include_labels"] == ["stage-2"]
        assert kwargs["exclude_labels"] == ["manual-hold"]
        assert kwargs["milestone"] == "v1"
        assert kwargs["allow_unassigned"] is False


# ---------------------------------------------------------------------------
# State machine re-open transitions
# ---------------------------------------------------------------------------


class TestReopenTransitions:
    @pytest.mark.parametrize("from_state", ["completed", "failed-terminal", "cancelled"])
    def test_terminal_state_can_reopen_to_pending(self, db_conn, from_state):
        from orchctl.state_machine import apply_issue_transition

        db_conn.execute(
            "INSERT INTO issues (area, number, state) VALUES ('client', 50, ?)",
            (from_state,),
        )
        db_conn.commit()
        issue_id = db_conn.execute(
            "SELECT id FROM issues WHERE area='client' AND number=50"
        ).fetchone()["id"]

        new_state = apply_issue_transition(db_conn, issue_id, "pending")
        assert new_state == "pending"

    @pytest.mark.parametrize("non_reopen_state", ["needs-human", "blocked-failed-dependency"])
    def test_operator_terminal_cannot_reopen(self, non_reopen_state):
        from orchctl.models import IssueState, ISSUE_TRANSITIONS
        from orchctl.state_machine import InvalidTransitionError, transition_issue

        with pytest.raises(InvalidTransitionError):
            transition_issue(non_reopen_state, "pending")


# ---------------------------------------------------------------------------
# Config: v5 defaults present after init
# ---------------------------------------------------------------------------


def test_config_v5_defaults_inserted(tmp_db):
    conn, _ = init_db(tmp_db)
    rows = {r["key"]: r["value"] for r in conn.execute("SELECT key, value FROM config")}
    conn.close()
    assert rows["discovery_enabled"] == "false"
    assert rows["scope_include_labels"] == "[]"
    assert rows["scope_exclude_labels"] == "[]"
    assert rows["scope_milestone"] == ""
    assert rows["scope_allow_unassigned"] == "true"


# ---------------------------------------------------------------------------
# CLI reconcile: discovery via --dry-run reports output
# ---------------------------------------------------------------------------


def test_reconcile_discovery_dry_run_reports_new_issue(tmp_path):
    runner = CliRunner()
    db = str(tmp_path / "test.db")
    runner.invoke(cli, ["--db", db, "init"])

    conn = get_db(db)
    conn.execute("UPDATE config SET value='true' WHERE key='discovery_enabled'")
    conn.commit()
    conn.close()

    fake_issue = GitHubIssue(number=101, title="New issue")

    with patch("orchctl.commands.reconcile.list_open_issues", return_value=[fake_issue]):
        result = runner.invoke(
            cli, ["--db", db, "reconcile", "--area", "client", "--dry-run"]
        )

    assert result.exit_code == 0, result.output
    assert "101" in result.output
    assert "dry-run" in result.output


# ---------------------------------------------------------------------------
# list_open_issues: timeout and limit-warning behaviour
# ---------------------------------------------------------------------------


class TestListOpenIssues:
    def test_timeout_expired_raises_github_error(self):
        """TimeoutExpired from subprocess is converted to GitHubError."""
        from orchctl.github import list_open_issues

        with patch(
            "orchctl.github.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="gh", timeout=30),
        ):
            with pytest.raises(GitHubError, match="timed out"):
                list_open_issues("owner/repo")

    def test_nonzero_exit_raises_github_error(self):
        """Non-zero returncode raises GitHubError."""
        from orchctl.github import list_open_issues
        from unittest.mock import MagicMock

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "authentication failed"

        with patch("orchctl.github.subprocess.run", return_value=mock_result):
            with pytest.raises(GitHubError, match="authentication failed"):
                list_open_issues("owner/repo")

    def test_limit_hit_emits_warning(self, capsys):
        """When gh returns exactly limit items, a warning is printed to stderr."""
        import subprocess as _sp
        from orchctl.github import list_open_issues, _GH_TIMEOUT
        from unittest.mock import MagicMock

        mock_result = MagicMock()
        mock_result.returncode = 0
        # Return exactly 2 items when limit=2 to trigger the warning
        mock_result.stdout = '[{"number":1,"title":"a","labels":[],"milestone":null,"assignees":[]},{"number":2,"title":"b","labels":[],"milestone":null,"assignees":[]}]'

        with patch("orchctl.github.subprocess.run", return_value=mock_result):
            issues = list_open_issues("owner/repo", limit=2)

        assert len(issues) == 2
        captured = capsys.readouterr()
        assert "hit issue limit" in captured.err

    def test_below_limit_no_warning(self, capsys):
        """When gh returns fewer items than limit, no warning is emitted."""
        from orchctl.github import list_open_issues
        from unittest.mock import MagicMock

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '[{"number":1,"title":"a","labels":[],"milestone":null,"assignees":[]}]'

        with patch("orchctl.github.subprocess.run", return_value=mock_result):
            issues = list_open_issues("owner/repo", limit=500)

        assert len(issues) == 1
        captured = capsys.readouterr()
        assert "hit issue limit" not in captured.err


# ---------------------------------------------------------------------------
# AREA_REPOS coverage: every reconcile-valid area must have a repo mapping
# ---------------------------------------------------------------------------


def test_area_repos_covers_all_reconcile_areas():
    """AREA_REPOS must map every area accepted by cmd_reconcile.

    This catches drift between github.py and the CLI's valid-area list.
    If an area is added to cmd_reconcile without updating AREA_REPOS,
    discovery would silently skip it.
    """
    import click
    from orchctl.commands.reconcile import cmd_reconcile
    from orchctl.github import AREA_REPOS

    # Extract the valid choices from the --area option
    area_param = next(p for p in cmd_reconcile.params if p.name == "area")
    valid_areas: set[str] = set(area_param.type.choices)

    missing = valid_areas - set(AREA_REPOS.keys())
    assert not missing, (
        f"AREA_REPOS is missing entries for areas: {missing}. "
        "Update orchctl/github.py to keep it in sync with the CLI."
    )


# ---------------------------------------------------------------------------
# _REOPEN_STATES: derived from ISSUE_TRANSITIONS (auto-sync smoke test)
# ---------------------------------------------------------------------------


def test_reopen_states_derived_from_transitions():
    """_REOPEN_STATES must equal the terminal states with a -> pending edge."""
    from orchctl.commands.reconcile import _REOPEN_STATES
    from orchctl.models import ISSUE_TRANSITIONS, IssueState, TERMINAL_ISSUE_STATES

    expected = frozenset(
        s.value
        for s, targets in ISSUE_TRANSITIONS.items()
        if s in TERMINAL_ISSUE_STATES and IssueState.PENDING in targets
    )
    assert _REOPEN_STATES == expected
