"""Shared fixtures for dev_log tests."""
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


@pytest.fixture
def monorepo_root(tmp_path):
    """Create a minimal monorepo-like directory tree."""
    (tmp_path / ".workspace" / "worktrees").mkdir(parents=True)
    (tmp_path / ".agents").mkdir()
    (tmp_path / "docs" / "workspace" / "findings").mkdir(parents=True)
    (tmp_path / "docs" / "workspace" / "progress").mkdir(parents=True)
    (tmp_path / "docs" / "workspace" / "decisions").mkdir(parents=True)
    return tmp_path
