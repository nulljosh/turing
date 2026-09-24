"""tools_write.py: drafting and saving a real file. The writer model and the home folder are stood in for.

Run: python3 tests/test_write.py
"""
import os
import sys
import tempfile
import unittest
from unittest import mock

os.environ["SAMANTHA_HEADLESS"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tools
import tools_write


class WriteDocument(unittest.TestCase):
    """What gets drafted and where it lands."""

    def test_drafts_and_saves_inside_home(self):
        """A real request drafts content with the local model and saves it under a slugged name on the Desktop."""
        with tempfile.TemporaryDirectory() as home:
            with mock.patch("os.path.expanduser", side_effect=lambda p: p.replace("~", home)), \
                    mock.patch("tools_llm.ask_llm", return_value="Dear team, the v3.1 release is out.\n(Answered by Qwen on this Mac, not by me.)"):
                result = tools_write.write_document("an email about the v3.1 release")
            path = os.path.realpath(os.path.join(home, "Desktop", "an-email-about-the-v3-1-release.md"))
            self.assertEqual(result, f"Wrote {path}.")
            self.assertEqual(open(path).read(), "Dear team, the v3.1 release is out.\n")

    def test_empty_request(self):
        """Nothing to draft is an honest ask, the model never called."""
        with mock.patch("tools_llm.ask_llm", side_effect=AssertionError("called")):
            self.assertIn("Write what", tools_write.write_document("  "))

    def test_a_blank_or_failed_draft_is_not_saved(self):
        """The local model saying nothing, or saying it could not answer, writes no file."""
        with tempfile.TemporaryDirectory() as home:
            with mock.patch("os.path.expanduser", side_effect=lambda p: p.replace("~", home)):
                with mock.patch("tools_llm.ask_llm", return_value="   "):
                    self.assertIn("could not draft", tools_write.write_document("a doc about x"))
                with mock.patch("tools_llm.ask_llm", return_value="I could not reach a local model."):
                    self.assertIn("could not draft", tools_write.write_document("a doc about x"))
            self.assertEqual(os.listdir(home) if os.path.exists(home) else [], [])


class EditLastDraft(unittest.TestCase):
    """Rewriting the file write_document last saved: diff shown, only lands on a yes."""

    def setUp(self):
        """No draft remembered until a test writes one."""
        tools_write._last_draft["path"] = None

    def _write(self, home, text="Dear team, the release is out.\n(Answered by Qwen on this Mac, not by me.)"):
        """write_document once, inside a fake home, and return the path it saved."""
        with mock.patch("os.path.expanduser", side_effect=lambda p: p.replace("~", home)), \
                mock.patch("tools_llm.ask_llm", return_value=text):
            tools_write.write_document("an email about the release")
        return tools_write._last_draft["path"]

    def test_no_draft_yet_declines_plainly(self):
        """Nothing written yet: says so, never calls the model."""
        with mock.patch("tools_llm.ask_llm", side_effect=AssertionError("called")):
            self.assertIn("no draft yet", tools_write.edit_last_draft("make it shorter"))

    def test_shows_a_diff_and_yes_writes_the_rewrite(self):
        """A yes through confirm writes the rewritten text; the diff is shown before it is asked."""
        with tempfile.TemporaryDirectory() as home:
            path = self._write(home)
            shown = []
            with mock.patch("tools_llm.ask_llm", return_value="Dear team, it's out.\n(Answered by Qwen on this Mac, not by me.)"):
                result = tools_write.edit_last_draft("make it shorter", log=shown.append, confirm=lambda n, a: True)
            self.assertEqual(result, f"Rewrote {path}.")
            self.assertEqual(open(path).read(), "Dear team, it's out.\n")
            self.assertTrue(any("-Dear team, the release is out." in line for line in shown))
            self.assertTrue(any("+Dear team, it's out." in line for line in shown))

    def test_no_leaves_the_file_untouched(self):
        """Saying no through confirm changes nothing on disk."""
        with tempfile.TemporaryDirectory() as home:
            path = self._write(home)
            before = open(path).read()
            with mock.patch("tools_llm.ask_llm", return_value="Dear team, it's out.\n(Answered by Qwen on this Mac, not by me.)"):
                result = tools_write.edit_last_draft("make it shorter", confirm=lambda n, a: False)
            self.assertEqual(result, "Okay, I will not.")
            self.assertEqual(open(path).read(), before)

    def test_empty_instruction(self):
        """No instruction is an honest ask, the model never called."""
        with tempfile.TemporaryDirectory() as home:
            self._write(home)
            with mock.patch("tools_llm.ask_llm", side_effect=AssertionError("called")):
                self.assertIn("Edit it how", tools_write.edit_last_draft("  "))

    def test_routes_through_tools_do(self):
        """The phrasings from the roadmap item reach edit_last_draft end to end, yes and no."""
        with tempfile.TemporaryDirectory() as home:
            path = self._write(home)
            with mock.patch("tools_llm.ask_llm", return_value="Dear team, hi there.\n(Answered by Qwen on this Mac, not by me.)"):
                self.assertEqual(tools.do("make it friendlier", confirm=lambda n, a: True), f"Rewrote {path}.")
            self.assertEqual(open(path).read(), "Dear team, hi there.\n")
            with mock.patch("tools_llm.ask_llm", return_value="Dear team, hi there, and Friday works.\n(Answered by Qwen on this Mac, not by me.)"):
                self.assertEqual(tools.do("add a line about Friday", confirm=lambda n, a: False), "Okay, I will not.")
            self.assertEqual(open(path).read(), "Dear team, hi there.\n")


class OnlyByName(unittest.TestCase):
    """Only "doc", "email" and "file" reach the drafting tool; "note" stays with new_note."""

    def test_routes(self):
        """The ways people ask for a drafted file, and the one word that stays clear of it."""
        self.assertEqual(tools.plan("draft an email about the v3.1 release"), [("write_document", ("the v3.1 release",))])
        self.assertEqual(tools.plan("write a doc about the roadmap"), [("write_document", ("the roadmap",))])
        self.assertEqual(tools.plan("write a note about the meeting"), [("new_note", ("about the meeting",))])

    def test_is_a_write(self):
        """Asking first is not optional: it is in WRITES, same as new_note and save_research."""
        self.assertIn("write_document", tools.WRITES)


if __name__ == "__main__":
    unittest.main()
