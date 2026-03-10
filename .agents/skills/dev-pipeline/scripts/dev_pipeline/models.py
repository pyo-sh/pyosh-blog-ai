import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class PipelineStep(str, Enum):
    BUILD = "build"
    REVIEW_DISPATCH = "review_dispatch"
    REVIEW_WAIT = "review_wait"
    REVIEW_PROCESS = "review_process"
    RESOLVE = "resolve"
    MERGE = "merge"
    LOG = "log"


class ReviewJobStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class ReviewJob:
    run_id: str = ""
    status: ReviewJobStatus = ReviewJobStatus.IDLE
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    tool: str = ""
    model: str = ""

    def to_dict(self) -> dict:
        return {
            "runId": self.run_id,
            "status": self.status.value if isinstance(self.status, ReviewJobStatus) else self.status,
            "startedAt": self.started_at,
            "finishedAt": self.finished_at,
            "tool": self.tool,
            "model": self.model,
        }

    def is_stale(self, timeout_secs: int = 1800) -> bool:
        """Check if this running job has exceeded the stale timeout."""
        if self.status != ReviewJobStatus.RUNNING:
            return False
        if not self.started_at:
            return True  # Running with no start time is stale
        try:
            started = datetime.fromisoformat(self.started_at.replace("Z", "+00:00"))
            elapsed = (datetime.now(timezone.utc) - started).total_seconds()
            return elapsed > timeout_secs
        except (ValueError, TypeError):
            return True  # Unparseable → treat as stale

    @classmethod
    def from_dict(cls, d: dict) -> "ReviewJob":
        status_raw = d.get("status", "idle")
        try:
            status = ReviewJobStatus(status_raw)
        except ValueError:
            status = ReviewJobStatus.IDLE
        return cls(
            run_id=d.get("runId", ""),
            status=status,
            started_at=d.get("startedAt"),
            finished_at=d.get("finishedAt"),
            tool=d.get("tool", ""),
            model=d.get("model", ""),
        )


@dataclass
class Paths:
    skill_cwd: str = ""
    repo_dir: str = ""
    worktree_dir: str = ""

    def to_dict(self) -> dict:
        return {
            "skillCwd": self.skill_cwd,
            "repoDir": self.repo_dir,
            "worktreeDir": self.worktree_dir,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Paths":
        return cls(
            skill_cwd=d.get("skillCwd", ""),
            repo_dir=d.get("repoDir", ""),
            worktree_dir=d.get("worktreeDir", ""),
        )


@dataclass
class PipelineState:
    version: int = 2
    issue: int = 0
    area: str = ""
    pr: int = 0
    branch: str = ""
    paths: Paths = field(default_factory=Paths)
    step: PipelineStep = PipelineStep.BUILD
    last_review_id: int = 0
    last_commit_sha: str = ""
    skip_review: bool = False
    review_resolve_round: int = 0
    max_review_resolve_rounds: int = 5
    stage_retries: dict = field(default_factory=lambda: {s.value: 0 for s in PipelineStep})
    max_stage_retries: int = 3
    review_job: ReviewJob = field(default_factory=ReviewJob)
    transition_log: list = field(default_factory=list)
    recovery_log: list = field(default_factory=list)
    updated_at: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "issue": self.issue,
            "area": self.area,
            "pr": self.pr,
            "branch": self.branch,
            "paths": self.paths.to_dict(),
            "step": self.step.value if isinstance(self.step, PipelineStep) else self.step,
            "lastReviewId": self.last_review_id,
            "lastCommitSha": self.last_commit_sha,
            "skipReview": self.skip_review,
            "reviewResolveRound": self.review_resolve_round,
            "maxReviewResolveRounds": self.max_review_resolve_rounds,
            "stageRetries": self.stage_retries,
            "maxStageRetries": self.max_stage_retries,
            "reviewJob": self.review_job.to_dict(),
            "transitionLog": self.transition_log,
            "recoveryLog": self.recovery_log,
            "updatedAt": self.updated_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PipelineState":
        step_raw = d.get("step", "build")
        # Migration: old state files may use "review" as a single step name.
        # Map it to review_dispatch so the pipeline resumes at the correct stage.
        _STEP_MIGRATION = {"review": "review_dispatch"}
        step_raw = _STEP_MIGRATION.get(step_raw, step_raw)
        try:
            step = PipelineStep(step_raw)
        except ValueError:
            print(
                f"[models] WARNING: unknown step {step_raw!r} in state "
                f"(issue={d.get('issue')}); defaulting to BUILD",
                file=sys.stderr,
            )
            step = PipelineStep.BUILD

        paths_raw = d.get("paths", {})
        paths = Paths.from_dict(paths_raw) if isinstance(paths_raw, dict) else Paths()

        review_job_raw = d.get("reviewJob", {})
        review_job = ReviewJob.from_dict(review_job_raw) if isinstance(review_job_raw, dict) else ReviewJob()

        default_retries = {s.value: 0 for s in PipelineStep}
        stage_retries = {**default_retries, **d.get("stageRetries", {})}

        return cls(
            version=d.get("version", 2),
            issue=d.get("issue", 0),
            area=d.get("area", ""),
            pr=d.get("pr", 0),
            branch=d.get("branch", ""),
            paths=paths,
            step=step,
            last_review_id=d.get("lastReviewId", 0),
            last_commit_sha=d.get("lastCommitSha", ""),
            skip_review=d.get("skipReview", False),
            review_resolve_round=d.get("reviewResolveRound", 0),
            max_review_resolve_rounds=d.get("maxReviewResolveRounds", 5),
            stage_retries=stage_retries,
            max_stage_retries=d.get("maxStageRetries", 3),
            review_job=review_job,
            transition_log=d.get("transitionLog", []),
            recovery_log=d.get("recoveryLog", []),
            updated_at=d.get("updatedAt"),
        )
