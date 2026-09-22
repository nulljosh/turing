"""Edge cases and error handling for the whole chat path: empty, huge, unicode, negative, malformed, half-finished,
offline and missing-command input. Nothing here may raise, and every reply is honest about what happened.

Run: python3 test_edges.py
"""
import os
import sys
import unittest
from unittest import mock

os.environ["SAMANTHA_HEADLESS"] = "1"
os.environ["SAMANTHA_MEMORY"] = "/nonexistent/samantha-memory.json"  # never read or write anyone's real memory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ask
import chat
import harness
import tools

# every kind of input a person (or a cat on the keyboard) can send
WEIRD = ["", " ", "?", "!!!", "\n", "\t\t", "a" * 5000, "open ", "open", "go to", "search", "search for", "google", "remind me", "take a note",
         "set a timer for -5 minutes", "set a timer for 0 seconds", "set a timer for 99999 hours", "set the volume to 999", "volume -3",
         "roll 0d6", "roll 1d1", "roll 999d999", "calculate", "calculate 10**10**10", "calculate 1e308*10", "convert 5 km to", "convert to miles",
         "resize ~/a.png to 0", "rotate ~/a.png by 45", "rotate ~/a.png by 99999999999999999999", "flip", "open 🎉", "search for 🎉 emoji", "whats",
         "what's the weather in ", "time in atlantis", "time in ", "days until yesterday", "is -7 prime", "is 0 prime", "factor 0", "factor -12",
         "roman numerals for 0", "roman numerals for -5", "tip on -10", "tip on " + "9" * 400, "base64 decode ", "morse ", "reverse ", "hash ",
         "read it", "open it", "again", "do that again", "and", "then", "and then", "open youtube and", "and set the volume to 20", "open youtube then",
         "go to http://", "go to https://", "go to ://", "read ~/../../etc/passwd", "read the file /etc/shadow", "list the files in /",
         "say " + "x" * 10000, "remember ", "forget ", "recall ", "switch to tab 999", "close tab -1", "what is 1/0", "what is 0/0",
         "\x00", "open \x00chrome", "search for ‮reversed", "ｏｐｅｎ ｃｈｒｏｍｅ", "OPEN CHROME", "open chrome.", "please please please open chrome",
         "take a note " + "é" * 100, "remind me to ", "google how tall is everest?", "make .png black and white", "convert ~/a.png to exe",
         "open youtube and and and set the volume to 20", ";;;", "then then then", "hi" * 1000, "🤖" * 50, "​​", "what is ﻿2+2"]


def offline():
    """Everything outside Python is gone: no osascript, no say, no network. The worst machine she can wake up on."""
    return [mock.patch.object(tools, "_run", return_value=""),
            mock.patch("subprocess.run", side_effect=FileNotFoundError(2, "No such file", "osascript")),
            mock.patch("subprocess.Popen", side_effect=FileNotFoundError(2, "No such file", "say")),
            mock.patch("urllib.request.urlopen", side_effect=OSError("offline"))]


class NeverCrash(unittest.TestCase):
    """Every weird input gets a reply, on the worst machine, and nothing raises."""

    def test_every_weird_input_gets_a_reply(self):
        """No exception, no traceback text, no empty reply, for any input in WEIRD, through the harness and then the answer chain."""
        patches = offline()
        for p in patches:
            p.start()
        try:
            s = harness.Session(confirm=lambda n, a: True, log=lambda line: None)
            for q in WEIRD:
                with self.subTest(q=q[:40]):
                    reply = s.ask(q, or_none=True)
                    if reply is None and q.strip():
                        reply = chat.safe_turn(q, [], False, None)[0]
                    if q.strip():
                        self.assertTrue(reply and reply.strip(), q[:40])
                        self.assertNotIn("Traceback", reply)
                        self.assertNotIn("Something broke", reply)  # safe_turn's net must not be what caught it
        finally:
            for p in patches:
                p.stop()


class HalfFinished(unittest.TestCase):
    """A command with its object missing asks for it."""

    def test_asks_for_what_is_missing(self):
        """Open what, search for what, remind you of what, and so on."""
        for q, want in (("open", "Open what? Name an app or a site."), ("search for", "Search for what?"), ("google", "Search for what?"),
                        ("remind me to ", "Remind you of what?"), ("take a note", "What should the note say?"),
                        ("set a timer", "For how long?"), ("say", "Say what?"), ("can you open please", "Open what? Name an app or a site.")):
            self.assertEqual(tools.do(q), want, q)

    def test_a_finished_command_is_not_asked_about(self):
        """The ask-back never fires on a real command."""
        for q in ("open chrome", "search for cats", "remind me to call mom", "take a note buy milk", "set a timer for 5 minutes", "say hi"):
            self.assertIsNone(tools.missing(q), q)

    def test_empty_input(self):
        """Nothing typed: the harness asks, the router stays out of it, and nothing is recorded."""
        s = harness.Session()
        self.assertEqual(s.ask("   "), "Say something, or tell me what to do.")
        self.assertIsNone(s.ask("", or_none=True))
        self.assertIsNone(tools.do(""))
        self.assertEqual(s.history, [])


class Typing(unittest.TestCase):
    """What people actually type."""

    def test_dangling_and_then(self):
        """A sentence that trails off with "and" or "then" is the command before it."""
        for q in ("open youtube and", "open youtube then", "open youtube, and then"):
            self.assertEqual(tools.plan(q), [("open_url", ("youtube",))], q)

    def test_full_width_and_invisible_characters(self):
        """Full-width letters are plain letters, and control or direction-override characters never reach a tool."""
        self.assertEqual(tools.plan("ｏｐｅｎ ｙｏｕｔｕｂｅ"), [("open_url", ("youtube",))])
        self.assertEqual(tools.plan("take a note hi‮evil\x00"), [("new_note", ("hievil",))])
        self.assertEqual(tools.plan("​calculate 2+2"), [("calculate", ("2+2",))])

    def test_empty_addresses(self):
        """A scheme with no host is not an address."""
        self.assertIsNone(tools._url("http://"))
        self.assertEqual(tools._url("https://github.com"), "https://github.com")
        with mock.patch.object(tools, "_run", return_value=""):
            self.assertEqual(tools.do("go to https://"), "That address is empty. Give me a site, like github.com.")

    def test_negative_numbers_get_the_tools_own_answer(self):
        """A negative number reaches its tool, which says its range, instead of falling through to an unrelated FAQ entry."""
        self.assertEqual(tools.do("is -7 prime"), "Give me a whole number from 2 to a trillion.")
        self.assertEqual(tools.do("factor -12"), "Give me a whole number from 2 to a trillion.")
        self.assertEqual(tools.do("roman numerals for -5"), "Roman numerals run from 1 to 3999.")
        self.assertEqual(tools.do("tip on -10"), "Give me the bill amount.")
        self.assertEqual(tools.do("tip on " + "9" * 400), "Give me the bill amount.")  # float("9"*400) is inf

    def test_divide_by_zero_is_an_answer(self):
        """1/0 says why it has no answer instead of "I don't know"."""
        self.assertEqual(ask.arithmetic("what is 1/0"), "1/0 has no answer: you can't divide by zero.")
        self.assertEqual(ask.arithmetic("what is 0/0"), "0/0 has no answer: you can't divide by zero.")
        self.assertEqual(ask.arithmetic("what is 6/3"), "6/3 = 2")


if __name__ == "__main__":
    unittest.main()
