"""Tests for review convergence detection and fingerprinting.

Covers:
- ReviewItem fingerprint stability
- classify_review_items tagging (new / repeated / reopened)
- is_no_progress detection
- parse_review_body_full with embedded metadata
"""
import pytest

from dev_pipeline.review_normalizer import (
    ClassifiedItem,
    ConvergenceTag,
    ParsedReview,
    ReviewItem,
    classify_review_items,
    is_no_progress,
    parse_review_body_full,
    _make_fingerprint,
)


REVIEW_WITH_ISSUES = """## Review Summary

**Verdict**: Request changes - 2 issues found.

### Critical

1. **Null pointer** in `src/handler.ts` line 10

### Warning

1. **Unused import** in `src/utils.ts`

### Suggestion

None
"""

REVIEW_SAME_ISSUES_SECOND_ROUND = """## Review Summary

**Verdict**: Request changes - same issues persist.

### Critical

1. **Null pointer** in `src/handler.ts` line 10

### Warning

1. **Unused import** in `src/utils.ts`

### Suggestion

None
"""

REVIEW_WITH_META = """## Review Summary

**Verdict**: Request changes - 1 Critical issue found.

### Critical

1. **Missing validation** in `src/api.ts`

### Warning

None

### Suggestion

None

<!-- dev-pipeline-meta: {"critical":1,"warning":0,"suggestion":0,"items":[{"severity":"critical","file":"src/api.ts","message":"Missing validation","fingerprint":"abc123def456","raw":"Missing validation in src/api.ts"}]} -->
"""


class TestFingerprint:
    def test_fingerprint_is_deterministic(self):
        fp1 = _make_fingerprint("critical", "src/foo.ts", "Null pointer")
        fp2 = _make_fingerprint("critical", "src/foo.ts", "Null pointer")
        assert fp1 == fp2

    def test_different_severity_different_fingerprint(self):
        fp1 = _make_fingerprint("critical", "src/foo.ts", "Null pointer")
        fp2 = _make_fingerprint("warning", "src/foo.ts", "Null pointer")
        assert fp1 != fp2

    def test_different_file_different_fingerprint(self):
        fp1 = _make_fingerprint("critical", "src/foo.ts", "Null pointer")
        fp2 = _make_fingerprint("critical", "src/bar.ts", "Null pointer")
        assert fp1 != fp2

    def test_case_and_whitespace_normalized(self):
        fp1 = _make_fingerprint("critical", "src/foo.ts", "Null Pointer")
        fp2 = _make_fingerprint("critical", "src/foo.ts", "null  pointer")
        assert fp1 == fp2

    def test_bold_markdown_stripped(self):
        """**Finding** and Finding produce the same fingerprint.

        REGRESSION: review items like '**Missing validation** in src/api.ts'
        would hash differently if the bold markers were included.
        """
        fp1 = _make_fingerprint("critical", "src/api.ts", "**Missing validation** in src/api.ts")
        fp2 = _make_fingerprint("critical", "src/api.ts", "Missing validation in src/api.ts")
        assert fp1 == fp2

    def test_line_number_stripped(self):
        """Same finding at different line numbers must produce the same fingerprint.

        REGRESSION: 'Missing validation line 24' and 'Missing validation line 31'
        would hash differently, causing repeated findings to be classified as new.
        """
        fp1 = _make_fingerprint("critical", "src/api.ts", "Missing validation line 24")
        fp2 = _make_fingerprint("critical", "src/api.ts", "Missing validation line 31")
        assert fp1 == fp2

    def test_line_range_stripped(self):
        fp1 = _make_fingerprint("warning", "src/foo.ts", "Unused import lines 10-20")
        fp2 = _make_fingerprint("warning", "src/foo.ts", "Unused import lines 15-25")
        assert fp1 == fp2

    def test_inline_code_stripped(self):
        """Inline code spans removed; file info is in the separate file field."""
        fp1 = _make_fingerprint("critical", "src/api.ts", "Missing validation in `src/api.ts`")
        fp2 = _make_fingerprint("critical", "src/api.ts", "Missing validation in")
        assert fp1 == fp2


from dev_pipeline.review_normalizer import _extract_file


