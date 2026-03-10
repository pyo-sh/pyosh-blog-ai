"""Tests for command_runner.run replace_env behavior and CLAUDECODE end-to-end."""
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from dev_pipeline.command_runner import RunResult, run


class TestReplaceEnv:
    def test_default_merges_os_environ(self, monkeypatch):
        """Without replace_env, os.environ is merged with env."""
        monkeypatch.setenv("EXISTING_VAR", "from_environ")
        captured = {}

        def fake_subprocess_run(cmd, **kwargs):
            captured["env"] = kwargs.get("env")

            class R:
                returncode = 0
                stdout = ""
                stderr = ""

            return R()

        with patch("subprocess.run", side_effect=fake_subprocess_run):
            run(["echo"], env={"NEW_VAR": "added"})

        assert captured["env"]["EXISTING_VAR"] == "from_environ"
        assert captured["env"]["NEW_VAR"] == "added"

    def test_replace_env_uses_exact_env(self, monkeypatch):
        """With replace_env=True, only the provided env is used."""
        monkeypatch.setenv("SHOULD_NOT_APPEAR", "leaked")
        captured = {}

        def fake_subprocess_run(cmd, **kwargs):
            captured["env"] = kwargs.get("env")

            class R:
                returncode = 0
                stdout = ""
                stderr = ""

            return R()

        custom_env = {"ONLY_THIS": "value", "PATH": "/usr/bin"}
        with patch("subprocess.run", side_effect=fake_subprocess_run):
            run(["echo"], env=custom_env, replace_env=True)

        assert "SHOULD_NOT_APPEAR" not in captured["env"]
        assert captured["env"]["ONLY_THIS"] == "value"

    def test_no_env_passes_none(self):
        """When env is None, subprocess gets None (inherits)."""
        captured = {}

        def fake_subprocess_run(cmd, **kwargs):
            captured["env"] = kwargs.get("env")

            class R:
                returncode = 0
                stdout = ""
                stderr = ""

            return R()

        with patch("subprocess.run", side_effect=fake_subprocess_run):
            run(["echo"])

        assert captured["env"] is None


class TestClaudeCodeEnvEndToEnd:
    """End-to-end test: CLAUDECODE must NOT appear in the subprocess env
    when _dispatch_claude uses replace_env=True."""

    def test_claudecode_stripped_end_to_end(self, tmp_path, monkeypatch):
        (tmp_path / ".workspace" / "pipeline" / "client").mkdir(parents=True)
        (tmp_path / ".workspace" / "pipeline" / "logs" / "client").mkdir(parents=True)
        (tmp_path / ".workspace" / "messages").mkdir(parents=True)
        (tmp_path / ".workspace" / "worktrees" / "client").mkdir(parents=True)

        monkeypatch.setenv("CLAUDECODE", "1")

        # Capture the actual env passed to subprocess.run (not command_runner.run)
        captured_subprocess_env = {}

        def fake_subprocess_run(cmd, **kwargs):
            env = kwargs.get("env")
            if env is not None:
                captured_subprocess_env.update(env)

            class R:
                returncode = 0
                stdout = "review output"
                stderr = ""

            return R()

        with patch("subprocess.run", side_effect=fake_subprocess_run):
            from dev_pipeline import review_runner
            review_runner._dispatch_claude(
                issue=1, area="client", pr=10,
                monorepo_root=tmp_path, model="",
            )

        assert "CLAUDECODE" not in captured_subprocess_env, (
            "CLAUDECODE must be stripped from the actual subprocess environment"
        )
        assert captured_subprocess_env.get("PIPELINE_AREA") == "client"
        assert captured_subprocess_env.get("PIPELINE_PR") == "10"
