"""Tests for dev_pipeline.steps module."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from dev_pipeline.models import (
    PipelineState,
    PipelineStep,
    Paths,
    ReviewJob,
    ReviewJobStatus,
)
from dev_pipeline.review_normalizer import ReviewCounts
from dev_pipeline.state_store import state_read, state_write
from dev_pipeline.steps import (
    StepResult,
    step_build_setup,
    step_build_finalize,
    step_review_dispatch,
    step_review_wait,
    step_review_process,
    step_suggestion_decide,
    step_resolve_setup,
    step_resolve_finalize,
    step_merge,
    step_cleanup_wt,
    step_log_finalize,
)

# Monkeypatch target prefix for steps module (module-level imports)
S = "dev_pipeline.steps"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def monorepo_root(tmp_path):
    (tmp_path / ".workspace" / "pipeline").mkdir(parents=True)
    (tmp_path / ".workspace" / "messages").mkdir(parents=True)
    (tmp_path / ".workspace" / "worktrees").mkdir(parents=True)
    return tmp_path


def _write_state(monorepo_root, issue, area, **overrides):
    """Helper to write a state file with common defaults."""
    from dev_pipeline.paths import pipeline_init
    pipeline_init(area, monorepo_root)

    defaults = dict(
        issue=issue,
        area=area,
        pr=99,
        branch="feat/issue-99",
        step=PipelineStep.BUILD,
        paths=Paths(
            skill_cwd=str(monorepo_root),
            repo_dir=str(monorepo_root),
            worktree_dir=str(monorepo_root / ".workspace" / "worktrees" / area / f"issue-{issue}"),
        ),
        last_commit_sha="a" * 40,
        review_job=ReviewJob(),
    )
    defaults.update(overrides)
    state = PipelineState(**defaults)
    state_write(issue, area, monorepo_root, state)
    return state


# ---------------------------------------------------------------------------
# build setup
# ---------------------------------------------------------------------------

class TestBuildSetup:
    def test_creates_state(self, monorepo_root, monkeypatch):
        monkeypatch.setattr(f"{S}.fetch", lambda *a, **kw: True)
        monkeypatch.setattr(f"{S}.rebase", lambda *a, **kw: True)

        result = step_build_setup(42, "workspace", monorepo_root)

        assert result.action == "ready"
        assert result.data["repo"] == "pyo-sh/pyosh-blog-ai"
        state = state_read(42, "workspace", monorepo_root)
        assert state.step == PipelineStep.BUILD

    def test_existing_state_not_overwritten(self, monorepo_root, monkeypatch):
        monkeypatch.setattr(f"{S}.fetch", lambda *a, **kw: True)
        monkeypatch.setattr(f"{S}.rebase", lambda *a, **kw: True)

        _write_state(monorepo_root, 42, "workspace", pr=123, step=PipelineStep.RESOLVE)
        result = step_build_setup(42, "workspace", monorepo_root)

        assert result.action == "ready"
        state = state_read(42, "workspace", monorepo_root)
        assert state.pr == 123

    def test_rebase_fail_falls_back_to_merge(self, monorepo_root, monkeypatch):
        monkeypatch.setattr(f"{S}.fetch", lambda *a, **kw: True)
        monkeypatch.setattr(f"{S}.rebase", lambda *a, **kw: False)
        merge_called = []
        monkeypatch.setattr(
            f"{S}.merge_no_edit",
            lambda *a, **kw: merge_called.append(1) or True,
        )

        result = step_build_setup(42, "workspace", monorepo_root)
        assert result.action == "ready"
        assert len(merge_called) == 1


# ---------------------------------------------------------------------------
# build finalize
# ---------------------------------------------------------------------------

class TestBuildFinalize:
    def test_reads_pr(self, monorepo_root, monkeypatch):
        _write_state(monorepo_root, 42, "workspace")

        mock_run = MagicMock()
        branch_result = MagicMock(stdout="feat/issue-42\n", rc=0)
        pr_result = MagicMock(stdout="99\n", rc=0)
        mock_run.side_effect = [branch_result, pr_result]

        monkeypatch.setattr(f"{S}.run_cmd", mock_run)
        monkeypatch.setattr(f"{S}.rev_parse_head", lambda wt: "b" * 40)

        result = step_build_finalize(42, "workspace", monorepo_root)

        assert result.action == "continue"
        assert result.data["pr"] == 99
        assert result.data["branch"] == "feat/issue-42"
        assert result.data["lastCommitSha"] == "b" * 40

        state = state_read(42, "workspace", monorepo_root)
        assert state.step == PipelineStep.REVIEW_DISPATCH

    def test_no_pr_found(self, monorepo_root, monkeypatch):
        _write_state(monorepo_root, 42, "workspace")

        mock_run = MagicMock()
        branch_result = MagicMock(stdout="feat/issue-42\n", rc=0)
        pr_result = MagicMock(stdout="\n", rc=0)
        mock_run.side_effect = [branch_result, pr_result]

        monkeypatch.setattr(f"{S}.run_cmd", mock_run)
        monkeypatch.setattr(f"{S}.rev_parse_head", lambda wt: "b" * 40)

        result = step_build_finalize(42, "workspace", monorepo_root)
        assert result.action == "error"


# ---------------------------------------------------------------------------
# review dispatch
# ---------------------------------------------------------------------------

class TestReviewDispatch:
    def test_existing_review(self, monorepo_root, monkeypatch):
        _write_state(monorepo_root, 42, "workspace", step=PipelineStep.REVIEW_DISPATCH)
        monkeypatch.setattr(f"{S}.check_review_exists", lambda *a, **kw: 555)

        result = step_review_dispatch(42, "workspace", monorepo_root)
        assert result.action == "found"
        assert result.data["reviewId"] == 555

    def test_no_review_dispatches(self, monorepo_root, monkeypatch):
        _write_state(monorepo_root, 42, "workspace", step=PipelineStep.REVIEW_DISPATCH)
        monkeypatch.setattr(f"{S}.check_review_exists", lambda *a, **kw: None)

        result = step_review_dispatch(42, "workspace", monorepo_root)
        assert result.action == "dispatch"
        assert result.data["tool"] == "claude"

        state = state_read(42, "workspace", monorepo_root)
        assert state.step == PipelineStep.REVIEW_WAIT

    def test_gh_api_error(self, monorepo_root, monkeypatch):
        _write_state(monorepo_root, 42, "workspace", step=PipelineStep.REVIEW_DISPATCH)

        def raise_err(*a, **kw):
            raise RuntimeError("gh error")

        monkeypatch.setattr(f"{S}.check_review_exists", raise_err)

        result = step_review_dispatch(42, "workspace", monorepo_root)
        assert result.action == "error"


# ---------------------------------------------------------------------------
# review wait - bug fix #2 tests
# ---------------------------------------------------------------------------

class TestReviewWait:
    def test_review_found(self, monorepo_root, monkeypatch):
        _write_state(
            monorepo_root, 42, "workspace",
            step=PipelineStep.REVIEW_WAIT,
            review_job=ReviewJob(status=ReviewJobStatus.SUCCESS, tool="claude"),
        )
        monkeypatch.setattr(f"{S}.check_review_exists", lambda *a, **kw: 777)

        result = step_review_wait(42, "workspace", monorepo_root)
        assert result.action == "review"
        assert result.data["reviewId"] == 777

    def test_codex_failed_fallback(self, monorepo_root, monkeypatch):
        """Bug fix #2: codex FAILED triggers codex->claude fallback."""
        _write_state(
            monorepo_root, 42, "workspace",
            step=PipelineStep.REVIEW_WAIT,
            review_job=ReviewJob(status=ReviewJobStatus.FAILED, tool="codex"),
        )
        monkeypatch.setattr(f"{S}.check_review_exists", lambda *a, **kw: None)

        result = step_review_wait(42, "workspace", monorepo_root)
        assert result.action == "retry"
        assert result.data["tool"] == "claude"

    def test_codex_failed_parse_fallback(self, monorepo_root, monkeypatch):
        """Existing behavior preserved: codex FAILED_PARSE also triggers fallback."""
        _write_state(
            monorepo_root, 42, "workspace",
            step=PipelineStep.REVIEW_WAIT,
            review_job=ReviewJob(status=ReviewJobStatus.FAILED_PARSE, tool="codex"),
        )
        monkeypatch.setattr(f"{S}.check_review_exists", lambda *a, **kw: None)

        result = step_review_wait(42, "workspace", monorepo_root)
        assert result.action == "retry"
        assert result.data["tool"] == "claude"

    def test_codex_failed_auth_fallback(self, monorepo_root, monkeypatch):
        """Bug fix #2: codex FAILED_AUTH triggers fallback."""
        _write_state(
            monorepo_root, 42, "workspace",
            step=PipelineStep.REVIEW_WAIT,
            review_job=ReviewJob(status=ReviewJobStatus.FAILED_AUTH, tool="codex"),
        )
        monkeypatch.setattr(f"{S}.check_review_exists", lambda *a, **kw: None)

        result = step_review_wait(42, "workspace", monorepo_root)
        assert result.action == "retry"
        assert result.data["tool"] == "claude"

    def test_codex_failed_publish_fallback(self, monorepo_root, monkeypatch):
        """Bug fix #2: codex FAILED_PUBLISH triggers fallback."""
        _write_state(
            monorepo_root, 42, "workspace",
            step=PipelineStep.REVIEW_WAIT,
            review_job=ReviewJob(status=ReviewJobStatus.FAILED_PUBLISH, tool="codex"),
        )
        monkeypatch.setattr(f"{S}.check_review_exists", lambda *a, **kw: None)

        result = step_review_wait(42, "workspace", monorepo_root)
        assert result.action == "retry"
        assert result.data["tool"] == "claude"

    def test_claude_failed_escalates(self, monorepo_root, monkeypatch):
        """claude failure -> escalate (no double fallback)."""
        _write_state(
            monorepo_root, 42, "workspace",
            step=PipelineStep.REVIEW_WAIT,
            review_job=ReviewJob(status=ReviewJobStatus.FAILED, tool="claude"),
        )
        monkeypatch.setattr(f"{S}.check_review_exists", lambda *a, **kw: None)

        result = step_review_wait(42, "workspace", monorepo_root)
        assert result.action == "escalate"

    def test_success_no_review_escalates(self, monorepo_root, monkeypatch):
        """Job succeeded but no review on GitHub -> escalate."""
        _write_state(
            monorepo_root, 42, "workspace",
            step=PipelineStep.REVIEW_WAIT,
            review_job=ReviewJob(status=ReviewJobStatus.SUCCESS, tool="claude"),
        )
        monkeypatch.setattr(f"{S}.check_review_exists", lambda *a, **kw: None)

        result = step_review_wait(42, "workspace", monorepo_root)
        assert result.action == "escalate"

    def test_running_job_returns_pending(self, monorepo_root, monkeypatch):
        """Bug 1 fix: job status=running returns pending instead of escalate."""
        _write_state(
            monorepo_root, 42, "workspace",
            step=PipelineStep.REVIEW_WAIT,
            review_job=ReviewJob(status=ReviewJobStatus.RUNNING, tool="claude"),
        )
        monkeypatch.setattr(f"{S}.check_review_exists", lambda *a, **kw: None)

        result = step_review_wait(42, "workspace", monorepo_root)
        assert result.action == "pending"


