"""Tests for CLI commands."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from orchctl.cli import cli


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def db_path(tmp_path: Path) -> str:
    return str(tmp_path / "test.db")


def test_help(runner):
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "orchctl" in result.output


def test_init(runner, db_path):
    result = runner.invoke(cli, ["--db", db_path, "init"])
    assert result.exit_code == 0, result.output
    assert "initialized" in result.output


def test_status_empty(runner, db_path):
    runner.invoke(cli, ["--db", db_path, "init"])
    result = runner.invoke(cli, ["--db", db_path, "status"])
    assert result.exit_code == 0, result.output
    assert "Active attempts: 0" in result.output


def test_status_json_empty(runner, db_path):
    import json

    runner.invoke(cli, ["--db", db_path, "init"])
    result = runner.invoke(cli, ["--db", db_path, "status", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert "issues" in data
    assert "active_attempts" in data
    assert data["active_attempts"] == []


def test_doctor_healthy(runner, db_path):
    runner.invoke(cli, ["--db", db_path, "init"])
    result = runner.invoke(cli, ["--db", db_path, "doctor"])
    assert result.exit_code == 0, result.output
    assert "OK" in result.output


def test_doctor_json_healthy(runner, db_path):
    import json

    runner.invoke(cli, ["--db", db_path, "init"])
    result = runner.invoke(cli, ["--db", db_path, "doctor", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["healthy"] is True
    assert data["findings"] == []


def test_reconcile_stub(runner, db_path):
    result = runner.invoke(cli, ["--db", db_path, "reconcile"])
    assert result.exit_code == 0, result.output
    assert "not yet implemented" in result.output


def test_status_requires_init(runner, db_path):
    result = runner.invoke(cli, ["--db", db_path, "status"])
    assert result.exit_code != 0
    assert "not initialised" in result.output


def test_doctor_requires_init(runner, db_path):
    result = runner.invoke(cli, ["--db", db_path, "doctor"])
    assert result.exit_code != 0
    assert "not initialised" in result.output
