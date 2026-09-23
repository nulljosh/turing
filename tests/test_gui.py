"""tools_gui.py: her hands on the screen. The screen reader and cliclick are stood in for, so no test ever clicks.

Run: python3 tests/test_gui.py
"""
import os
import sys
import unittest
from unittest import mock

os.environ["SAMANTHA_HEADLESS"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import harness
import tools
import tools_gui

OCR = "SCREEN\t1920.0\t1080.0\n0.10\t0.20\t0.10\t0.02\tSign in\n0.40\t0.50\t0.20\t0.04\tSign in with Apple\nbad line\n0.5\t0.5\t0.1\t0.1\t  \n"


class Boxes(unittest.TestCase):
    """Reading ocr.swift --boxes and choosing what to click."""

    def test_centers_in_points(self):
        """Fractions of the screen become the center of each line in points; junk lines are skipped."""
        self.assertEqual(tools_gui.parse_boxes(OCR), [("Sign in", 288, 227), ("Sign in with Apple", 960, 562)])
        self.assertEqual(tools_gui.parse_boxes(""), [])
        self.assertEqual(tools_gui.parse_boxes("no header\n0.1\t0.1\t0.1\t0.1\tx"), [])

    def test_exact_before_contains(self):
        """"sign in" is the button, not the longer line that holds it; a missing target is None."""
        boxes = tools_gui.parse_boxes(OCR)
        self.assertEqual(tools_gui.find("Sign In", boxes)[0], "Sign in")
        self.assertEqual(tools_gui.find("apple", boxes)[0], "Sign in with Apple")
        self.assertIsNone(tools_gui.find("Register", boxes))


class Hands(unittest.TestCase):
    """What each tool does, with the screen and cliclick stood in for."""

    def live(self):
        """Pretend this is a real Mac with cliclick: not headless, and every command recorded."""
        self.ran = []
        return [mock.patch.dict(os.environ, {"SAMANTHA_HEADLESS": "0"}), mock.patch("shutil.which", return_value="/bin/cliclick"),
                mock.patch.object(tools_gui, "_run", side_effect=lambda argv, timeout=60: self.ran.append(argv) or "")]

    def test_click_finds_and_clicks_the_center(self):
        """click_text clicks the center of the matching line, and says what it clicked."""
        with mock.patch.object(tools_gui, "screen_boxes", return_value=tools_gui.parse_boxes(OCR)):
            patches = self.live()
            for p in patches:
                p.start()
            try:
                self.assertEqual(tools_gui.click_text('"Sign in"'), "Clicked Sign in.")
                self.assertEqual(tools_gui.click_text("Register"), "I do not see Register on the screen.")
            finally:
                for p in patches:
                    p.stop()
        self.assertEqual(self.ran, [["cliclick", "c:288,227"]])

    def test_type_and_press(self):
        """type_text and press_key send cliclick the right command; unknown keys and huge text are refused."""
        patches = self.live()
        for p in patches:
            p.start()
        try:
            self.assertEqual(tools_gui.type_text("hello world"), "Typed hello world.")
            self.assertEqual(tools_gui.press_key("Escape key"), "Pressed escape.")
            self.assertIn("I can press", tools_gui.press_key("f13"))
            self.assertIn("at most", tools_gui.type_text("x" * 501))
        finally:
            for p in patches:
                p.stop()
        self.assertEqual(self.ran, [["cliclick", "t:hello world"], ["cliclick", "kp:esc"]])

    def test_plain_replies_when_something_is_missing(self):
        """No cliclick, an unreadable screen, empty asks, and headless mode: each a sentence, nothing clicked."""
        with mock.patch.dict(os.environ, {"SAMANTHA_HEADLESS": "0"}), mock.patch("shutil.which", return_value=None):
            self.assertIn("brew install cliclick", tools_gui.click_text("OK"))
            self.assertIn("brew install cliclick", tools_gui.type_text("hi"))
        with mock.patch.dict(os.environ, {"SAMANTHA_HEADLESS": "0"}), mock.patch("shutil.which", return_value="/bin/cliclick"), \
                mock.patch.object(tools_gui, "screen_boxes", return_value=[]):
            self.assertIn("could not read the screen", tools_gui.click_text("OK"))
        self.assertIn("Click what", tools_gui.click_text("  "))
        self.assertEqual(tools_gui.click_text("OK"), "Would click OK.")
        self.assertEqual(tools_gui.press_key("return"), "Would press return.")


class OnlyWithAYes(unittest.TestCase):
    """Every step on the screen is shown and asked first, and routes read the way people say them."""

    def test_asks_before_every_step(self):
        """A no clicks nothing; the step shown is the one that would run."""
        asked = []
        with mock.patch.object(tools_gui, "click_text", side_effect=AssertionError("clicked without a yes")):
            no = harness.Session(confirm=lambda n, a: asked.append((n, a)) or False, log=lambda l: None).ask("click Sign in")
        self.assertEqual((no, asked), ("Okay, I will not.", [("click_text", ("Sign in",))]))
        self.assertLessEqual({"click_text", "type_text", "press_key"}, tools.WRITES)

    def test_routes(self):
        """A named key is a key, anything else pressed or clicked is words on the screen."""
        self.assertEqual(tools.plan("press tab"), [("press_key", ("tab",))])
        self.assertEqual(tools.plan("click the Submit button"), [("click_text", ("Submit",))])
        self.assertEqual(tools.plan("press Continue"), [("click_text", ("Continue",))])
        self.assertEqual(tools.plan("type hello there"), [("type_text", ("hello there",))])
        self.assertEqual(tools.do("click"), 'Click what? Say it like "click Sign in".')


if __name__ == "__main__":
    unittest.main()
