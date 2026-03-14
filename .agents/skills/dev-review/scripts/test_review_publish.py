"""Regression tests for review_publish.py.

Covers: schema validation, contamination detection, markdown rendering,
CLI dry-run mode, and publish arg enforcement.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

# Import the module under test
sys.path.insert(0, str(Path(__file__).resolve().parent))
from review_publish import (
    check_contamination,
    render_markdown,
    validate_payload,
    main,
)

PUBLISHER = str(Path(__file__).resolve().parent / "review_publish.py")

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

VALID_PAYLOAD = {
    "verdict": "request_changes",
    "summary": "Found one critical issue in error handling.",
    "issues": [
        {
            "severity": "P1",
            "path": "src/app.ts",
            "line": 42,
            "title": "Unhandled promise rejection",
            "body": "The async handler does not catch errors.",
        }
    ],
}

APPROVE_PAYLOAD = {
    "verdict": "approve",
    "summary": "No issues found.",
    "issues": [],
}


@pytest.fixture
def valid_json(tmp_path):
    p = tmp_path / "review.json"
    p.write_text(json.dumps(VALID_PAYLOAD))
    return p


@pytest.fixture
def approve_json(tmp_path):
    p = tmp_path / "review.json"
    p.write_text(json.dumps(APPROVE_PAYLOAD))
    return p


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------

class TestValidatePayload:
    def test_valid_payload(self):
        assert validate_payload(VALID_PAYLOAD) == []

    def test_valid_approve(self):
        assert validate_payload(APPROVE_PAYLOAD) == []

    def test_missing_verdict(self):
        payload = {"summary": "ok", "issues": []}
        errors = validate_payload(payload)
        assert any("verdict" in e for e in errors)

    def test_invalid_verdict(self):
        payload = {"verdict": "reject", "summary": "ok", "issues": []}
        errors = validate_payload(payload)
        assert any("verdict" in e for e in errors)

    def test_missing_summary(self):
        payload = {"verdict": "approve", "issues": []}
        errors = validate_payload(payload)
        assert any("summary" in e for e in errors)

    def test_summary_too_long(self):
        payload = {"verdict": "approve", "summary": "x" * 2001, "issues": []}
        errors = validate_payload(payload)
        assert any("2000" in e for e in errors)

    def test_missing_issues(self):
        payload = {"verdict": "approve", "summary": "ok"}
        errors = validate_payload(payload)
        assert any("issues" in e for e in errors)

    def test_too_many_issues(self):
        issues = [{"severity": "P3", "title": "t", "body": "b"}] * 51
        payload = {"verdict": "comment", "summary": "ok", "issues": issues}
        errors = validate_payload(payload)
        assert any("51" in e for e in errors)

    def test_invalid_severity(self):
        payload = {
            "verdict": "comment",
            "summary": "ok",
            "issues": [{"severity": "HIGH", "title": "t", "body": "b"}],
        }
        errors = validate_payload(payload)
        assert any("severity" in e for e in errors)

    def test_all_valid_severities(self):
        for sev in ("P0", "P1", "P2", "P3", "info"):
            payload = {
                "verdict": "comment",
                "summary": "ok",
                "issues": [{"severity": sev, "title": "t", "body": "b"}],
            }
            assert validate_payload(payload) == [], f"severity {sev} should be valid"

    def test_missing_title(self):
        payload = {
            "verdict": "comment",
            "summary": "ok",
            "issues": [{"severity": "P1", "body": "b"}],
        }
        errors = validate_payload(payload)
        assert any("title" in e for e in errors)

    def test_unknown_top_key(self):
        payload = {"verdict": "approve", "summary": "ok", "issues": [], "extra": 1}
        errors = validate_payload(payload)
        assert any("unknown keys" in e for e in errors)

    def test_unknown_issue_key(self):
        payload = {
            "verdict": "comment",
            "summary": "ok",
            "issues": [{"severity": "P1", "title": "t", "body": "b", "xxx": 1}],
        }
        errors = validate_payload(payload)
        assert any("unknown keys" in e for e in errors)

    def test_line_must_be_positive_int(self):
        payload = {
            "verdict": "comment",
            "summary": "ok",
            "issues": [{"severity": "P1", "title": "t", "body": "b", "line": 0}],
        }
        errors = validate_payload(payload)
        assert any("line" in e for e in errors)

    def test_not_a_dict(self):
        errors = validate_payload([])
        assert errors == ["payload is not a JSON object"]

    def test_null_path_is_valid(self):
        payload = {
            "verdict": "comment",
            "summary": "ok",
            "issues": [{"severity": "P1", "path": None, "title": "t", "body": "b"}],
        }
        assert validate_payload(payload) == []

    def test_null_line_is_valid(self):
        payload = {
            "verdict": "comment",
            "summary": "ok",
            "issues": [{"severity": "P1", "line": None, "title": "t", "body": "b"}],
        }
        assert validate_payload(payload) == []


# ---------------------------------------------------------------------------
# Contamination check
# ---------------------------------------------------------------------------

class TestContamination:
    def test_clean_payload(self):
        assert check_contamination(VALID_PAYLOAD) == []

    def test_skill_frontmatter_in_summary(self):
        payload = {
            "verdict": "comment",
            "summary": "---\nname: dev-review\ndescription: leak",
            "issues": [],
        }
        findings = check_contamination(payload)
        assert len(findings) > 0
        assert any("frontmatter" in f for f in findings)

    def test_pipeline_env_var_in_body(self):
        payload = {
            "verdict": "comment",
            "summary": "ok",
            "issues": [{
                "severity": "P1",
                "title": "t",
                "body": "Use PIPELINE_MONOREPO_ROOT to find root.",
            }],
        }
        findings = check_contamination(payload)
        assert len(findings) > 0
        assert any("env var" in f for f in findings)

    def test_cli_flag_leak(self):
        payload = {
            "verdict": "comment",
            "summary": "Run with --dangerously-skip-permissions",
            "issues": [],
        }
        findings = check_contamination(payload)
        assert len(findings) > 0

    def test_system_prompt_tag(self):
        payload = {
            "verdict": "comment",
            "summary": "ok",
            "issues": [{
                "severity": "P1",
                "title": "t",
                "body": "Found <system-reminder> tag in output.",
            }],
        }
        findings = check_contamination(payload)
        assert len(findings) > 0

    def test_skill_section_header(self):
        payload = {
            "verdict": "comment",
            "summary": "## Runtime contract when invoked by dev-pipeline",
            "issues": [],
        }
        findings = check_contamination(payload)
        assert len(findings) > 0


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------

class TestRenderMarkdown:
    def test_starts_with_review_summary(self):
        md = render_markdown(VALID_PAYLOAD)
        assert md.startswith("## Review Summary")

    def test_severity_table(self):
        md = render_markdown(VALID_PAYLOAD)
        assert "| [CRITICAL] | 1 |" in md
        assert "| [WARNING] | 0 |" in md
        assert "| [SUGGESTION] | 0 |" in md
        assert "| [INFO] | 0 |" in md

    def test_critical_section(self):
        md = render_markdown(VALID_PAYLOAD)
        assert "### Critical" in md
        assert "`src/app.ts:42`" in md
        assert "Unhandled promise rejection" in md

    def test_approve_no_sections(self):
        md = render_markdown(APPROVE_PAYLOAD)
        assert "### Critical" not in md
        assert "| [CRITICAL] | 0 |" in md
        assert "| [INFO] | 0 |" in md

    def test_info_severity_counted(self):
        payload = {
            "verdict": "comment",
            "summary": "ok",
            "issues": [
                {"severity": "info", "title": "FYI", "body": "Just a note."},
            ],
        }
        md = render_markdown(payload)
        assert "| [INFO] | 1 |" in md
        assert "### Info" in md

    def test_p0_and_p1_merged_in_critical(self):
        payload = {
            "verdict": "request_changes",
            "summary": "ok",
            "issues": [
                {"severity": "P0", "title": "immediate", "body": "fix now"},
                {"severity": "P1", "title": "must fix", "body": "fix soon"},
            ],
        }
        md = render_markdown(payload)
        # Both should be in Critical section, count should be 2
        assert "| [CRITICAL] | 2 |" in md
        assert md.count("### Critical") == 1
        assert "immediate" in md
        assert "must fix" in md

    def test_suggested_fix_rendered(self):
        payload = {
            "verdict": "comment",
            "summary": "ok",
            "issues": [{
                "severity": "P2",
                "title": "Style issue",
                "body": "Inconsistent naming.",
                "suggested_fix": "Rename to camelCase.",
            }],
        }
        md = render_markdown(payload)
        assert "**Suggested fix:**" in md
        assert "Rename to camelCase." in md

    def test_ends_with_newline(self):
        md = render_markdown(VALID_PAYLOAD)
        assert md.endswith("\n")

    def test_null_path_renders_without_location(self):
        payload = {
            "verdict": "comment",
            "summary": "ok",
            "issues": [{"severity": "P1", "path": None, "title": "General issue", "body": "Details."}],
        }
        md = render_markdown(payload)
        assert "General issue" in md
        assert "`" not in md.split("General issue")[0].split("\n")[-1]

    def test_null_line_renders_path_without_line(self):
        payload = {
            "verdict": "comment",
            "summary": "ok",
            "issues": [{"severity": "P1", "path": "src/foo.ts", "line": None, "title": "Issue", "body": "Details."}],
        }
        md = render_markdown(payload)
        assert "`src/foo.ts`" in md
        assert "`src/foo.ts:" not in md


# ---------------------------------------------------------------------------
# CLI integration (dry-run only)
# ---------------------------------------------------------------------------

class TestCLI:
    def test_dry_run_valid(self, valid_json, tmp_path):
        rc = main(["--input", str(valid_json), "--mode", "dry-run",
                    "--output-dir", str(tmp_path / "out")])
        assert rc == 0
        assert (tmp_path / "out" / "review.md").exists()

    def test_dry_run_prints_markdown(self, valid_json, capsys):
        rc = main(["--input", str(valid_json), "--mode", "dry-run"])
        assert rc == 0
        captured = capsys.readouterr()
        assert "## Review Summary" in captured.out

    def test_invalid_json_file(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("not json")
        rc = main(["--input", str(bad), "--mode", "dry-run"])
        assert rc == 1

    def test_missing_input_file(self, tmp_path):
        rc = main(["--input", str(tmp_path / "missing.json"), "--mode", "dry-run"])
        assert rc == 1

    def test_schema_validation_blocks_publish(self, tmp_path):
        bad = tmp_path / "review.json"
        bad.write_text(json.dumps({"verdict": "approve", "issues": []}))
        rc = main(["--input", str(bad), "--mode", "dry-run"])
        assert rc == 1

    def test_contamination_blocks_publish(self, tmp_path):
        payload = {
            "verdict": "approve",
            "summary": "Run --dangerously-skip-permissions for access.",
            "issues": [],
        }
        p = tmp_path / "review.json"
        p.write_text(json.dumps(payload))
        rc = main(["--input", str(p), "--mode", "dry-run"])
        assert rc == 1

    def test_publish_requires_repo_and_pr(self, valid_json):
        """publish mode without --repo/--pr must fail at arg parsing."""
        with pytest.raises(SystemExit) as exc:
            main(["--input", str(valid_json), "--mode", "publish"])
        assert exc.value.code == 2
