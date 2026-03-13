"""Tests for event log and webhook notification."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from orchctl.cli import cli
from orchctl.db.connection import get_db
from orchctl.events import (
    EVENT_ATTEMPT_COMPLETED,
    EVENT_ISSUE_STATE_CHANGED,
    dispatch_webhook,
    emit_event,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def db_path(tmp_path: Path) -> str:
    return str(tmp_path / "test.db")


def _init_db(runner, db_path):
    result = runner.invoke(cli, ["--db", db_path, "init"])
    assert result.exit_code == 0, result.output


# ---------------------------------------------------------------------------
# emit_event tests
# ---------------------------------------------------------------------------

class TestEmitEvent:
    def test_inserts_row(self, runner, db_path):
        _init_db(runner, db_path)
        conn = get_db(db_path)
        event_id = emit_event(conn, EVENT_ISSUE_STATE_CHANGED, area="workspace", payload={"from": "pending", "to": "dispatched"})
        conn.close()

        conn = get_db(db_path)
        row = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
        conn.close()

        assert row is not None
        assert row["event_type"] == EVENT_ISSUE_STATE_CHANGED
        assert row["area"] == "workspace"
        payload = json.loads(row["payload"])
        assert payload["from"] == "pending"

    def test_nullable_area_and_issue(self, runner, db_path):
        _init_db(runner, db_path)
        conn = get_db(db_path)
        event_id = emit_event(conn, "global_event")
        conn.close()

        conn = get_db(db_path)
        row = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
        conn.close()

        assert row["area"] is None
        assert row["issue_id"] is None

    def test_default_empty_payload(self, runner, db_path):
        _init_db(runner, db_path)
        conn = get_db(db_path)
        emit_event(conn, "test_event", area="workspace")
        conn.close()

        conn = get_db(db_path)
        row = conn.execute("SELECT payload FROM events WHERE event_type = 'test_event'").fetchone()
        conn.close()
        assert json.loads(row["payload"]) == {}

    def test_does_not_fire_webhook_when_disabled(self, runner, db_path):
        _init_db(runner, db_path)
        conn = get_db(db_path)
        with patch("orchctl.events.dispatch_webhook") as mock_wh:
            emit_event(conn, EVENT_ISSUE_STATE_CHANGED, area="workspace")
            mock_wh.assert_not_called()
        conn.close()

    def test_fires_webhook_when_enabled(self, runner, db_path):
        _init_db(runner, db_path)
        conn = get_db(db_path)
        # Enable webhook
        conn.execute("UPDATE config SET value = 'true' WHERE key = 'webhook_enabled'")
        conn.execute("UPDATE config SET value = 'http://example.test/hook' WHERE key = 'webhook_url'")
        conn.commit()

        with patch("orchctl.events.dispatch_webhook", return_value=(True, "200")) as mock_wh:
            emit_event(conn, EVENT_ISSUE_STATE_CHANGED, area="workspace")
            mock_wh.assert_called_once()
        conn.close()

    def test_webhook_event_filter_allows_matching(self, runner, db_path):
        _init_db(runner, db_path)
        conn = get_db(db_path)
        conn.execute("UPDATE config SET value = 'true' WHERE key = 'webhook_enabled'")
        conn.execute("UPDATE config SET value = 'http://example.test/hook' WHERE key = 'webhook_url'")
        conn.execute(
            "UPDATE config SET value = ? WHERE key = 'webhook_events'",
            (json.dumps([EVENT_ISSUE_STATE_CHANGED]),),
        )
        conn.commit()

        with patch("orchctl.events.dispatch_webhook", return_value=(True, "200")) as mock_wh:
            emit_event(conn, EVENT_ISSUE_STATE_CHANGED, area="workspace")
            mock_wh.assert_called_once()
        conn.close()

    def test_webhook_event_filter_blocks_non_matching(self, runner, db_path):
        _init_db(runner, db_path)
        conn = get_db(db_path)
        conn.execute("UPDATE config SET value = 'true' WHERE key = 'webhook_enabled'")
        conn.execute("UPDATE config SET value = 'http://example.test/hook' WHERE key = 'webhook_url'")
        conn.execute(
            "UPDATE config SET value = ? WHERE key = 'webhook_events'",
            (json.dumps([EVENT_ATTEMPT_COMPLETED]),),
        )
        conn.commit()

        with patch("orchctl.events.dispatch_webhook", return_value=(True, "200")) as mock_wh:
            emit_event(conn, EVENT_ISSUE_STATE_CHANGED, area="workspace")
            mock_wh.assert_not_called()
        conn.close()

    def test_webhook_failure_logged_to_stderr(self, runner, db_path, capsys):
        _init_db(runner, db_path)
        conn = get_db(db_path)
        conn.execute("UPDATE config SET value = 'true' WHERE key = 'webhook_enabled'")
        conn.execute("UPDATE config SET value = 'http://example.test/hook' WHERE key = 'webhook_url'")
        conn.commit()

        with patch("orchctl.events.dispatch_webhook", return_value=(False, "connection refused")):
            emit_event(conn, EVENT_ISSUE_STATE_CHANGED, area="workspace")
        conn.close()

        captured = capsys.readouterr()
        assert "webhook delivery failed" in captured.err
        assert "connection refused" in captured.err


# ---------------------------------------------------------------------------
# dispatch_webhook tests
# ---------------------------------------------------------------------------

class TestDispatchWebhook:
    def test_success(self):
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.status = 200

        with patch("urllib.request.urlopen", return_value=mock_resp):
            ok, detail = dispatch_webhook("http://example.test/hook", '{"test": 1}')

        assert ok is True
        assert detail == "200"

    def test_http_error(self):
        import urllib.error

        with patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError(None, 503, "Service Unavailable", {}, None)):
            ok, detail = dispatch_webhook("http://example.test/hook", '{"test": 1}')

        assert ok is False
        assert "503" in detail

    def test_network_error(self):
        with patch("urllib.request.urlopen", side_effect=OSError("connection refused")):
            ok, detail = dispatch_webhook("http://example.test/hook", '{"test": 1}')

        assert ok is False
        assert "connection refused" in detail


# ---------------------------------------------------------------------------
# CLI: events list
# ---------------------------------------------------------------------------

class TestEventsListCmd:
    def test_requires_init(self, runner, db_path):
        result = runner.invoke(cli, ["--db", db_path, "events", "list"])
        assert result.exit_code != 0
        assert "not initialised" in result.output

    def test_empty(self, runner, db_path):
        _init_db(runner, db_path)
        result = runner.invoke(cli, ["--db", db_path, "events", "list"])
        assert result.exit_code == 0
        assert "No events found" in result.output

    def test_lists_events(self, runner, db_path):
        _init_db(runner, db_path)
        conn = get_db(db_path)
        emit_event(conn, EVENT_ISSUE_STATE_CHANGED, area="workspace")
        emit_event(conn, EVENT_ATTEMPT_COMPLETED, area="client")
        conn.close()

        result = runner.invoke(cli, ["--db", db_path, "events", "list"])
        assert result.exit_code == 0
        assert EVENT_ISSUE_STATE_CHANGED in result.output
        assert EVENT_ATTEMPT_COMPLETED in result.output

    def test_filter_by_area(self, runner, db_path):
        _init_db(runner, db_path)
        conn = get_db(db_path)
        emit_event(conn, EVENT_ISSUE_STATE_CHANGED, area="workspace")
        emit_event(conn, EVENT_ATTEMPT_COMPLETED, area="client")
        conn.close()

        result = runner.invoke(cli, ["--db", db_path, "events", "list", "--area", "workspace"])
        assert result.exit_code == 0
        assert EVENT_ISSUE_STATE_CHANGED in result.output
        assert "client" not in result.output

    def test_filter_by_type(self, runner, db_path):
        _init_db(runner, db_path)
        conn = get_db(db_path)
        emit_event(conn, EVENT_ISSUE_STATE_CHANGED, area="workspace")
        emit_event(conn, EVENT_ATTEMPT_COMPLETED, area="workspace")
        conn.close()

        result = runner.invoke(cli, ["--db", db_path, "events", "list", "--type", EVENT_ATTEMPT_COMPLETED])
        assert result.exit_code == 0
        assert EVENT_ATTEMPT_COMPLETED in result.output
        assert EVENT_ISSUE_STATE_CHANGED not in result.output

    def test_json_output(self, runner, db_path):
        _init_db(runner, db_path)
        conn = get_db(db_path)
        emit_event(conn, "x_event", area="workspace", payload={"k": "v"})
        conn.close()

        result = runner.invoke(cli, ["--db", db_path, "events", "list", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert data[0]["event_type"] == "x_event"

    def test_limit(self, runner, db_path):
        _init_db(runner, db_path)
        conn = get_db(db_path)
        for i in range(10):
            emit_event(conn, "evt", area="workspace", payload={"i": i})
        conn.close()

        result = runner.invoke(cli, ["--db", db_path, "events", "list", "--limit", "3", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 3


# ---------------------------------------------------------------------------
# CLI: notify
# ---------------------------------------------------------------------------

class TestNotifyCmd:
    def test_status_requires_init(self, runner, db_path):
        result = runner.invoke(cli, ["--db", db_path, "notify", "status"])
        assert result.exit_code != 0

    def test_status_default(self, runner, db_path):
        _init_db(runner, db_path)
        result = runner.invoke(cli, ["--db", db_path, "notify", "status"])
        assert result.exit_code == 0
        assert "disabled" in result.output

    def test_set_url(self, runner, db_path):
        _init_db(runner, db_path)
        result = runner.invoke(
            cli, ["--db", db_path, "notify", "set", "--url", "http://hook.example/path"]
        )
        assert result.exit_code == 0

        result = runner.invoke(cli, ["--db", db_path, "notify", "status"])
        assert "http://hook.example/path" in result.output

    def test_enable_disable(self, runner, db_path):
        _init_db(runner, db_path)
        runner.invoke(cli, ["--db", db_path, "notify", "set", "--enable"])
        result = runner.invoke(cli, ["--db", db_path, "notify", "status"])
        assert "enabled" in result.output

        runner.invoke(cli, ["--db", db_path, "notify", "set", "--disable"])
        result = runner.invoke(cli, ["--db", db_path, "notify", "status"])
        assert "disabled" in result.output

    def test_set_events_list(self, runner, db_path):
        _init_db(runner, db_path)
        runner.invoke(
            cli,
            ["--db", db_path, "notify", "set", "--events", "issue_state_changed,attempt_failed"],
        )
        result = runner.invoke(cli, ["--db", db_path, "notify", "status"])
        assert result.exit_code == 0
        assert "issue_state_changed" in result.output
        assert "attempt_failed" in result.output

    def test_set_events_all(self, runner, db_path):
        _init_db(runner, db_path)
        runner.invoke(cli, ["--db", db_path, "notify", "set", "--events", "all"])
        result = runner.invoke(cli, ["--db", db_path, "notify", "status"])
        assert "(all)" in result.output

    def test_set_url_rejects_non_http(self, runner, db_path):
        _init_db(runner, db_path)
        result = runner.invoke(cli, ["--db", db_path, "notify", "set", "--url", "ftp://example.test/hook"])
        assert result.exit_code != 0
        assert "http or https" in result.output

    def test_set_url_rejects_file_scheme(self, runner, db_path):
        _init_db(runner, db_path)
        result = runner.invoke(cli, ["--db", db_path, "notify", "set", "--url", "file:///etc/passwd"])
        assert result.exit_code != 0
        assert "http or https" in result.output

    def test_set_url_empty_string_allowed(self, runner, db_path):
        _init_db(runner, db_path)
        result = runner.invoke(cli, ["--db", db_path, "notify", "set", "--url", ""])
        assert result.exit_code == 0

    def test_status_json(self, runner, db_path):
        _init_db(runner, db_path)
        result = runner.invoke(cli, ["--db", db_path, "notify", "status", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "webhook_url" in data
        assert "webhook_enabled" in data
        assert "webhook_events" in data

    def test_test_no_url_configured(self, runner, db_path):
        _init_db(runner, db_path)
        result = runner.invoke(cli, ["--db", db_path, "notify", "test"])
        assert result.exit_code != 0
        assert "No webhook URL" in result.output

    def test_test_rejects_non_http_url(self, runner, db_path):
        _init_db(runner, db_path)
        result = runner.invoke(cli, ["--db", db_path, "notify", "test", "--url", "ftp://example.test/hook"])
        assert result.exit_code != 0
        assert "http or https" in result.output

    def test_test_success(self, runner, db_path):
        _init_db(runner, db_path)
        runner.invoke(
            cli, ["--db", db_path, "notify", "set", "--url", "http://example.test/hook"]
        )

        with patch("orchctl.commands.notify.dispatch_webhook", return_value=(True, "200")):
            result = runner.invoke(
                cli, ["--db", db_path, "notify", "test", "--url", "http://example.test/hook"]
            )
        assert result.exit_code == 0
        assert "200" in result.output

    def test_test_failure(self, runner, db_path):
        _init_db(runner, db_path)
        with patch("orchctl.commands.notify.dispatch_webhook", return_value=(False, "connection refused")):
            result = runner.invoke(
                cli, ["--db", db_path, "notify", "test", "--url", "http://example.test/hook"]
            )
        assert result.exit_code != 0
        assert "connection refused" in result.output
