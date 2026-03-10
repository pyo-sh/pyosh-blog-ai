import re
from dataclasses import dataclass


@dataclass
class ReviewCounts:
    critical: int
    warning: int
    suggestion: int


def parse_review_body(body: str) -> ReviewCounts:
    """Parse review body sections and count numbered items per section.

    Raises ValueError if the '## Review Summary' header is absent.
    """
    if "## Review Summary" not in body:
        raise ValueError(
            '[review_normalizer] parse error: review body missing "## Review Summary"'
            " - wrong format or empty review"
        )

    critical = 0
    warning = 0
    suggestion = 0
    section = None

    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("### Critical"):
            section = "critical"
        elif stripped.startswith("### Warning"):
            section = "warning"
        elif stripped.startswith("### Suggestion"):
            section = "suggestion"
        elif stripped.startswith("### "):
            section = None

        if section and re.match(r"^\d+\.", stripped):
            if section == "critical":
                critical += 1
            elif section == "warning":
                warning += 1
            elif section == "suggestion":
                suggestion += 1

    return ReviewCounts(critical=critical, warning=warning, suggestion=suggestion)