# ---------------------------------------------------------------------------
# review process
# ---------------------------------------------------------------------------

class TestReviewProcess:
    def test_clean_review(self, monorepo_root, monkeypatch):
        _write_state(
            monorepo_root, 42, "workspace",
            step=PipelineStep.REVIEW_PROCESS,
        )
        monkeypatch.setattr(
            f"{S}.fetch_review",
            lambda *a, **kw: {"state": "COMMENTED", "body": "## Review Summary\n..."},
        )
        monkeypatch.setattr(f"{S}.parse_review_body", lambda b: ReviewCounts(0, 0, 0))

        result = step_review_process(42, "workspace", monorepo_root, review_id=100)
        assert result.action == "clean"

    def test_critical_triggers_resolve(self, monorepo_root, monkeypatch):
        _write_state(
            monorepo_root, 42, "workspace",
            step=PipelineStep.REVIEW_PROCESS,
        )
        monkeypatch.setattr(
            f"{S}.fetch_review",
            lambda *a, **kw: {"state": "CHANGES_REQUESTED", "body": "..."},
        )
        monkeypatch.setattr(f"{S}.parse_review_body", lambda b: ReviewCounts(2, 0, 0))

        result = step_review_process(42, "workspace", monorepo_root, review_id=100)
        assert result.action == "resolve"
        assert result.data["counts"]["critical"] == 2
        assert result.data["round"] == 1

    def test_warning_triggers_resolve(self, monorepo_root, monkeypatch):
        _write_state(
            monorepo_root, 42, "workspace",
            step=PipelineStep.REVIEW_PROCESS,
        )
        monkeypatch.setattr(
            f"{S}.fetch_review",
            lambda *a, **kw: {"state": "COMMENTED", "body": "..."},
        )
        monkeypatch.setattr(f"{S}.parse_review_body", lambda b: ReviewCounts(0, 1, 0))

        result = step_review_process(42, "workspace", monorepo_root, review_id=100)
        assert result.action == "resolve"

    def test_round_limit(self, monorepo_root, monkeypatch):
        _write_state(
            monorepo_root, 42, "workspace",
            step=PipelineStep.REVIEW_PROCESS,
            review_resolve_round=5,
            max_review_resolve_rounds=5,
        )
        monkeypatch.setattr(
            f"{S}.fetch_review",
            lambda *a, **kw: {"state": "CHANGES_REQUESTED", "body": "..."},
        )
        monkeypatch.setattr(f"{S}.parse_review_body", lambda b: ReviewCounts(1, 0, 0))

        result = step_review_process(42, "workspace", monorepo_root, review_id=100)
        assert result.action == "round_limit"

    def test_suggestion_only(self, monorepo_root, monkeypatch):
        _write_state(
            monorepo_root, 42, "workspace",
            step=PipelineStep.REVIEW_PROCESS,
        )
        monkeypatch.setattr(
            f"{S}.fetch_review",
            lambda *a, **kw: {"state": "COMMENTED", "body": "..."},
        )
        monkeypatch.setattr(f"{S}.parse_review_body", lambda b: ReviewCounts(0, 0, 3))

        result = step_review_process(42, "workspace", monorepo_root, review_id=100)
        assert result.action == "suggestion_only"

    def test_suggestion_only_round_incremented(self, monorepo_root, monkeypatch):
        """Bug 2 fix: suggestion_only returns round_num + 1, not round_num."""
        _write_state(
            monorepo_root, 42, "workspace",
            step=PipelineStep.REVIEW_PROCESS,
            review_resolve_round=1,
        )
        monkeypatch.setattr(
            f"{S}.fetch_review",
            lambda *a, **kw: {"state": "COMMENTED", "body": "..."},
        )
        monkeypatch.setattr(f"{S}.parse_review_body", lambda b: ReviewCounts(0, 0, 2))

        result = step_review_process(42, "workspace", monorepo_root, review_id=100)
        assert result.action == "suggestion_only"
        assert result.data["round"] == 2

    def test_suggestion_only_includes_review_body(self, monorepo_root, monkeypatch):
        """Bug 4 fix: suggestion_only data includes reviewBody for AI decision."""
        _write_state(
            monorepo_root, 42, "workspace",
            step=PipelineStep.REVIEW_PROCESS,
        )
        monkeypatch.setattr(
            f"{S}.fetch_review",
            lambda *a, **kw: {"state": "COMMENTED", "body": "review body content"},
        )
        monkeypatch.setattr(f"{S}.parse_review_body", lambda b: ReviewCounts(0, 0, 1))

        result = step_review_process(42, "workspace", monorepo_root, review_id=100)
        assert result.action == "suggestion_only"
        assert result.data["reviewBody"] == "review body content"

    def test_suggestion_at_round_limit_is_clean(self, monorepo_root, monkeypatch):
        _write_state(
            monorepo_root, 42, "workspace",
            step=PipelineStep.REVIEW_PROCESS,
            review_resolve_round=5,
            max_review_resolve_rounds=5,
        )
        monkeypatch.setattr(
            f"{S}.fetch_review",
            lambda *a, **kw: {"state": "COMMENTED", "body": "..."},
        )
        monkeypatch.setattr(f"{S}.parse_review_body", lambda b: ReviewCounts(0, 0, 1))

        result = step_review_process(42, "workspace", monorepo_root, review_id=100)
        assert result.action == "clean"

    def test_pending_review_escalates(self, monorepo_root, monkeypatch):
        _write_state(
            monorepo_root, 42, "workspace",
            step=PipelineStep.REVIEW_PROCESS,
        )
        monkeypatch.setattr(
            f"{S}.fetch_review",
            lambda *a, **kw: {"state": "PENDING", "body": "..."},
        )

        result = step_review_process(42, "workspace", monorepo_root, review_id=100)
        assert result.action == "escalate"

    def test_parse_failure_escalates(self, monorepo_root, monkeypatch):
        _write_state(
            monorepo_root, 42, "workspace",
            step=PipelineStep.REVIEW_PROCESS,
        )
        monkeypatch.setattr(
            f"{S}.fetch_review",
            lambda *a, **kw: {"state": "COMMENTED", "body": "bad body"},
        )

        def raise_parse(b):
            raise ValueError("no Review Summary")

        monkeypatch.setattr(f"{S}.parse_review_body", raise_parse)

        result = step_review_process(42, "workspace", monorepo_root, review_id=100)
        assert result.action == "escalate"