class TestExtractFile:
    def test_bare_backtick_path(self):
        assert _extract_file("Bug in `src/foo.ts`") == "src/foo.ts"

    def test_backtick_path_with_line_reference(self):
        """path:line format must return only the file path, not the line number.

        REGRESSION: `.agents/.../cli.py:265` yielded file="" because the regex
        required the backtick to close immediately after the extension.
        Two findings with identical messages but different files would then share
        the same fingerprint and be mis-tagged as repeated across files.
        """
        result = _extract_file("`.agents/skills/dev-pipeline/scripts/dev_pipeline/cli.py:265`")
        assert result == ".agents/skills/dev-pipeline/scripts/dev_pipeline/cli.py"

    def test_backtick_path_line_not_in_result(self):
        """Line number must be excluded from the returned file path."""
        result = _extract_file("`src/handler.ts:42`")
        assert result == "src/handler.ts"
        assert ":42" not in result

    def test_different_files_different_fingerprint_with_line_ref(self):
        """Cross-file findings must hash differently even with identical messages.

        REGRESSION: if _extract_file() returns "" for path:line format, two findings
        in different files with the same wording get identical fingerprints and the
        convergence classifier treats them as the same issue.
        """
        fp1 = _make_fingerprint("critical", _extract_file("`src/foo.ts:10`"), "Missing check")
        fp2 = _make_fingerprint("critical", _extract_file("`src/bar.ts:10`"), "Missing check")
        assert fp1 != fp2

    def test_in_prose_pattern(self):
        assert _extract_file("Missing check in src/utils.ts line 5") == "src/utils.ts"

    def test_no_file_returns_empty(self):
        assert _extract_file("This finding has no file reference") == ""


class TestParseReviewBodyFull:
    def test_returns_parsed_review(self):
        result = parse_review_body_full(REVIEW_WITH_ISSUES)
        assert isinstance(result, ParsedReview)
        assert result.counts.critical == 1
        assert result.counts.warning == 1
        assert result.counts.suggestion == 0

    def test_items_have_fingerprints(self):
        result = parse_review_body_full(REVIEW_WITH_ISSUES)
        assert len(result.items) == 2
        for item in result.items:
            assert item.fingerprint
            assert len(item.fingerprint) == 16

    def test_items_have_severity(self):
        result = parse_review_body_full(REVIEW_WITH_ISSUES)
        severities = {item.severity for item in result.items}
        assert "critical" in severities
        assert "warning" in severities

    def test_meta_takes_priority_over_markdown(self):
        """Embedded JSON metadata must be used when present."""
        result = parse_review_body_full(REVIEW_WITH_META)
        assert result.counts.critical == 1
        assert result.counts.warning == 0
        # fingerprint from meta
        assert result.items[0].fingerprint == "abc123def456"

    def test_missing_header_raises(self):
        with pytest.raises(ValueError, match="Review Summary"):
            parse_review_body_full("No header here.")


class TestConvergenceDetection:
    def test_new_items_tagged_new(self):
        result = parse_review_body_full(REVIEW_WITH_ISSUES)
        classified = classify_review_items(result.items, set(), set())
        assert all(c.tag == ConvergenceTag.NEW for c in classified)

    def test_repeated_items_tagged_repeated(self):
        """Same fingerprints in round 2 → REPEATED.

        REGRESSION: 11-round non-convergence happened because the same items
        kept appearing without being detected as repeated.
        """
        round1 = parse_review_body_full(REVIEW_WITH_ISSUES)
        previous_fps = {item.fingerprint for item in round1.items}

        round2 = parse_review_body_full(REVIEW_SAME_ISSUES_SECOND_ROUND)
        classified = classify_review_items(round2.items, previous_fps, set())

        repeated = [c for c in classified if c.tag == ConvergenceTag.REPEATED]
        assert len(repeated) >= 1, (
            "REGRESSION: same review items must be tagged REPEATED in round 2. "
            "Non-convergence detection depends on this."
        )

    def test_reopened_items_tagged_reopened(self):
        result = parse_review_body_full(REVIEW_WITH_ISSUES)
        fps = {item.fingerprint for item in result.items}
        # Mark all as resolved, then present same items again
        classified = classify_review_items(result.items, fps, fps)
        reopened = [c for c in classified if c.tag == ConvergenceTag.REOPENED]
        assert len(reopened) >= 1

    def test_is_no_progress_false_for_all_new(self):
        result = parse_review_body_full(REVIEW_WITH_ISSUES)
        classified = classify_review_items(result.items, set(), set())
        assert is_no_progress(classified) is False

    def test_is_no_progress_true_when_enough_repeated(self):
        """is_no_progress must return True when >= threshold items repeat.

        REGRESSION: 11-round loop had 2+ repeated items each round.
        """
        items = [
            ReviewItem(severity="critical", file="a.ts", message="bug1",
                       fingerprint="fp1", raw=""),
            ReviewItem(severity="warning", file="b.ts", message="bug2",
                       fingerprint="fp2", raw=""),
        ]
        classified = [
            ClassifiedItem(item=items[0], tag=ConvergenceTag.REPEATED),
            ClassifiedItem(item=items[1], tag=ConvergenceTag.REPEATED),
        ]
        assert is_no_progress(classified, threshold=2) is True

    def test_is_no_progress_false_below_threshold(self):
        items = [
            ReviewItem(severity="critical", file="a.ts", message="bug1",
                       fingerprint="fp1", raw=""),
        ]
        classified = [ClassifiedItem(item=items[0], tag=ConvergenceTag.REPEATED)]
        assert is_no_progress(classified, threshold=2) is False
