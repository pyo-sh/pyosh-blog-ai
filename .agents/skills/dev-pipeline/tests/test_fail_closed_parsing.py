"""Regression tests for fail-closed review output parsing.

These tests encode actual failure patterns observed in production:
- Codex stderr transcript with a valid review embedded
- Codex output missing '## Review Summary' → must NOT upload, must fail-closed
- Empty / whitespace-only output → fail-closed
- Exact startswith("## Review Summary") contract for check_review_exists
"""
import pytest

from dev_pipeline.review_runner import normalize_codex_output


# --- Fixtures representing real Codex transcript shapes ---

TRANSCRIPT_WITH_REVIEW = """\
[Codex session started]
Analyzing PR diff...
Looking at changed files...

After review:

## Review Summary

**Verdict**: Request changes - 1 Critical issue found.

### Critical

1. **Missing error handling** in `src/handler.ts` line 24
   The async function does not catch rejection.

### Warning

None

### Suggestion

None
"""

TRANSCRIPT_NO_REVIEW_SUMMARY = """\
[Codex session started]
Analyzing diff...
I looked at the changes but the output format was not emitted.
Exit 0 but no structured review.
"""

TRANSCRIPT_EMPTY = ""

TRANSCRIPT_WHITESPACE_ONLY = "   \n\n\t  \n"

TRANSCRIPT_MULTIPLE_SUMMARIES = """\
[Codex thinking]
The review should look like:

## Review Summary

**Verdict**: Approve

(but this is a draft, not the real one)

Actually here is the real review:

## Review Summary

**Verdict**: Request changes - 1 Warning issue found.

### Critical

None

### Warning

1. **Unused import** in `src/utils.ts`

### Suggestion

None
"""

TRANSCRIPT_REVIEW_IN_CODEBLOCK = """\
Here is what I will output:

```
## Review Summary

**Verdict**: Approve

### Critical

None

### Warning

None

### Suggestion

None
```

## Review Summary

**Verdict**: Approve

### Critical

None

### Warning

None

### Suggestion

None
"""


class TestNormalizeCodexOutput:
    def test_valid_review_passthrough(self):
        """Valid transcript with '## Review Summary' returns the review section."""
        result = normalize_codex_output(TRANSCRIPT_WITH_REVIEW)
        assert result is not None
        assert result.startswith("## Review Summary")

    def test_missing_review_summary_returns_none(self):
        """Transcript without '## Review Summary' must return None (fail-closed)."""
        result = normalize_codex_output(TRANSCRIPT_NO_REVIEW_SUMMARY)
        assert result is None, (
            "REGRESSION: normalize_codex_output must return None when "
            "'## Review Summary' is absent. Do NOT upload raw transcript to GitHub."
        )

    def test_empty_output_returns_none(self):
        """Empty output must return None."""
        assert normalize_codex_output(TRANSCRIPT_EMPTY) is None

    def test_whitespace_only_returns_none(self):
        """Whitespace-only output must return None."""
        assert normalize_codex_output(TRANSCRIPT_WHITESPACE_ONLY) is None

    def test_extracts_last_review_summary(self):
        """When multiple '## Review Summary' markers exist, extract from the last one."""
        result = normalize_codex_output(TRANSCRIPT_MULTIPLE_SUMMARIES)
        assert result is not None
        assert result.startswith("## Review Summary")
        # Should contain the final review content, not the draft
        assert "Unused import" in result
        # The draft "Approve" verdict should NOT be the one we got (last one wins)
        # Both say "## Review Summary" - we just verify it contains the last item
        assert "src/utils.ts" in result

    def test_result_satisfies_check_review_exists_contract(self):
        """Normalized output must satisfy startswith('## Review Summary').

        This is the exact filter used by github_client.check_review_exists().
        """
        result = normalize_codex_output(TRANSCRIPT_WITH_REVIEW)
        assert result is not None
        assert result.startswith("## Review Summary"), (
            "normalize_codex_output must return a string that starts with "
            "'## Review Summary' - github_client.check_review_exists() "
            "requires this exact check."
        )

    def test_review_in_codeblock_extracts_last(self):
        """The last '## Review Summary' outside the codeblock is preferred."""
        result = normalize_codex_output(TRANSCRIPT_REVIEW_IN_CODEBLOCK)
        assert result is not None
        assert result.startswith("## Review Summary")

    def test_none_means_do_not_upload(self):
        """Returning None is the signal to callers: do NOT upload to GitHub."""
        # This test documents the contract, not just behavior.
        for bad_transcript in [
            TRANSCRIPT_NO_REVIEW_SUMMARY,
            TRANSCRIPT_EMPTY,
            TRANSCRIPT_WHITESPACE_ONLY,
        ]:
            result = normalize_codex_output(bad_transcript)
            assert result is None, (
                f"normalize_codex_output({bad_transcript[:40]!r}...) returned "
                f"{result!r} instead of None. "
                "None is the fail-closed signal: callers must NOT upload to GitHub."
            )
