"""read_screen against a made-up OCR result. No screenshot is taken and Vision is not run."""
import os
import sys
import unittest
from unittest import mock

os.environ["SAMANTHA_HEADLESS"] = "1"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tools
import tools_util as u

OCR = "Inbox (3)\nMeeting with Sam at noon\nBuy milk\n"


class ScreenTests(unittest.TestCase):
    """Reading, filtering, failing quietly, and staying private."""

    def run_it(self, query="", ocr=OCR):
        """Run read_screen off headless with fake screenshot and OCR commands, returning the reply and the commands sent."""
        sent = []

        def fake(argv, timeout=5):
            """Record the command; the screenshot command writes nothing, the swift one returns the fake text."""
            sent.append(argv[0])
            return ocr if argv[0] == "swift" else ""

        with mock.patch.object(u, "HEADLESS", False), mock.patch.object(u, "_sh", side_effect=fake):
            return u.read_screen(query), sent

    def test_headless_never_captures(self):
        """A test run must not photograph anyone's screen."""
        self.assertEqual(u.read_screen(), "Would read the screen.")

    def test_reads_everything_with_no_query(self):
        """No query returns every line, joined."""
        text, sent = self.run_it()
        self.assertEqual(text, "Inbox (3) | Meeting with Sam at noon | Buy milk")
        self.assertEqual(sent, ["screencapture", "swift"])

    def test_a_query_keeps_only_matching_lines(self):
        """Asking for a word returns the lines that have it, and says so when none do."""
        self.assertEqual(self.run_it("meeting")[0], "Meeting with Sam at noon")
        self.assertEqual(self.run_it("zebra")[0], "I do not see zebra on the screen.")

    def test_no_text_explains_the_permission(self):
        """An empty OCR result points at Screen Recording."""
        self.assertIn("Screen Recording", self.run_it(ocr="")[0])

    def test_the_screenshot_file_is_removed(self):
        """The temporary picture never outlives the call."""
        made = []
        real = u.os.unlink
        with mock.patch.object(u.os, "unlink", side_effect=lambda p: (made.append(p), real(p))[1]):
            self.run_it()
        self.assertEqual(len(made), 1)
        self.assertFalse(os.path.exists(made[0]))

    def test_it_is_private(self):
        """It asks first and never reaches a model or MCP."""
        self.assertIn("read_screen", tools.WRITES)
        self.assertIn("read_screen", tools.NOT_FOR_MODELS)
        self.assertNotIn("read_screen", tools.model_tools())


if __name__ == "__main__":
    unittest.main()