# ---------------------------------------------------------------------------
# suggestion decide (fix #2 + #3)
# ---------------------------------------------------------------------------

class TestSuggestionDecide:
    def test_merge(self, monorepo_root):
        _write_state(
            monorepo_root, 42, "workspace",
            step=PipelineStep.REVIEW_PROCESS,
            review_resolve_round=2,
        )

        result = step_suggestion_decide(42, "workspace", monorepo_root, decision="merge")
        assert result.action == "merge"
        assert result.data["round"] == 3

        state = state_read(42, "workspace", monorepo_root)
        assert state.step == PipelineStep.MERGE
        assert state.review_resolve_round == 3

    def test_resolve_skip(self, monorepo_root):
        _write_state(
            monorepo_root, 42, "workspace",
            step=PipelineStep.REVIEW_PROCESS,
            review_resolve_round=1,
        )

        result = step_suggestion_decide(42, "workspace", monorepo_root, decision="resolve-skip")
        assert result.action == "resolve"
        assert result.data["round"] == 2

        state = state_read(42, "workspace", monorepo_root)
        assert state.step == PipelineStep.RESOLVE
        assert state.skip_review is True
        assert state.review_resolve_round == 2

    def test_resolve_review(self, monorepo_root):
        _write_state(
            monorepo_root, 42, "workspace",
            step=PipelineStep.REVIEW_PROCESS,
            review_resolve_round=0,
        )

        result = step_suggestion_decide(42, "workspace", monorepo_root, decision="resolve-review")
        assert result.action == "resolve"
        assert result.data["round"] == 1

        state = state_read(42, "workspace", monorepo_root)
        assert state.step == PipelineStep.RESOLVE
        assert state.skip_review is False
        assert state.review_resolve_round == 1

    def test_invalid_decision(self, monorepo_root):
        _write_state(
            monorepo_root, 42, "workspace",
            step=PipelineStep.REVIEW_PROCESS,
        )

        result = step_suggestion_decide(42, "workspace", monorepo_root, decision="invalid")
        assert result.action == "error"

    def test_round_counter_increments(self, monorepo_root):
        """Fix #3: round counter increments on suggestion_only path."""
        _write_state(
            monorepo_root, 42, "workspace",
            step=PipelineStep.REVIEW_PROCESS,
            review_resolve_round=3,
        )

        result = step_suggestion_decide(42, "workspace", monorepo_root, decision="resolve-skip")

        state = state_read(42, "workspace", monorepo_root)
        assert state.review_resolve_round == 4
        assert result.data["round"] == 4


