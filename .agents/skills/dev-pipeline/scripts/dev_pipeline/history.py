"""Attempt history log for the dev-pipeline.

Provides persistent, append-only storage of completed pipeline attempts so that
failure patterns and operational statistics can be queried after state files are
deleted.

Storage: `.workspace/pipeline/history.jsonl`  (one JSON object per line)

Record schema
-------------
{
  "area":          str,           # "client" | "server" | "workspace"
  "issue":         int,
  "pr":            int,
  "branch":        str,
  "outcome":       str,           # "success" | "failed" | "escalated"
  "failureClass":  str,           # ReviewJobStatus value; "" on success
  "step":          str,           # pipeline step where outcome occurred
  "reviewRound":   int,
  "stageRetries":  dict[str,int],
  "recoveryCount": int,
  "startedAt":     str | null,    # ISO8601 or null
  "finishedAt":    str,           # ISO8601
  "tool":          str,
  "model":         str
}
"""

from __future__ import annotations

import json
import os
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Record dataclass
# ---------------------------------------------------------------------------

@dataclass
class AttemptRecord:
    area: str
    issue: int
    pr: int
    branch: str
    outcome: str        # "success" | "failed" | "escalated"
    failure_class: str  # ReviewJobStatus.value or ""
    step: str
    review_round: int
    stage_retries: Dict[str, int] = field(default_factory=dict)
    recovery_count: int = 0
    started_at: Optional[str] = None
    finished_at: str = ""
    tool: str = ""
    model: str = ""

    def to_dict(self) -> dict:
        return {
            "area": self.area,
            "issue": self.issue,
            "pr": self.pr,
            "branch": self.branch,
            "outcome": self.outcome,
            "failureClass": self.failure_class,
            "step": self.step,
            "reviewRound": self.review_round,
            "stageRetries": self.stage_retries,
            "recoveryCount": self.recovery_count,
            "startedAt": self.started_at,
            "finishedAt": self.finished_at,
            "tool": self.tool,
            "model": self.model,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "AttemptRecord":
        return cls(
            area=d.get("area", ""),
            issue=int(d.get("issue") or 0),
            pr=int(d.get("pr") or 0),
            branch=d.get("branch", ""),
            outcome=d.get("outcome", ""),
            failure_class=d.get("failureClass", ""),
            step=d.get("step", ""),
            review_round=int(d.get("reviewRound") or 0),
            stage_retries=d.get("stageRetries", {}),
            recovery_count=int(d.get("recoveryCount") or 0),
            started_at=d.get("startedAt"),
            finished_at=d.get("finishedAt", ""),
            tool=d.get("tool", ""),
            model=d.get("model", ""),
        )

    @classmethod
    def from_state(cls, state, outcome: str, failure_class: str = "") -> "AttemptRecord":
        """Build an AttemptRecord from a PipelineState object."""
        started_at: Optional[str] = None
        if state.transition_log:
            started_at = state.transition_log[0].get("ts")

        return cls(
            area=state.area,
            issue=state.issue,
            pr=state.pr,
            branch=state.branch,
            outcome=outcome,
            failure_class=failure_class,
            step=state.step.value if hasattr(state.step, "value") else str(state.step),
            review_round=state.review_resolve_round,
            stage_retries=dict(state.stage_retries),
            recovery_count=len(getattr(state, "recovery_log", [])),
            started_at=started_at,
            finished_at=_now_iso(),
            tool=getattr(state.review_job, "tool", "") if state.review_job else "",
            model=getattr(state.review_job, "model", "") if state.review_job else "",
        )


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def history_log_path(monorepo_root: Path) -> Path:
    return monorepo_root / ".workspace" / "pipeline" / "history.jsonl"


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------

def history_append(monorepo_root: Path, record: AttemptRecord) -> None:
    """Append one attempt record to the history log (atomic line append)."""
    log_path = history_log_path(monorepo_root)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record.to_dict(), separators=(",", ":")) + "\n"
    # O_APPEND mode: on Linux, short writes to a regular file via O_APPEND do
    # not interleave in practice (kernel i_mutex serialises them), but this is
    # not a portable POSIX guarantee. JSONL lines are short, so this is safe
    # for the expected single-host usage of this tool.
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(line)


# ---------------------------------------------------------------------------
# Read + filter
# ---------------------------------------------------------------------------

