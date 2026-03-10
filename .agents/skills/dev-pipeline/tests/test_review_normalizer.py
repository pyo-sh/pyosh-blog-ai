"""Tests for review_normalizer.parse_review_body and codex output normalization."""
import pytest

from dev_pipeline.review_normalizer import ReviewCounts, parse_review_body
from dev_pipeline.review_runner import normalize_codex_output


VALID_REVIEW = """## Review Summary

**Verdict**: Request changes — 2 Critical issue(s) found.

Some summary paragraph here.

### Critical

1. **Missing null check** in `src/api.ts` line 42
2. **SQL injection risk** in `src/db.ts` line 17

### Warning

1. Unused import in `src/utils.ts`

### Suggestions

1. Consider adding a unit test for the new helper

"""

APPROVE_REVIEW = """## Review Summary

**Verdict**: Approve

Looks good overall.

### Critical

None

### Warning

None

### Suggestions

1. Minor: rename variable for clarity

"""


def test_parse_valid_review_counts():
    counts = parse_review_body(VALID_REVIEW)
    assert counts.critical == 2
    assert counts.warning == 1
    assert counts.suggestion == 1  # "### Suggestions" matches startswith("### Suggestion")


def test_parse_suggestion_section_variant():
    """Section header 'Suggestion' (singular) should also match."""
    body = """## Review Summary

**Verdict**: Approve

### Critical

None

### Warning

None

### Suggestion

1. Add a docstring
2. Use f-strings

"""
    counts = parse_review_body(body)
    assert counts.suggestion == 2


def test_parse_approve_review():
    counts = parse_review_body(APPROVE_REVIEW)
    assert counts.critical == 0
    assert counts.warning == 0
    assert counts.suggestion == 1


def test_parse_empty_sections():
    body = """## Review Summary

**Verdict**: Approve

### Critical

None

### Warning

### Suggestions

"""
    counts = parse_review_body(body)
    assert counts.critical == 0
    assert counts.warning == 0
    assert counts.suggestion == 0


def test_missing_header_raises():
    with pytest.raises(ValueError, match="Review Summary"):
        parse_review_body("Some random text without the header.")


def test_missing_header_empty_string():
    with pytest.raises(ValueError, match="Review Summary"):
        parse_review_body("")


def test_partial_header_raises():
    with pytest.raises(ValueError, match="Review Summary"):
        parse_review_body("# Review Summary\n\nNot the right level.")


def test_numbered_items_counted():
    """Only lines starting with digits + period are counted."""
    body = """## Review Summary

### Critical

1. First issue
2. Second issue
- Bullet point (not counted)
a. Letter item (not counted)
3. Third issue

### Warning

1. One warning

"""
    counts = parse_review_body(body)
    assert counts.critical == 3
    assert counts.warning == 1


def test_dataclass_fields():
    counts = ReviewCounts(critical=1, warning=2, suggestion=3)
    assert counts.critical == 1
    assert counts.warning == 2
    assert counts.suggestion == 3


# --- normalize_codex_output tests ---


def test_normalize_valid_codex_output():
    """Valid codex output starting with '## Review Summary' passes through."""
    result = normalize_codex_output(VALID_REVIEW)
    assert result == VALID_REVIEW
    counts = parse_review_body(result)
    assert counts.critical == 2


def test_normalize_invalid_codex_output():
    """Non-empty output without '## Review Summary' gets wrapped."""
    raw = "Some codex output that doesn't match the template.\nLine two."
    result = normalize_codex_output(raw)
    assert result is not None
    assert result.startswith("## Review Summary")
    counts = parse_review_body(result)
    assert counts.warning == 1
    assert counts.critical == 0
    assert counts.suggestion == 0


def test_normalize_empty_codex_output():
    """Empty or whitespace-only output returns None."""
    assert normalize_codex_output("") is None
    assert normalize_codex_output("   \n  \n") is None
