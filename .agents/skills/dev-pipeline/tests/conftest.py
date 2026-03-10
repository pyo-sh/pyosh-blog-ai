"""Shared fixtures for dev_pipeline tests."""
import json
import sys
from pathlib import Path

import pytest

# Ensure the scripts directory is on sys.path so `dev_pipeline` is importable
SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


@pytest.fixture
def monorepo_root(tmp_path):
    """Create a minimal monorepo-like directory tree under tmp_path."""
    (tmp_path / ".workspace" / "pipeline").mkdir(parents=True)
    (tmp_path / ".workspace" / "messages").mkdir(parents=True)
    (tmp_path / ".workspace" / "worktrees").mkdir(parents=True)
    return tmp_path


@pytest.fixture
def sample_state() -> dict:
    """Return a minimal v2 state dict matching the camelCase JSON schema."""
    return {
        "version": 2,
        "issue": 42,
        "area": "client",
        "pr": 129,
        "branch": "feat/issue-42",
        "paths": {
            "skillCwd": "/workspace",
            "repoDir": "/workspace/client",
            "worktreeDir": "/workspace/.workspace/worktrees/client/issue-42",
        },
        "step": "review_dispatch",
        "lastReviewId": 0,
        "lastCommitSha": "abc123",
        "skipReview": False,
        "reviewResolveRound": 0,
        "maxReviewResolveRounds": 5,
        "stageRetries": {
            "build": 0,
            "review_dispatch": 0,
            "review_wait": 0,
            "review_process": 0,
            "resolve": 0,
            "merge": 0,
            "log": 0,
        },
        "maxStageRetries": 3,
        "reviewJob": {
            "runId": "",
            "status": "idle",
            "startedAt": None,
            "finishedAt": None,
            "tool": "",
            "model": "",
        },
        "transitionLog": [],
        "recoveryLog": [],
        "updatedAt": None,
    }


@pytest.fixture
def state_file(monorepo_root, sample_state):
    """Write sample_state to the expected state file location and return the path."""
    area = sample_state["area"]
    issue = sample_state["issue"]
    state_dir = monorepo_root / ".workspace" / "pipeline" / area
    state_dir.mkdir(parents=True, exist_ok=True)
    path = state_dir / f"issue-{issue}.state.json"
    path.write_text(json.dumps(sample_state, indent=2))
    return path
