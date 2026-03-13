"""Display adapter - terminal width calculation using Python stdlib.

Replaces GNU-specific ``wc -L`` with unicodedata for CJK-aware display width.
Works on Linux, macOS, and WSL without external commands.
"""

from __future__ import annotations

import unicodedata


def east_asian_display_width(s: str) -> int:
    """Return terminal display width of s, counting CJK characters as width 2.

    Equivalent to ``printf '%s' "$s" | wc -L`` (GNU coreutils) but cross-platform.
    Wide (W) and Fullwidth (F) characters count as 2; all others count as 1.
    """
    width = 0
    for ch in s:
        eaw = unicodedata.east_asian_width(ch)
        if eaw in ("W", "F"):
            width += 2
        else:
            width += 1
    return width
