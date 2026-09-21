"""Chrome tab tools, against a made-up list of tabs. No Chrome, no osascript."""
import os
import sys
import unittest
from unittest import mock

os.environ["SAMANTHA_HEADLESS"] = "1"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tools_util as u

FAKE = "1.1\tHacker News\thttps://news.ycombinator.com/\n1.2\tturing: a tiny assistant\thttps://github.com/nulljosh/turing\n2.1\tInbox (3)\thttps://mail.google.com/mail/u/0/\n"


class TabTests(unittest.TestCase):
    """Listing, finding, switching, closing and reading, and never touching Chrome while headless."""

    def setUp(self):
        """Every osascript call returns the fake tab list and is recorded."""
        self.calls = []
        self.patch = mock.patch.object(u, "_sh", side_effect=lambda argv, timeout=5: self.calls.append(argv) or FAKE)
        self.patch.start()

    def tearDown(self):
        """Put the real runner back."""
        self.patch.stop()

    def test_list(self):
        """Tabs come back numbered with a short title and the site."""
        self.assertEqual(u.list_tabs().splitlines(), ["1.1 Hacker News (news.ycombinator.com)", "1.2 turing: a tiny assistant (github.com)", "2.1 Inbox (3) (mail.google.com)"])

    def test_find_by_number_and_word(self):
        """A number, a window.tab number, a title word and a site word all find the tab."""
        self.assertEqual(u._find_tab("2")[0][:2], (1, 2))
        self.assertEqual(u._find_tab("2.1")[0][:2], (2, 1))
        self.assertEqual(u._find_tab("github")[0][:2], (1, 2))
        self.assertEqual(u._find_tab("INBOX")[0][:2], (2, 1))
        self.assertEqual(u._find_tab("nothing like this")[1], "No tab matches nothing like this.")
        self.assertEqual(u._find_tab("9")[1], "No tab 9.")

    def test_headless_switch_and_close_only_look(self):
        """While headless, switching and closing name the tab but send no command to Chrome."""
        self.assertEqual(u.switch_tab("github"), "Switched to turing: a tiny assistant.")
        self.assertEqual(u.close_tab("mail"), "Closed Inbox (3).")
        self.assertTrue(all("close tab" not in a[-1] and "active tab index" not in a[-1] for a in self.calls))

    def test_close_needs_a_target(self):
        """Closing with no words closes nothing."""
        self.assertIn("Say which tab", u.close_tab(""))

    def test_real_commands_carry_only_numbers(self):
        """Off headless, the AppleScript is built from tab numbers we parsed, never from the words she was given."""
        with mock.patch.object(u, "HEADLESS", False):
            u.close_tab('mail" & (do shell script "rm -rf ~") & "')  # matches nothing, so nothing runs
            u.close_tab("mail")
        sent = [a[-1] for a in self.calls if "close tab" in a[-1]]
        self.assertEqual(sent, ['tell application "Google Chrome" to close tab 1 of window 2'])

    def test_read_needs_the_javascript_switch(self):
        """When Chrome hands nothing back she says how to turn the setting on."""
        with mock.patch.object(u, "HEADLESS", False), mock.patch.object(u, "_sh", side_effect=lambda argv, timeout=5: (FAKE if "windows" in argv[-1] else "") if argv[0] == "osascript" else "123"):
            self.assertIn("Allow JavaScript from Apple Events", u.read_tab("github"))

    def test_empty_chrome(self):
        """No tabs open reads as a plain sentence."""
        with mock.patch.object(u, "_sh", return_value=""):
            self.assertEqual(u.list_tabs(), "Chrome has no tabs open.")
            self.assertEqual(u.read_tab(), "Chrome has no tabs open.")


if __name__ == "__main__":
    unittest.main()
