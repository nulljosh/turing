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


class EditFile(unittest.TestCase):
    """Rewriting any text file inside home: found by name, diff shown, only lands on a yes, never outside home."""

    def test_edits_a_named_file_on_a_yes(self):
        """A file on the Desktop, named bare, is found, rewritten and its diff shown."""
        with tempfile.TemporaryDirectory() as tmp:
            home = os.path.realpath(tmp)
            os.makedirs(f"{home}/Desktop")
            path = f"{home}/Desktop/notes.md"
            open(path, "w").write("A long note.\n")
            shown = []
            with mock.patch("os.path.expanduser", side_effect=lambda p: p.replace("~", home)), \
                    mock.patch("tools_llm.ask_llm", return_value="A note.\n(Answered by Qwen on this Mac, not by me.)"):
                result = tools_write.edit_file("notes.md", "make it shorter", log=shown.append, confirm=lambda n, a: n == "edit_file")
            self.assertEqual(result, f"Rewrote {path}.")
            self.assertEqual(open(path).read(), "A note.\n")
            self.assertTrue(any("-A long note." in line for line in shown))

    def test_missing_outside_or_binary_refused(self):
        """No such file, a file outside home, or a binary one: declined, the model never called."""
        with tempfile.TemporaryDirectory() as home, mock.patch("tools_llm.ask_llm", side_effect=AssertionError("called")), \
                mock.patch("os.path.expanduser", side_effect=lambda p: p.replace("~", home)):
            self.assertIn("can't find", tools_write.edit_file("nope.md", "shorter"))
            self.assertIn("can't find", tools_write.edit_file("/etc/hosts", "shorter"))
            open(f"{home}/pic.png", "wb").write(b"\x89PNG\xff\xfe\x00")
            self.assertIn("not a text file", tools_write.edit_file("pic.png", "shorter"))

    def test_routes_end_to_end(self):
        """"edit notes.md: make it shorter" and "in notes.md, fix the typo" both reach edit_file through tools.do."""
        with mock.patch("tools_write.edit_file", return_value="Rewrote x.") as ef:
            self.assertEqual(tools.do("edit notes.md: make it shorter", confirm=lambda n, a: True), "Rewrote x.")
            self.assertEqual(ef.call_args.args[:2], ("notes.md", "make it shorter"))
            tools.do("in ~/Desktop/notes.md, fix the typo", confirm=lambda n, a: True)
            self.assertEqual(ef.call_args.args[:2], ("~/Desktop/notes.md", "fix the typo"))


class WriteCode(unittest.TestCase):
    """New code to disk: the fence stripped, the whole file shown, only lands on a yes."""

    def test_writes_code_on_a_yes_and_not_on_a_no(self):
        """The model's fenced reply lands as bare code on a yes; a no leaves nothing behind."""
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch("os.path.expanduser", side_effect=lambda p: p.replace("~", os.path.realpath(tmp))), \
                mock.patch("tools_llm.ask_llm", return_value="```python\nprint('hi')\n```\n(Answered by Qwen on this Mac, not by me.)"):
            self.assertEqual(tools_write.write_code("print hi", "hi.py", confirm=lambda n, a: False), "Okay, I will not.")
            self.assertFalse(os.path.exists(f"{tmp}/Desktop/hi.py"))
            shown = []
            result = tools_write.write_code("print hi", "hi.py", log=shown.append, confirm=lambda n, a: n == "write_code")
            home = os.path.realpath(tmp)
            self.assertEqual(result, f"Wrote {home}/Desktop/hi.py.")
            self.assertEqual(open(f"{home}/Desktop/hi.py").read(), "print('hi')\n")
            self.assertTrue(any("+print('hi')" in line for line in shown))

    def test_outside_home_refused(self):
        """A path outside home is refused before the model is called."""
        with mock.patch("tools_llm.ask_llm", side_effect=AssertionError("called")):
            self.assertIn("only write inside", tools_write.write_code("print hi", "/tmp/hi.py"))

    def test_routes_end_to_end(self):
        """Both phrasings reach write_code through tools.do, and "write a doc about x" still does not."""
        with mock.patch("tools_write.write_code", return_value="Wrote x.") as wc:
            self.assertEqual(tools.do("write a python script that prints the date to today.py", confirm=lambda n, a: True), "Wrote x.")
            self.assertEqual(wc.call_args.args[:2], ("python script that prints the date", "today.py"))
            tools.do("write hello.sh that echoes hi", confirm=lambda n, a: True)
            self.assertEqual(wc.call_args.args[:2], ("echoes hi", "hello.sh"))
            wc.reset_mock()
            with mock.patch("tools_llm.ask_llm", return_value="A doc."), mock.patch("builtins.open", mock.mock_open()):
                tools.do("write a doc about the roadmap", confirm=lambda n, a: True)
            self.assertFalse(wc.called)


if __name__ == "__main__":
    unittest.main()
