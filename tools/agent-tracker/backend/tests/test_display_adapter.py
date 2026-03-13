"""Tests for display_adapter: east_asian_display_width (replaces wc -L)."""

from __future__ import annotations

import pytest

from backend.adapters.display_adapter import east_asian_display_width


class TestAsciiStrings:
    def test_empty(self) -> None:
        assert east_asian_display_width("") == 0

    def test_ascii_word(self) -> None:
        assert east_asian_display_width("hello") == 5

    def test_ascii_with_spaces(self) -> None:
        assert east_asian_display_width("hello world") == 11

    def test_single_char(self) -> None:
        assert east_asian_display_width("A") == 1


class TestCjkStrings:
    def test_single_cjk(self) -> None:
        # 가 (U+AC00) is Wide
        assert east_asian_display_width("가") == 2

    def test_chinese_chars(self) -> None:
        # 中文 (two CJK characters)
        assert east_asian_display_width("中文") == 4

    def test_japanese_kanji(self) -> None:
        # 日本語 (three kanji)
        assert east_asian_display_width("日本語") == 6

    def test_mixed_ascii_cjk(self) -> None:
        # "A가B" → 1 + 2 + 1 = 4
        assert east_asian_display_width("A가B") == 4

    def test_fullwidth_ascii(self) -> None:
        # Ａ (U+FF21) is Fullwidth → width 2
        assert east_asian_display_width("Ａ") == 2


class TestSpecialCharacters:
    def test_latin_extended(self) -> None:
        # é (U+00E9) is Narrow → width 1
        assert east_asian_display_width("é") == 1

    def test_emoji_is_wide(self) -> None:
        # 😀 (U+1F600) East_Asian_Width=W → width 2
        assert east_asian_display_width("😀") == 2

    def test_newline_counts_as_one(self) -> None:
        # \n is Neutral → 1 (wc -L behaviour may differ, but this tests the function)
        assert east_asian_display_width("\n") == 1

    def test_long_mixed_string(self) -> None:
        # "Fix 問題 now" → F(1)+i(1)+x(1)+sp(1)+問(2)+題(2)+sp(1)+n(1)+o(1)+w(1) = 12
        assert east_asian_display_width("Fix 問題 now") == 12
