"""Tests for area validation and centralized area config."""
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from dev_pipeline.paths import (
    VALID_AREAS,
    area_repo_dir,
    area_repo_name,
    validate_area,
)


class TestValidateArea:
    def test_valid_areas_accepted(self):
        for area in ("client", "server", "workspace"):
            assert validate_area(area) == area

    def test_invalid_area_raises(self):
        with pytest.raises(ValueError, match="Unknown area"):
            validate_area("foo")

    def test_empty_area_raises(self):
        with pytest.raises(ValueError, match="Unknown area"):
            validate_area("")

    def test_case_sensitive(self):
        with pytest.raises(ValueError, match="Unknown area"):
            validate_area("Client")


class TestAreaRepoName:
    def test_client(self):
        assert area_repo_name("client") == "pyo-sh/pyosh-blog-fe"

    def test_server(self):
        assert area_repo_name("server") == "pyo-sh/pyosh-blog-be"

    def test_workspace(self):
        assert area_repo_name("workspace") == "pyo-sh/pyosh-blog-ai"

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            area_repo_name("nonexistent")


class TestAreaRepoDir:
    def test_client(self, tmp_path):
        assert area_repo_dir("client", tmp_path) == tmp_path / "client"

    def test_server(self, tmp_path):
        assert area_repo_dir("server", tmp_path) == tmp_path / "server"

    def test_workspace_is_root(self, tmp_path):
        assert area_repo_dir("workspace", tmp_path) == tmp_path

    def test_invalid_raises(self, tmp_path):
        with pytest.raises(ValueError):
            area_repo_dir("bogus", tmp_path)


class TestGithubClientRepoValidation:
    def test_invalid_area_raises_from_github_client(self):
        from dev_pipeline.github_client import _repo

        with pytest.raises(ValueError, match="Unknown area"):
            _repo("nonexistent")
