import base64
import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ReviewCounts:
    critical: int
    warning: int
    suggestion: int


@dataclass
class ReviewItem:
    severity: str       # "critical" | "warning" | "suggestion"
    file: str           # normalized file path, or "" if not found
    message: str        # first line of the item text (normalized)
    fingerprint: str    # sha1 of "{severity}:{file}:{message_normalized}"
    raw: str            # full item text as extracted


@dataclass
class ParsedReview:
    counts: ReviewCounts
    items: List[ReviewItem] = field(default_factory=list)


# Markers used in review body to embed machine-readable metadata.
# -b64 variant: base64-encoded JSON, immune to --> injection from model output.
# Plain variant: kept for backward compatibility with older review bodies.
_META_PREFIX_B64 = "<!-- dev-pipeline-meta-b64:"
_META_PREFIX = "<!-- dev-pipeline-meta:"
_META_SUFFIX = "-->"


def _extract_meta(body: str) -> Optional[dict]:
    """Extract embedded JSON metadata from review body, if present.

    Tries the base64 format first (<!-- dev-pipeline-meta-b64: ... -->), then
    falls back to the plain JSON format (<!-- dev-pipeline-meta: ... -->).
    """
    # Base64 format (preferred, immune to --> injection)
    start = body.find(_META_PREFIX_B64)
    if start != -1:
        end = body.find(_META_SUFFIX, start)
        if end != -1:
            raw_b64 = body[start + len(_META_PREFIX_B64):end].strip()
            try:
                raw_json = base64.b64decode(raw_b64.encode()).decode()
                return json.loads(raw_json)
            except Exception:
                pass  # fall through to plain format

    # Plain JSON format (backward compatibility)
    start = body.find(_META_PREFIX)
    if start == -1:
        return None
    end = body.find(_META_SUFFIX, start)
    if end == -1:
        return None
    raw_json = body[start + len(_META_PREFIX):end].strip()
    try:
        return json.loads(raw_json)
    except json.JSONDecodeError:
        return None


def _normalize_message(text: str) -> str:
    """Strip volatile formatting from a review item message before fingerprinting.

    Removes:
    - Markdown bold/italic (**text**, *text*)
    - Inline code spans (`code`) — file path already extracted separately
    - Line number references (line 24, lines 10-20)
    - Leading/trailing whitespace; collapses internal whitespace
    """
    # Remove bold/italic markers
    text = re.sub(r'\*+([^*]*)\*+', r'\1', text)
    # Remove inline code spans entirely (file info is in the separate `file` field)
    text = re.sub(r'`[^`]*`', '', text)
    # Remove line number references
    text = re.sub(r'\blines?\s+\d+(?:[-\u2013]\d+)?', '', text, flags=re.IGNORECASE)
    # Collapse whitespace
    return re.sub(r'\s+', ' ', text).strip().lower()


def _make_fingerprint(severity: str, file: str, message: str) -> str:
    """Return a short fingerprint for a review item.

    Normalizes message before hashing so that minor formatting changes
    (bold, line numbers, file path duplication) do not produce different
    fingerprints for the same logical finding.
    """
    normalized = f"{severity}:{file}:{_normalize_message(message)}"
    return hashlib.sha1(normalized.encode()).hexdigest()[:16]


def _extract_file(text: str) -> str:
    """Extract a file path from item text.

    Handles:
    - Bare backtick path: `src/foo.ts`
    - Backtick path with line reference: `src/foo.ts:265`  (line excluded from result)
    - Prose 'in src/...' pattern
    """
    # backtick path, optionally followed by :line before the closing backtick
    m = re.search(r"`([^`]+\.[a-zA-Z]{1,10})(?::\d+)?`", text)
    if m:
        return m.group(1)
    # "in src/..." pattern
    m = re.search(r"\bin\s+([\w./-]+\.[a-zA-Z]{1,10})", text)
    if m:
        return m.group(1)
    return ""


def parse_review_body(body: str) -> ReviewCounts:
    """Parse review body sections and count numbered items per section.

    Raises ValueError if the '## Review Summary' header is absent.
    """
    result = parse_review_body_full(body)
    return result.counts