def history_read(
    monorepo_root: Path,
    area: Optional[str] = None,
    issue: Optional[int] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
) -> List[AttemptRecord]:
    """Read history log and return filtered records (newest first)."""
    log_path = history_log_path(monorepo_root)
    if not log_path.exists():
        return []

    records: List[AttemptRecord] = []
    with open(log_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
                records.append(AttemptRecord.from_dict(d))
            except (json.JSONDecodeError, KeyError, ValueError):
                continue  # skip malformed lines

    # Filter
    if area:
        records = [r for r in records if r.area == area]
    if issue is not None:
        records = [r for r in records if r.issue == issue]
    if since:
        records = [r for r in records if r.finished_at >= since]
    if until:
        # Normalize a bare date ("YYYY-MM-DD") to end-of-day so the boundary
        # date is included in the result set.
        _until = until + "T23:59:59Z" if "T" not in until else until
        records = [r for r in records if r.finished_at <= _until]

    records.sort(key=lambda r: r.finished_at, reverse=True)
    return records


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

def history_stats(records: List[AttemptRecord]) -> dict:
    """Compute statistics across attempt records.

    Returns:
        {
          "total": int,
          "byOutcome": {"success": int, "failed": int, "escalated": int},
          "byFailureClass": {"failed_parse": int, ...},
          "byArea": {"workspace": int, ...},
          "byTool": {"claude": int, "codex": int},
          "avgReviewRound": float,
          "avgRecoveryCount": float,
        }
    """
    if not records:
        return {
            "total": 0,
            "byOutcome": {},
            "byFailureClass": {},
            "byArea": {},
            "byTool": {},
            "avgReviewRound": 0.0,
            "avgRecoveryCount": 0.0,
        }

    by_outcome: Dict[str, int] = defaultdict(int)
    by_failure_class: Dict[str, int] = defaultdict(int)
    by_area: Dict[str, int] = defaultdict(int)
    by_tool: Dict[str, int] = defaultdict(int)
    total_rounds = 0
    total_recovery = 0

    for r in records:
        by_outcome[r.outcome] += 1
        if r.failure_class:
            by_failure_class[r.failure_class] += 1
        by_area[r.area] += 1
        if r.tool:
            by_tool[r.tool] += 1
        total_rounds += r.review_round
        total_recovery += r.recovery_count

    n = len(records)
    return {
        "total": n,
        "byOutcome": dict(by_outcome),
        "byFailureClass": dict(by_failure_class),
        "byArea": dict(by_area),
        "byTool": dict(by_tool),
        "avgReviewRound": round(total_rounds / n, 2),
        "avgRecoveryCount": round(total_recovery / n, 2),
    }


# ---------------------------------------------------------------------------
# Pattern analysis
# ---------------------------------------------------------------------------

def history_patterns(records: List[AttemptRecord]) -> dict:
    """Identify repeated failure patterns.

    Returns:
        {
          "repeatedFailureClass": [
            {"failureClass": str, "count": int, "issues": [int, ...]},
            ...  sorted by count desc
          ],
          "repeatedIssueFailures": [
            {"issue": int, "area": str, "failCount": int, "classes": [str, ...]},
            ...  issues with > 1 failure
          ],
          "hourlyFailureDistribution": {
            "00": int, "01": int, ..., "23": int
          }
        }
    """
    failed = [r for r in records if r.outcome in ("failed", "escalated")]

    # --- repeated failure_class frequency ---
    fc_counts: Dict[str, int] = defaultdict(int)
    fc_issues: Dict[str, set] = defaultdict(set)
    for r in failed:
        fc = r.failure_class or "(unknown)"
        fc_counts[fc] += 1
        fc_issues[fc].add(r.issue)

    repeated_fc = sorted(
        [
            {"failureClass": fc, "count": cnt, "issues": sorted(fc_issues[fc])}
            for fc, cnt in fc_counts.items()
        ],
        key=lambda x: x["count"],
        reverse=True,
    )

    # --- repeated issue failures ---
    issue_counts: Dict[tuple, int] = defaultdict(int)
    issue_classes: Dict[tuple, list] = defaultdict(list)
    for r in failed:
        k = (r.area, r.issue)
        issue_counts[k] += 1
        issue_classes[k].append(r.failure_class or "(unknown)")

    repeated_issues = sorted(
        [
            {
                "issue": k[1],
                "area": k[0],
                "failCount": cnt,
                "classes": list(dict.fromkeys(issue_classes[k])),  # dedup, order-preserving
            }
            for k, cnt in issue_counts.items()
            if cnt > 1
        ],
        key=lambda x: x["failCount"],
        reverse=True,
    )

    # --- hourly failure distribution ---
    hourly: Dict[str, int] = defaultdict(int)
    for r in failed:
        if r.finished_at:
            try:
                dt = datetime.fromisoformat(r.finished_at.replace("Z", "+00:00"))
                hourly[f"{dt.hour:02d}"] += 1
            except (ValueError, AttributeError):
                pass
    hourly_dist = {f"{h:02d}": hourly.get(f"{h:02d}", 0) for h in range(24)}

    return {
        "repeatedFailureClass": repeated_fc,
        "repeatedIssueFailures": repeated_issues,
        "hourlyFailureDistribution": hourly_dist,
    }


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

def format_table(records: List[AttemptRecord]) -> str:
    """Render records as a plain-text table."""
    if not records:
        return "(no records)"

    headers = ["area", "issue", "pr", "outcome", "failure_class", "step", "round", "tool", "finished_at"]
    rows = [
        [
            r.area,
            str(r.issue),
            str(r.pr) if r.pr else "-",
            r.outcome,
            r.failure_class or "-",
            r.step,
            str(r.review_round),
            r.tool or "-",
            r.finished_at[:19] if r.finished_at else "-",
        ]
        for r in records
    ]

    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(cell))

    def fmt_row(cells: list) -> str:
        return "  ".join(c.ljust(col_widths[i]) for i, c in enumerate(cells))

    sep = "  ".join("-" * w for w in col_widths)
    lines = [fmt_row(headers), sep] + [fmt_row(r) for r in rows]
    return "\n".join(lines)


