"""Tests for session-aware Codex auth preflight in _dispatch_codex.

Regression for: CODEX_API_KEY-only preflight incorrectly failing
when session-auth (codex login) is already valid.
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from dev_pipeline.command_runner import RunResult
from dev_pipeline.models import PipelineState, ReviewJobStatus
from dev_pipeline.state_store import state_write, state_read


def _make_run_result(rc=0, stdout="", stderr="", timed_out=False):
    return RunResult(command=[], rc=rc, stdout=stdout, stderr=stderr, timed_out=timed_out)


def _init_state(tmp_path, issue=1, area="client", pr=10):
    """Create minimal pipeline directories and write a running review job state."""
    for sub in [
        f".workspace/pipeline/{area}",
        f".workspace/pipeline/logs/{area}",
        ".workspace/messages",
        f".workspace/worktrees/{area}/issue-{issue}",
    ]:
        (tmp_path / sub).mkdir(parents=True, exist_ok=True)

    state_dict = {
        "version": 2,
        "issue": issue,
        "area": area,
        "pr": pr,
        "branch": f"feat/issue-{issue}",
        "paths": {
            "skillCwd": str(tmp_path),
            "repoDir": str(tmp_path / area),
            "worktreeDir": str(tmp_path / f".workspace/worktrees/{area}/issue-{issue}"),
        },
        "step": "review_dispatch",
        "lastReviewId": 0,
        "lastCommitSha": "abc123",
        "skipReview": False,
        "reviewResolveRound": 0,
        "maxReviewResolveRounds": 5,
        "stageRetries": {s: 0 for s in ["build", "review_dispatch", "review_wait", "review_process", "resolve", "merge", "log"]},
        "maxStageRetries": 3,
        "reviewJob": {"runId": "test-run", "status": "running", "startedAt": None, "finishedAt": None, "tool": "codex", "model": ""},
        "transitionLog": [],
        "recoveryLog": [],
        "updatedAt": None,
    }
    state = PipelineState.from_dict(state_dict)
    state_write(issue, area, tmp_path, state)
    return issue, area, pr


class TestDetectCodexAuth:
    def test_session_auth_valid_returns_session(self):
        from dev_pipeline.review_runner import _detect_codex_auth

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            mode, _ = _detect_codex_auth({})

        assert mode == "session"

    def test_session_auth_failed_api_key_present_returns_api(self):
        from dev_pipeline.review_runner import _detect_codex_auth

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            mode, auth_path = _detect_codex_auth({"CODEX_API_KEY": "sk-test"})

        assert mode == "api"
        assert auth_path is None

    def test_neither_present_returns_missing(self):
        from dev_pipeline.review_runner import _detect_codex_auth

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            mode, auth_path = _detect_codex_auth({})

        assert mode == "missing"
        assert auth_path is None

    def test_codex_not_installed_falls_back_to_api_key(self):
        """FileNotFoundError from missing codex binary must not crash auth detection."""
        from dev_pipeline.review_runner import _detect_codex_auth

        with patch("subprocess.run", side_effect=FileNotFoundError):
            mode, auth_path = _detect_codex_auth({"CODEX_API_KEY": "sk-test"})

        assert mode == "api"

    def test_codex_not_installed_no_key_returns_missing(self):
        from dev_pipeline.review_runner import _detect_codex_auth

        with patch("subprocess.run", side_effect=FileNotFoundError):
            mode, auth_path = _detect_codex_auth({})

        assert mode == "missing"

    def test_session_auth_seeds_auth_json_path_when_exists(self, tmp_path):
        """When session-auth is valid and auth.json exists, path is returned."""
        from dev_pipeline.review_runner import _detect_codex_auth

        codex_home = tmp_path / ".codex"
        codex_home.mkdir()
        auth_json = codex_home / "auth.json"
        auth_json.write_text('{"token":"fake"}')

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            mode, path = _detect_codex_auth({"CODEX_HOME": str(codex_home)})

        assert mode == "session"
        assert path == auth_json

    def test_session_auth_keyring_backed_returns_none_path(self, tmp_path):
        """When session-auth is valid but no auth.json (keyring-backed), path is None."""
        from dev_pipeline.review_runner import _detect_codex_auth

        codex_home = tmp_path / ".codex"
        codex_home.mkdir()
        # No auth.json - simulates keyring-backed auth

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            mode, path = _detect_codex_auth({"CODEX_HOME": str(codex_home)})

        assert mode == "session"
        assert path is None


class TestDispatchCodexAuthPreflight:
    def test_missing_auth_sets_failed_auth_status(self, tmp_path):
        """_dispatch_codex must set failed_auth and return 1 when no auth is available."""
        issue, area, pr = _init_state(tmp_path)

        with (
            patch("subprocess.run") as mock_run,
            patch("dev_pipeline.github_client.get_pr_base_ref", return_value="main"),
        ):
            # codex login status fails, no API key
            mock_run.return_value = MagicMock(returncode=1)

            from dev_pipeline import review_runner
            rc = review_runner._dispatch_codex(issue=issue, area=area, pr=pr, monorepo_root=tmp_path)

        assert rc == 1
        state = state_read(issue, area, tmp_path)
        assert state.review_job.status == ReviewJobStatus.FAILED_AUTH

    def test_session_auth_proceeds_without_api_key(self, tmp_path, monkeypatch):
        """_dispatch_codex must not fail when session-auth is valid and CODEX_API_KEY is absent."""
        issue, area, pr = _init_state(tmp_path)
        monkeypatch.delenv("CODEX_API_KEY", raising=False)

        review_json_content = '{"verdict":"comment","summary":"ok","issues":[]}'

        def fake_run(cmd, *, cwd=None, env=None, timeout=None, capture_output=False, replace_env=False):
            if "-o" in cmd:
                out_path = cmd[cmd.index("-o") + 1]
                Path(out_path).write_text(review_json_content)
            return _make_run_result(rc=0, stderr="codex progress")

        def fake_subprocess_run(cmd, **kwargs):
            # Both calls (codex login status + publisher) succeed
            return MagicMock(returncode=0, stdout="", stderr="")

        with (
            patch("subprocess.run", side_effect=fake_subprocess_run),
            patch("dev_pipeline.review_runner.run", side_effect=fake_run),
            patch("dev_pipeline.github_client.get_pr_base_ref", return_value="main"),
            patch("dev_pipeline.github_client.check_review_exists", return_value=None),
        ):
            from dev_pipeline import review_runner
            rc = review_runner._dispatch_codex(issue=issue, area=area, pr=pr, monorepo_root=tmp_path)

        state = state_read(issue, area, tmp_path)
        # Status must NOT be failed_auth - auth stage was passed
        assert state.review_job.status != ReviewJobStatus.FAILED_AUTH


class TestExplicitFailureStatusPreservation:
    """dispatch_review() must preserve all explicit failure statuses."""

    def _run_dispatch_with_fake_inner(self, tmp_path, explicit_status: str, tool="codex"):
        """Run dispatch_review with an inner dispatch that sets an explicit failure status."""
        issue, area, pr = _init_state(tmp_path)

        def fake_inner(*args, **kwargs):
            from dev_pipeline.state_store import state_update
            from datetime import datetime, timezone
            state_update(issue, area, tmp_path, {
                "reviewJob": {
                    "status": explicit_status,
                    "finishedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                }
            })
            return 1

        patch_target = f"dev_pipeline.review_runner._dispatch_{tool}"
        with patch(patch_target, side_effect=fake_inner):
            from dev_pipeline.review_runner import dispatch_review
            rc = dispatch_review(issue, area, pr, tmp_path, tool=tool)

        return rc, state_read(issue, area, tmp_path)

    @pytest.mark.parametrize("status", [
        "failed_parse",
        "failed_auth",
        "failed_publish",
        "failed_postcondition",
        "failed_dispatch",
    ])
    def test_explicit_failure_status_preserved(self, tmp_path, status):
        """dispatch_review() must not overwrite any explicit failure status with 'failed'."""
        rc, state = self._run_dispatch_with_fake_inner(tmp_path, status)
        assert rc == 1
        assert state.review_job.status.value == status, (
            f"REGRESSION: dispatch_review() overwrote {status!r} with "
            f"{state.review_job.status.value!r}. Explicit failure statuses must be preserved."
        )