def parse_review_body_full(body: str) -> ParsedReview:
    """Parse review body into counts and structured items with fingerprints.

    Priority order:
      1. Embedded JSON metadata (<!-- dev-pipeline-meta: {...} -->)
      2. Markdown section parsing
      3. Raises ValueError if '## Review Summary' is absent

    Raises ValueError if the '## Review Summary' header is absent.
    """
    if "## Review Summary" not in body:
        raise ValueError(
            '[review_normalizer] parse error: review body missing "## Review Summary"'
            " - wrong format or empty review"
        )

    # Try embedded metadata first
    meta = _extract_meta(body)
    if meta is not None:
        try:
            counts = ReviewCounts(
                critical=int(meta.get("critical", 0)),
                warning=int(meta.get("warning", 0)),
                suggestion=int(meta.get("suggestion", 0)),
            )
            items = []
            for raw_item in meta.get("items", []):
                severity = raw_item.get("severity", "")
                file = raw_item.get("file", "")
                message = raw_item.get("message", "")
                fp = raw_item.get("fingerprint") or _make_fingerprint(severity, file, message)
                items.append(ReviewItem(
                    severity=severity,
                    file=file,
                    message=message,
                    fingerprint=fp,
                    raw=raw_item.get("raw", ""),
                ))
            return ParsedReview(counts=counts, items=items)
        except (TypeError, ValueError):
            pass  # fall through to markdown parsing

    # Markdown section parsing
    critical = 0
    warning = 0
    suggestion = 0
    section = None
    items = []

    current_item_lines: List[str] = []
    current_severity: Optional[str] = None

    def _flush_item() -> None:
        if not current_item_lines or current_severity is None:
            return
        raw = "\n".join(current_item_lines).strip()
        first_line = current_item_lines[0].strip()
        # strip leading "N. " numbering
        first_line = re.sub(r"^\d+\.\s*", "", first_line)
        file = _extract_file(raw)
        fp = _make_fingerprint(current_severity, file, first_line)
        items.append(ReviewItem(
            severity=current_severity,
            file=file,
            message=first_line,
            fingerprint=fp,
            raw=raw,
        ))

    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("### Critical"):
            _flush_item()
            current_item_lines = []
            current_severity = None
            section = "critical"
        elif stripped.startswith("### Warning"):
            _flush_item()
            current_item_lines = []
            current_severity = None
            section = "warning"
        elif stripped.startswith("### Suggestion"):
            _flush_item()
            current_item_lines = []
            current_severity = None
            section = "suggestion"
        elif stripped.startswith("### "):
            _flush_item()
            current_item_lines = []
            current_severity = None
            section = None
        elif section and re.match(r"^\d+\.", stripped):
            _flush_item()
            current_item_lines = [line]
            current_severity = section
            if section == "critical":
                critical += 1
            elif section == "warning":
                warning += 1
            elif section == "suggestion":
                suggestion += 1
        elif current_item_lines:
            current_item_lines.append(line)

    _flush_item()

    counts = ReviewCounts(critical=critical, warning=warning, suggestion=suggestion)
    return ParsedReview(counts=counts, items=items)


# --- Convergence detection ---

class ConvergenceTag(str):
    NEW = "new"
    REPEATED = "repeated"
    REOPENED = "reopened"
    CONTRADICTORY = "contradictory"


@dataclass
class ClassifiedItem:
    item: ReviewItem
    tag: str  # ConvergenceTag value


def classify_review_items(
    new_items: List[ReviewItem],
    previous_fingerprints: set,
    resolved_fingerprints: set,
) -> List[ClassifiedItem]:
    """Classify each new review item against prior review history.

    Tags:
      new          - not seen before
      repeated     - seen in a previous round and not resolved
      reopened     - was marked resolved but appeared again
      contradictory - same file+message in a different severity than before
                     (not implemented here; requires per-item severity history)
    """
    classified = []
    for item in new_items:
        if item.fingerprint in resolved_fingerprints:
            tag = ConvergenceTag.REOPENED
        elif item.fingerprint in previous_fingerprints:
            tag = ConvergenceTag.REPEATED
        else:
            tag = ConvergenceTag.NEW
        classified.append(ClassifiedItem(item=item, tag=tag))
    return classified


def is_no_progress(classified: List[ClassifiedItem], threshold: int = 2) -> bool:
    """Return True if the same issue category has appeared >= threshold times (no_progress)."""
    repeated_count = sum(1 for c in classified if c.tag in (ConvergenceTag.REPEATED, ConvergenceTag.REOPENED))
    return repeated_count >= threshold
