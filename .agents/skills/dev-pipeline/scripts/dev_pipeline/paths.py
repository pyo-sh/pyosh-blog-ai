import os
from pathlib import Path
from typing import Optional


def find_monorepo_root() -> Path:
    """Find monorepo root by env var or by walking up looking for sentinel file."""
    env_root = os.environ.get("PIPELINE_MONOREPO_ROOT")
    if env_root:
        return Path(env_root)
    # Walk up from __file__ looking for .agents/scripts/monorepo-helpers.sh
    candidate = Path(__file__).resolve()
    while candidate != candidate.parent:
        if (candidate / ".agents" / "scripts" / "monorepo-helpers.sh").exists():
            return candidate
        candidate = candidate.parent
    return Path("/workspace")


def pipeline_dir(monorepo_root: Path) -> Path:
    return monorepo_root / ".workspace" / "pipeline"


def pipeline_state_dir(area: str, monorepo_root: Path) -> Path:
    return pipeline_dir(monorepo_root) / area


def pipeline_log_dir(area: str, monorepo_root: Path) -> Path:
    return pipeline_dir(monorepo_root) / "logs" / area


def pipeline_state_path(issue: int, area: str, monorepo_root: Path) -> Path:
    return pipeline_state_dir(area, monorepo_root) / f"issue-{issue}.state.json"


def pipeline_log_path(issue: int, area: str, stage: str, monorepo_root: Path) -> Path:
    return pipeline_log_dir(area, monorepo_root) / f"issue-{issue}-{stage}.log"


def pipeline_err_path(issue: int, area: str, stage: str, monorepo_root: Path) -> Path:
    return pipeline_log_dir(area, monorepo_root) / f"issue-{issue}-{stage}.err"


def pipeline_headless_meta_path(issue: int, area: str, stage: str, monorepo_root: Path) -> Path:
    return pipeline_state_dir(area, monorepo_root) / f"issue-{issue}-{stage}.job.json"


def pipeline_message_path(area: str, pr: int, kind: str, monorepo_root: Path) -> Path:
    return monorepo_root / ".workspace" / "messages" / f"{area}-pr-{pr}-{kind}.md"


def pipeline_worktree_path(issue: int, area: str, monorepo_root: Path) -> Path:
    return monorepo_root / ".workspace" / "worktrees" / area / f"issue-{issue}"


def resolve_worktree_path(issue: int, area: str, monorepo_root: Path) -> Optional[Path]:
    """Returns Path if exists, None otherwise."""
    p = pipeline_worktree_path(issue, area, monorepo_root)
    return p if p.is_dir() else None


def pipeline_init(area: str, monorepo_root: Path) -> None:
    """Create all required directories."""
    pipeline_state_dir(area, monorepo_root).mkdir(parents=True, exist_ok=True)
    pipeline_log_dir(area, monorepo_root).mkdir(parents=True, exist_ok=True)
    (monorepo_root / ".workspace" / "messages").mkdir(parents=True, exist_ok=True)
    (monorepo_root / ".workspace" / "worktrees" / area).mkdir(parents=True, exist_ok=True)