# ---------------------------------------------------------------------------
# resolve setup
# ---------------------------------------------------------------------------

class TestResolveSetup:
    def test_worktree_not_found(self, monorepo_root):
        _write_state(monorepo_root, 42, "workspace", step=PipelineStep.RESOLVE)

        result = step_resolve_setup(42, "workspace", monorepo_root)
        assert result.action == "escalate"
        assert "worktree not found" in result.data["reason"]

    def test_ready(self, monorepo_root, monkeypatch):
        wt = monorepo_root / ".workspace" / "worktrees" / "workspace" / "issue-42"
        wt.mkdir(parents=True)

        _write_state(monorepo_root, 42, "workspace", step=PipelineStep.RESOLVE)

        monkeypatch.setattr(f"{S}.rev_parse_head", lambda wt: "a" * 40)
        monkeypatch.setattr(f"{S}.is_clean", lambda wt: True)
        monkeypatch.setattr(f"{S}.check_new_commits", lambda *a, **kw: None)
        monkeypatch.setattr(
            f"{S}.fetch_review",
            lambda *a, **kw: {"body": "## Review Summary\n..."},
        )
        monkeypatch.setattr(
            f"{S}.fetch_review_comments",
            lambda *a, **kw: [{"path": "a.py", "line": 1, "body": "fix"}],
        )

        result = step_resolve_setup(42, "workspace", monorepo_root)
        assert result.action == "ready"
        assert result.data["reviewBody"] == "## Review Summary\n..."
        assert len(result.data["comments"]) == 1

    def test_head_mismatch_dirty(self, monorepo_root, monkeypatch):
        wt = monorepo_root / ".workspace" / "worktrees" / "workspace" / "issue-42"
        wt.mkdir(parents=True)

        _write_state(monorepo_root, 42, "workspace", step=PipelineStep.RESOLVE)

        monkeypatch.setattr(f"{S}.rev_parse_head", lambda wt: "b" * 40)
        monkeypatch.setattr(f"{S}.is_clean", lambda wt: False)

        result = step_resolve_setup(42, "workspace", monorepo_root)
        assert result.action == "recovery"
        assert "HEAD mismatch + dirty tree" in result.data["reason"]

    def test_head_match_dirty(self, monorepo_root, monkeypatch):
        wt = monorepo_root / ".workspace" / "worktrees" / "workspace" / "issue-42"
        wt.mkdir(parents=True)

        _write_state(monorepo_root, 42, "workspace", step=PipelineStep.RESOLVE)

        monkeypatch.setattr(f"{S}.rev_parse_head", lambda wt: "a" * 40)
        monkeypatch.setattr(f"{S}.is_clean", lambda wt: False)

        result = step_resolve_setup(42, "workspace", monorepo_root)
        assert result.action == "recovery"
        assert "dirty tree" in result.data["reason"]


