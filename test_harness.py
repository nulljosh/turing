"""The harness: it shows the tool log, asks before writes, remembers, and never lets a no through."""
import os
import sys
import unittest
from unittest import mock

os.environ["SAMANTHA_HEADLESS"] = "1"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harness
import tools


class HarnessTests(unittest.TestCase):
    """Uses a mocked _run so no note is ever really made."""

    def session(self, answer):
        """A session whose confirm answers as told, plus the lists of what was asked and shown."""
        asked, shown = [], []
        s = harness.Session(confirm=lambda n, a: asked.append((n, a)) or answer, log=shown.append)
        return s, asked, shown

    def test_a_no_stops_the_write(self):
        """A no stops the write."""
        s, asked, shown = self.session(False)
        with mock.patch.object(tools, "_app") as run:
            self.assertEqual(s.ask("take a note buy milk"), "Okay, I will not.")
        run.assert_not_called()
        self.assertEqual(asked, [("new_note", ("buy milk",))])
        self.assertEqual(shown, ["  [new_note(buy milk)]"])

    def test_a_yes_runs_it_once(self):
        """A yes runs it once."""
        s, asked, _ = self.session(True)
        with mock.patch.object(tools, "_app") as run:
            self.assertEqual(s.ask("take a note buy milk"), "Noted: buy milk")
        self.assertEqual(run.call_count, 1)
        self.assertEqual(len(asked), 1)

    def test_reads_never_ask(self):
        """Reads never ask."""
        s, asked, shown = self.session(False)
        self.assertEqual(s.ask("calculate 17*23"), "391")
        self.assertEqual(asked, [])
        self.assertEqual(shown, ["  [calculate(17*23)]"])

    def test_it_remembers_what_it_did(self):
        """It remembers what it did."""
        s, _, _ = self.session(False)
        s.ask("calculate 2+2")
        s.ask("roman numerals for 2026")
        self.assertEqual(s.recall(), "calculate 2+2: [calculate(2+2)]\nroman numerals for 2026: [roman_numeral(2026)]")
        self.assertEqual(s.ask("what did you just do"), s.recall())

    def test_a_broken_tool_is_a_reply_not_a_crash(self):
        """A tool whose command is missing or hangs says so, the chat keeps going, and the turn is recorded."""
        import subprocess
        s, _, _ = self.session(True)
        with mock.patch("subprocess.run", side_effect=FileNotFoundError(2, "No such file", "osascript")):
            reply = s.ask("set the volume to 30")
        self.assertEqual(reply, "I tried set_volume(30), but it did not work: osascript is not on this machine.")
        with mock.patch("subprocess.run", side_effect=subprocess.TimeoutExpired("osascript", 10)):
            self.assertIn("longer than 10 seconds", s.ask("set the volume to 40"))
        self.assertEqual(s.ask("calculate 2+2"), "4")
        self.assertEqual(len(s.history), 3)

    def test_plan_runs_nothing(self):
        """Plan runs nothing."""
        with mock.patch.object(tools, "_run", return_value="") as run:
            self.assertEqual(tools.plan("set the volume to 30"), [("set_volume", ("30",))])
            self.assertEqual(tools.plan("what is turing"), [])
        run.assert_not_called()
        self.assertTrue(callable(tools.set_volume) and tools.set_volume.__name__ == "set_volume")  # swapped back

    def test_a_question_is_handed_back_for_the_chat(self):
        """With or_none a sentence that is not a command comes back as None and is not recorded, so chat.py can answer it."""
        s, _, _ = self.session(False)
        with mock.patch.object(tools, "pick", return_value=None):
            self.assertIsNone(s.ask("what is the capital of france", or_none=True))
            self.assertEqual(s.history, [])
            self.assertEqual(s.ask("calculate 2+2", or_none=True), "4")

    def test_every_write_is_a_real_tool(self):
        """Every write is a real tool."""
        self.assertLessEqual(tools.WRITES, set(tools.TOOLS))


if __name__ == "__main__":
    unittest.main()
