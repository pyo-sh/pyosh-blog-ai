#!/usr/bin/env python3
"""Read a string from stdin and print its terminal display width.

Cross-platform replacement for ``printf '%s' "$s" | wc -L`` (GNU only).
CJK Wide/Fullwidth characters count as 2; all others count as 1.

Usage (from util.sh):
    printf '%s' "$s" | python3 "$(dirname "$0")/display_width.py"
"""

import sys
import unicodedata


def display_width(s: str) -> int:
    width = 0
    for ch in s:
        eaw = unicodedata.east_asian_width(ch)
        if eaw in ("W", "F"):
            width += 2
        else:
            width += 1
    return width


if __name__ == "__main__":
    s = sys.stdin.read()
    print(display_width(s), end="")