# ---------------------------------------------------------------------------
# resolve finalize
# ---------------------------------------------------------------------------

class TestResolveFinalize:
    def test_with_changes_and_re_review(self, monorepo_root, monkeypatch):
        _write_state(
            monorepo_root, 42, "workspace",
            step=PipelineStep.RESOLVE,
            skip_review=False,
        )

        monkeypatch.setattr(f"{S}.add_all", lambda wt: True)
        monkeypatch.setattr(f"{S}.has_staged_changes", lambda wt: True)
        monkeypatch.setattr(f"{S}.commit", lambda wt, msg: True)
        monkeypatch.setattr(f"{S}.push_safely", lambda wt: True)
        monkeypatch.setattr(f"{S}.rev_parse_head", lambda wt: "c" * 40)

        result = step_resolve_finalize(42, "workspace", monorepo_root)
        assert result.action == "re_review"

        state = state_read(42, "workspace", monorepo_root)
        assert state.step == PipelineStep.REVIEW_DISPATCH

    def test_skip_review_goes_to_merge(self, monorepo_root, monkeypatch):
        _write_state(
            monorepo_root, 42, "workspace",
            step=PipelineStep.RESOLVE,
            skip_review=True,
        )

        monkeypatch.setattr(f"{S}.add_all", lambda wt: True)
        monkeypatch.setattr(f"{S}.has_staged_changes", lambda wt: False)
        monkeypatch.setattr(f"{S}.rev_parse_head", lambda wt: "a" * 40)

        result = step_resolve_finalize(42, "workspace", monorepo_root)
        assert result.action == "merge"

        state = state_read(42, "workspace", monorepo_root)
        assert state.step == PipelineStep.MERGE

    def test_no_changes_skip_review(self, monorepo_root, monkeypatch):
        _write_state(
            monorepo_root, 42, "workspace",
            step=PipelineStep.RESOLVE,
            skip_review=False,
        )

        monkeypatch.setattr(f"{S}.add_all", lambda wt: True)
        monkeypatch.setattr(f"{S}.has_staged_changes", lambda wt: False)
        monkeypatch.setattr(f"{S}.rev_parse_head", lambda wt: "a" * 40)

        result = step_resolve_finalize(42, "workspace", monorepo_root)
        assert result.action == "re_review"

    def test_ai_committed_directly_updates_sha(self, monorepo_root, monkeypatch):
        """Fix #1: AI commits before finalize -> SHA updated even with no staged changes."""
        _write_state(
            monorepo_root, 42, "workspace",
            step=PipelineStep.RESOLVE,
            skip_review=False,
            last_commit_sha="a" * 40,
        )

        monkeypatch.setattr(f"{S}.add_all", lambda wt: True)
        monkeypatch.setattr(f"{S}.has_staged_changes", lambda wt: False)
        # HEAD differs from state - AI committed directly
        monkeypatch.setattr(f"{S}.rev_parse_head", lambda wt: "b" * 40)

        result = step_resolve_finalize(42, "workspace", monorepo_root)
        assert result.action == "re_review"

        state = state_read(42, "workspace", monorepo_root)
        assert state.last_commit_sha == "b" * 40