def format_stats_table(stats: dict) -> str:
    """Render statistics dict as human-readable text."""
    lines = [
        f"Total attempts:        {stats['total']}",
        f"Avg review rounds:     {stats['avgReviewRound']}",
        f"Avg recovery retries:  {stats['avgRecoveryCount']}",
        "",
        "Outcome breakdown:",
    ]
    for k, v in sorted(stats["byOutcome"].items()):
        lines.append(f"  {k:<18} {v}")

    if stats["byFailureClass"]:
        lines += ["", "Failure class breakdown:"]
        for k, v in sorted(stats["byFailureClass"].items(), key=lambda x: -x[1]):
            lines.append(f"  {k:<24} {v}")

    if stats["byArea"]:
        lines += ["", "By area:"]
        for k, v in sorted(stats["byArea"].items()):
            lines.append(f"  {k:<18} {v}")

    if stats["byTool"]:
        lines += ["", "By tool:"]
        for k, v in sorted(stats["byTool"].items()):
            lines.append(f"  {k:<18} {v}")

    return "\n".join(lines)


def format_patterns_table(patterns: dict) -> str:
    """Render pattern analysis as human-readable text."""
    lines: List[str] = []

    rfc = patterns["repeatedFailureClass"]
    if rfc:
        lines.append("Repeated failure classes (by frequency):")
        for entry in rfc:
            issues_str = ", ".join(f"#{i}" for i in entry["issues"])
            lines.append(f"  {entry['failureClass']:<28} x{entry['count']}  issues: {issues_str}")
    else:
        lines.append("Repeated failure classes: (none)")

    rif = patterns["repeatedIssueFailures"]
    lines.append("")
    if rif:
        lines.append("Issues with repeated failures (>1 failure):")
        for entry in rif:
            classes_str = ", ".join(entry["classes"])
            lines.append(
                f"  #{entry['issue']} ({entry['area']})  "
                f"failures: {entry['failCount']}  classes: {classes_str}"
            )
    else:
        lines.append("Issues with repeated failures: (none)")

    hourly = patterns["hourlyFailureDistribution"]
    non_zero = {h: c for h, c in hourly.items() if c > 0}
    lines.append("")
    if non_zero:
        lines.append("Hourly failure distribution (UTC):")
        for hour in sorted(non_zero):
            bar = "#" * non_zero[hour]
            lines.append(f"  {hour}:00  {bar} ({non_zero[hour]})")
    else:
        lines.append("Hourly failure distribution: (no data)")

    return "\n".join(lines)
