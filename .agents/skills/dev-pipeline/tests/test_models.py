"""Tests for models serialization / deserialization."""
import pytest

from dev_pipeline.models import (
    Paths,
    PipelineState,
    PipelineStep,
    ReviewJob,
    ReviewJobStatus,
)


def test_pipeline_step_values():
    assert PipelineStep.BUILD.value == "build"
    assert PipelineStep.REVIEW_DISPATCH.value == "review_dispatch"
    assert PipelineStep.MERGE.value == "merge"


def test_review_job_status_values():
    assert ReviewJobStatus.IDLE.value == "idle"
    assert ReviewJobStatus.RUNNING.value == "running"
    assert ReviewJobStatus.SUCCESS.value == "success"
    assert ReviewJobStatus.FAILED.value == "failed"


def test_paths_to_dict():
    p = Paths(skill_cwd="/workspace", repo_dir="/workspace/client", worktree_dir="/wt")
    d = p.to_dict()
    assert d == {
        "skillCwd": "/workspace",
        "repoDir": "/workspace/client",
        "worktreeDir": "/wt",
    }


def test_paths_from_dict():
    d = {"skillCwd": "/workspace", "repoDir": "/repo", "worktreeDir": "/wt"}
    p = Paths.from_dict(d)
    assert p.skill_cwd == "/workspace"
    assert p.repo_dir == "/repo"
    assert p.worktree_dir == "/wt"


def test_paths_from_dict_missing_keys():
    p = Paths.from_dict({})
    assert p.skill_cwd == ""
    assert p.repo_dir == ""
    assert p.worktree_dir == ""


def test_review_job_to_dict():
    rj = ReviewJob(run_id="r1", status=ReviewJobStatus.RUNNING, tool="claude", model="")
    d = rj.to_dict()
    assert d["runId"] == "r1"
    assert d["status"] == "running"
    assert d["tool"] == "claude"
    assert d["startedAt"] is None


def test_review_job_from_dict():
    d = {
        "runId": "r2",
        "status": "success",
        "startedAt": "2024-01-01T00:00:00Z",
        "finishedAt": "2024-01-01T00:05:00Z",
        "tool": "codex",
        "model": "gpt-4",
    }
    rj = ReviewJob.from_dict(d)
    assert rj.run_id == "r2"
    assert rj.status == ReviewJobStatus.SUCCESS
    assert rj.started_at == "2024-01-01T00:00:00Z"
    assert rj.tool == "codex"


def test_review_job_from_dict_invalid_status():
    rj = ReviewJob.from_dict({"status": "unknown_status"})
    assert rj.status == ReviewJobStatus.IDLE


def test_pipeline_state_defaults():
    state = PipelineState()
    assert state.version == 2
    assert state.issue == 0
    assert state.step == PipelineStep.BUILD
    assert isinstance(state.stage_retries, dict)
    assert state.max_stage_retries == 3


def test_pipeline_state_to_dict_camelcase():
    state = PipelineState(issue=42, area="client", pr=129)
    d = state.to_dict()
    # Check camelCase keys
    assert "lastReviewId" in d
    assert "lastCommitSha" in d
    assert "skipReview" in d
    assert "reviewResolveRound" in d
    assert "maxReviewResolveRounds" in d
    assert "stageRetries" in d
    assert "maxStageRetries" in d
    assert "reviewJob" in d
    assert "transitionLog" in d
    assert "recoveryLog" in d
    # No snake_case leakage
    assert "last_review_id" not in d
    assert "skip_review" not in d


def test_pipeline_state_from_dict(sample_state):
    state = PipelineState.from_dict(sample_state)
    assert state.issue == 42
    assert state.area == "client"
    assert state.pr == 129
    assert state.branch == "feat/issue-42"
    assert state.step == PipelineStep.REVIEW_DISPATCH
    assert state.last_review_id == 0
    assert state.last_commit_sha == "abc123"
    assert state.skip_review is False
    assert state.review_resolve_round == 0
    assert state.max_review_resolve_rounds == 5
    assert state.max_stage_retries == 3


def test_pipeline_state_roundtrip(sample_state):
    state = PipelineState.from_dict(sample_state)
    d = state.to_dict()
    state2 = PipelineState.from_dict(d)
    assert state2.issue == state.issue
    assert state2.area == state.area
    assert state2.step == state.step
    assert state2.last_commit_sha == state.last_commit_sha


def test_pipeline_state_paths_roundtrip(sample_state):
    state = PipelineState.from_dict(sample_state)
    assert state.paths.skill_cwd == "/workspace"
    assert state.paths.repo_dir == "/workspace/client"


def test_pipeline_state_stage_retries_defaults():
    state = PipelineState()
    for step in ["build", "review_dispatch", "review_wait", "review_process", "resolve", "merge", "log"]:
        assert step in state.stage_retries
        assert state.stage_retries[step] == 0


def test_pipeline_state_from_dict_unknown_step():
    state = PipelineState.from_dict({"step": "nonexistent_step"})
    assert state.step == PipelineStep.BUILD


def test_pipeline_state_from_dict_legacy_review_step():
    """Old state files may have step='review' instead of split steps.
    This must be migrated to review_dispatch, not reset to BUILD."""
    state = PipelineState.from_dict({"step": "review", "issue": 99})
    assert state.step == PipelineStep.REVIEW_DISPATCH


def test_pipeline_state_transition_log(sample_state):
    sample_state["transitionLog"] = [
        {"from": "build", "to": "review_dispatch", "reason": "ok", "ts": "2024-01-01T00:00:00Z"}
    ]
    state = PipelineState.from_dict(sample_state)
    assert len(state.transition_log) == 1
    assert state.transition_log[0]["from"] == "build"