# ---------------------------------------------------------------------------
# merge
# ---------------------------------------------------------------------------

class TestStepMerge:
    def test_success(self, monorepo_root, monkeypatch):
        _write_state(
            monorepo_root, 42, "workspace",
            step=PipelineStep.MERGE,
            branch="feat/issue-42",
        )

        monkeypatch.setattr(f"{S}.get_pr_state", lambda *a: "OPEN")
        monkeypatch.setattr(f"{S}.merge_pr", lambda *a, **kw: None)
        monkeypatch.setattr(f"{S}.fetch_prune", lambda *a: None)

        result = step_merge(42, "workspace", monorepo_root)
        assert result.action == "merged"

        state = state_read(42, "workspace", monorepo_root)
        assert state.step == PipelineStep.CLEANUP_WT

    def test_already_merged(self, monorepo_root, monkeypatch):
        _write_state(
            monorepo_root, 42, "workspace",
            step=PipelineStep.MERGE,
        )

        monkeypatch.setattr(f"{S}.get_pr_state", lambda *a: "MERGED")
        monkeypatch.setattr(f"{S}.fetch_prune", lambda *a: None)

        result = step_merge(42, "workspace", monorepo_root)
        assert result.action == "already_merged"

        state = state_read(42, "workspace", monorepo_root)
        assert state.step == PipelineStep.CLEANUP_WT

    def test_closed(self, monorepo_root, monkeypatch):
        _write_state(
            monorepo_root, 42, "workspace",
            step=PipelineStep.MERGE,
        )

        monkeypatch.setattr(f"{S}.get_pr_state", lambda *a: "CLOSED")

        result = step_merge(42, "workspace", monorepo_root)
        assert result.action == "closed"

    def test_merge_failure_retries(self, monorepo_root, monkeypatch):
        _write_state(
            monorepo_root, 42, "workspace",
            step=PipelineStep.MERGE,
            branch="feat/issue-42",
        )

        monkeypatch.setattr(f"{S}.get_pr_state", lambda *a: "OPEN")

        def raise_merge(*a, **kw):
            raise RuntimeError("merge failed")

        monkeypatch.setattr(f"{S}.merge_pr", raise_merge)

        result = step_merge(42, "workspace", monorepo_root)
        assert result.action == "retry"


