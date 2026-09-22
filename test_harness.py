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

    def test_photoshop_means_the_photo_editor_this_mac_has(self):
        """"open photoshop" opens Pixelmator when there is no Photoshop, and Photoshop when there is."""
        with mock.patch.object(tools, "installed_apps", return_value={"pixelmator pro": "Pixelmator Pro"}):
            self.assertEqual(tools._app_match("photoshop"), "Pixelmator Pro")
        with mock.patch.object(tools, "installed_apps", return_value={"adobe photoshop 2026": "Adobe Photoshop 2026", "pixelmator pro": "Pixelmator Pro"}):
            self.assertEqual(tools._app_match("adobe photoshop"), "Adobe Photoshop 2026")

    def test_a_photo_edit_asks_first(self):
        """An exact photo command is a write: it is shown and asked about before Pixelmator is touched."""
        s, asked, shown = self.session(False)
        with mock.patch.object(tools, "grayscale_image") as edit:
            self.assertEqual(s.ask("make ~/Desktop/cat.png black and white"), "Okay, I will not.")
        edit.assert_not_called()
        self.assertEqual(asked, [("grayscale_image", ("~/Desktop/cat.png",))])

    def test_again_repeats_the_last_command_and_still_asks(self):
        """"do that again" runs the last command once more, and a write asks again."""
        s, asked, _ = self.session(False)
        self.assertEqual(s.ask("again"), "Nothing to do again yet.")
        self.assertEqual(s.ask("calculate 6*7"), "42")
        self.assertEqual(s.ask("do that again"), "42")
        s.ask("take a note buy milk")
        self.assertEqual(s.ask("one more time"), "Okay, I will not.")
        self.assertEqual(len(asked), 2)

    def test_plain_commands_chain_without_a_model(self):
        """Two commands in one sentence both run, in order, each shown, and a write in the chain still asks."""
        s, asked, shown = self.session(False)
        with mock.patch.object(tools, "_run", return_value=""):
            self.assertEqual(s.ask("open youtube and set the volume to 20"), "Opened https://youtube.com in Chrome.\nVolume at 20.")
            self.assertEqual(shown, ["  [open_url(youtube)]", "  [set_volume(20)]"])
            reply = s.ask("calculate 6*7, then take a note buy milk")
        self.assertEqual(reply, "42\nSkipped new_note.")
        self.assertEqual(asked, [("new_note", ("buy milk",))])

    def test_an_and_inside_one_command_is_not_a_chain(self):
        """A route for the whole sentence wins, and a later step only a catch-all takes is words, not a command."""
        for command in ("open chrome and go to github.com", "make a logo for salt and pepper", "remind me to call mom and open the garage", "search for cats and dogs", "rock and roll"):
            self.assertIsNone(tools.chain(command), command)

    def test_a_searched_question_is_answered_with_its_source(self):
        """"google how tall is everest" opens the search and answers it; a non-question only opens the tab; a lookup that fails never fails the search."""
        import ask
        s, _, _ = self.session(False)
        with mock.patch.object(tools, "_run", return_value=""), \
             mock.patch.object(ask, "general_knowledge", return_value=("Everest is 8,849 m tall.", "Wikipedia")) as gk:
            self.assertEqual(s.ask("google how tall is everest"),
                             "Everest is 8,849 m tall. (Source: Wikipedia.)\nSearching for 'how tall is everest' in Chrome.")
            gk.assert_called_once_with("how tall is everest", hands=False)
            self.assertEqual(s.ask("google best pizza in vancouver"), "Searching for 'best pizza in vancouver' in Chrome.")
        with mock.patch.object(tools, "_run", return_value=""), mock.patch.object(ask, "general_knowledge", side_effect=OSError("offline")):
            self.assertEqual(s.ask("search for who painted the mona lisa"), "Searching for 'who painted the mona lisa' in Chrome.")
        with mock.patch.object(tools, "_run", return_value=""), mock.patch.object(ask, "general_knowledge", return_value=(None, ask.UNREACHABLE)):
            self.assertEqual(s.ask("google how tall is everest"), "Searching for 'how tall is everest' in Chrome.")

    def test_it_and_that_point_at_the_last_page(self):
        """"read it" reads the page she last opened, "open it" after a search opens that search, and with nothing opened they are not guessed."""
        s, _, shown = self.session(False)
        self.assertEqual(s.point_back("read it"), None)
        with mock.patch.object(tools, "_run", return_value=""), mock.patch.object(tools, "read_page", return_value="Hello page") as read:
            s.ask("go to github.com/nulljosh/turing")
            self.assertEqual(s.ask("read it"), "Hello page")
            read.assert_called_once_with("https://github.com/nulljosh/turing")
            self.assertEqual(s.ask("what does that page say"), "Hello page")
            s.ask("search for mlx lora")
            self.assertEqual(s.ask("open it again"), "Opened https://duckduckgo.com/?q=mlx+lora in Chrome.")
        self.assertIn("  [read_page(https://github.com/nulljosh/turing)]", shown)

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
