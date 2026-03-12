from datetime import date

from dev_log.indexing import check_progress, next_sequence


def test_next_seq_empty_dir(monorepo_root):
    d = str(monorepo_root / "docs" / "workspace" / "findings")
    result = next_sequence(d, "findings")
    assert result == {"next": 1, "formatted": "001"}


def test_next_seq_existing(monorepo_root):
    findings_dir = monorepo_root / "docs" / "workspace" / "findings"
    (findings_dir / "findings.003-topic-a.md").touch()
    (findings_dir / "findings.007-topic-b.md").touch()
    result = next_sequence(str(findings_dir), "findings")
    assert result == {"next": 8, "formatted": "008"}


def test_next_seq_decision(monorepo_root):
    decisions_dir = monorepo_root / "docs" / "workspace" / "decisions"
    (decisions_dir / "decision-002-auth.md").touch()
    (decisions_dir / "decision-005-storage.md").touch()
    result = next_sequence(str(decisions_dir), "decision")
    assert result == {"next": 6, "formatted": "006"}


def test_next_seq_nonexistent_dir(tmp_path):
    result = next_sequence(str(tmp_path / "nonexistent"), "findings")
    assert result == {"next": 1, "formatted": "001"}


def test_check_progress_not_exists(monorepo_root):
    d = str(monorepo_root / "docs" / "workspace")
    result = check_progress(d)
    assert result["exists"] is False
    assert result["date"] == date.today().isoformat()


def test_check_progress_exists(monorepo_root):
    today = date.today().isoformat()
    progress_dir = monorepo_root / "docs" / "workspace" / "progress"
    (progress_dir / f"progress.{today}.md").touch()
    result = check_progress(str(monorepo_root / "docs" / "workspace"))
    assert result["exists"] is True
    assert result["date"] == today


def test_check_progress_specific_date(monorepo_root):
    progress_dir = monorepo_root / "docs" / "workspace" / "progress"
    (progress_dir / "progress.2026-01-15.md").touch()
    result = check_progress(
        str(monorepo_root / "docs" / "workspace"), target_date="2026-01-15"
    )
    assert result["exists"] is True
    assert result["date"] == "2026-01-15"