# ---------------------------------------------------------------------------
# log finalize
# ---------------------------------------------------------------------------

class TestStepCleanupWt:
    def test_continue(self, monorepo_root, monkeypatch):
        _write_state(
            monorepo_root, 42, "workspace",
            step=PipelineStep.CLEANUP_WT,
            branch="feat/issue-42",
        )

        monkeypatch.setattr(f"{S}.cleanup_worktree", lambda *a, **kw: None)

        result = step_cleanup_wt(42, "workspace", monorepo_root)
        assert result.action == "continue"

        state = state_read(42, "workspace", monorepo_root)
        assert state.step == PipelineStep.LOG


class TestLogFinalize:
    def test_done(self, monorepo_root, monkeypatch):
        _write_state(
            monorepo_root, 42, "workspace",
            step=PipelineStep.LOG,
        )

        result = step_log_finalize(42, "workspace", monorepo_root)
        assert result.action == "done"


# ---------------------------------------------------------------------------
# init --issue (bug fix #3)
# ---------------------------------------------------------------------------

class TestInitWithIssue:
    def test_creates_state(self, monorepo_root):
        from dev_pipeline.paths import pipeline_init, area_repo_dir, pipeline_worktree_path
        from dev_pipeline.state_store import state_exists

        pipeline_init("workspace", monorepo_root)
        assert not state_exists(999, "workspace", monorepo_root)

        state = PipelineState(
            issue=999,
            area="workspace",
            step=PipelineStep.BUILD,
            paths=Paths(
                skill_cwd=str(monorepo_root),
                repo_dir=str(area_repo_dir("workspace", monorepo_root)),
                worktree_dir=str(pipeline_worktree_path(999, "workspace", monorepo_root)),
            ),
        )
        state_write(999, "workspace", monorepo_root, state)

        assert state_exists(999, "workspace", monorepo_root)
        loaded = state_read(999, "workspace", monorepo_root)
        assert loaded.issue == 999
        assert loaded.step == PipelineStep.BUILD

    def test_no_issue_no_state(self, monorepo_root):
        from dev_pipeline.paths import pipeline_init
        from dev_pipeline.state_store import state_exists

        pipeline_init("workspace", monorepo_root)
        assert not state_exists(999, "workspace", monorepo_root)
