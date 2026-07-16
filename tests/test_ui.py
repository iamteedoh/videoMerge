# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for the terminal-styling helpers used by the interactive menu."""

import io
import unittest
import unittest.mock

import merge_videos as mv


class SupportsColorTests(unittest.TestCase):
    def test_disabled_when_no_color_set(self):
        with unittest.mock.patch.dict("os.environ", {"NO_COLOR": "1"}):
            self.assertFalse(mv._supports_color(_tty(True)))

    def test_disabled_for_dumb_terminal(self):
        with unittest.mock.patch.dict("os.environ", {"TERM": "dumb"}, clear=False):
            os = mv.os
            os.environ.pop("NO_COLOR", None)
            self.assertFalse(mv._supports_color(_tty(True)))

    def test_disabled_for_non_tty(self):
        with unittest.mock.patch.dict("os.environ", {}, clear=False):
            mv.os.environ.pop("NO_COLOR", None)
            mv.os.environ.pop("TERM", None)
            self.assertFalse(mv._supports_color(_tty(False)))

    def test_enabled_for_plain_tty(self):
        with unittest.mock.patch.dict("os.environ", {}, clear=False):
            mv.os.environ.pop("NO_COLOR", None)
            mv.os.environ.pop("TERM", None)
            self.assertTrue(mv._supports_color(_tty(True)))


class PaintTests(unittest.TestCase):
    def test_returns_plain_text_when_color_disabled(self):
        with unittest.mock.patch.object(mv, "COLOR", False):
            self.assertEqual(mv.paint("hello", mv.BOLD, mv.CYAN), "hello")

    def test_wraps_in_sgr_codes_when_enabled(self):
        with unittest.mock.patch.object(mv, "COLOR", True):
            self.assertEqual(
                mv.paint("hi", mv.BOLD, mv.CYAN), "\033[1;96mhi\033[0m"
            )

    def test_no_codes_returns_plain_text(self):
        with unittest.mock.patch.object(mv, "COLOR", True):
            self.assertEqual(mv.paint("hi"), "hi")


class BannerTests(unittest.TestCase):
    def test_banner_has_five_equal_width_rows(self):
        rows = mv.render_banner("VIDEO", "MERGE")
        self.assertEqual(len(rows), mv._BANNER_HEIGHT)
        widths = {len(row) for row in rows}
        self.assertEqual(len(widths), 1)
        self.assertTrue(all("█" in row for row in rows))

    def test_unknown_characters_are_skipped(self):
        # Digits have no glyph; the banner should still render without error.
        self.assertEqual(len(mv.render_banner("V1D")), mv._BANNER_HEIGHT)


class CenterTests(unittest.TestCase):
    def test_centers_within_width(self):
        self.assertEqual(mv._center("abc", 9), "   abc")

    def test_no_negative_padding_when_wider_than_width(self):
        self.assertEqual(mv._center("abcdef", 4), "abcdef")


def _tty(is_tty: bool) -> io.StringIO:
    stream = io.StringIO()
    stream.isatty = lambda: is_tty  # type: ignore[method-assign]
    return stream


if __name__ == "__main__":
    unittest.main()
