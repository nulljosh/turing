"""Edge cases and error handling for the whole chat path: empty, huge, unicode, negative, malformed, half-finished,
offline and missing-command input. Nothing here may raise, and every reply is honest about what happened.

Run: python3 tests/test_edges.py
"""
import os
import sys
import unittest
from unittest import mock

os.environ["SAMANTHA_HEADLESS"] = "1"
os.environ["SAMANTHA_MEMORY"] = "/nonexistent/samantha-memory.json"  # never read or write anyone's real memory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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
         "open youtube and and and set the volume to 20", ";;;", "then then then", "hi" * 1000, "🤖" * 50, "​​", "what is ﻿2+2",
         "ask claude", "claude,", "ask claude " + "x" * 30000, "claude: \x00", "ask claude why is the sky blue", "ask qwen", "ask llama " + "y" * 30000, "ask phi hi"]


def offline():
    """Everything outside Python is gone: no osascript, no say, no network. The worst machine she can wake up on."""
    return [mock.patch.object(tools, "_run", return_value=""),
            mock.patch("subprocess.run", side_effect=FileNotFoundError(2, "No such file", "osascript")),
            mock.patch("subprocess.Popen", side_effect=FileNotFoundError(2, "No such file", "say")),
            mock.patch("urllib.request.urlopen", side_effect=OSError("offline")),
            mock.patch.object(chat, "_model", side_effect=OSError("offline"))]  # her answer model stays unloaded, as on CI


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

    def test_natural_math_phrases(self):
        """Square root, percent-of, squared/cubed and power all compute; "10 times 7" still never hijacks to a search."""
        self.assertEqual(ask.arithmetic("what is the square root of 81"), "sqrt(81) = 9")
        self.assertEqual(ask.arithmetic("what is 15% of 200"), "((15)/100)*(200) = 30")
        self.assertEqual(ask.arithmetic("what is 4 squared"), "(4)**2 = 16")
        self.assertEqual(ask.arithmetic("what is 2 cubed"), "(2)**3 = 8")
        self.assertEqual(ask.arithmetic("what is 2 to the power of 10"), "(2)**(10) = 1024")
        self.assertEqual(ask.arithmetic("what is 10 times 7"), "10 * 7 = 70")  # the original newspaper-hijack case


class Dates(unittest.TestCase):
    """date_math is exact at the edges: month ends, leap days, year 1 and 9999, bad dates, today moving."""

    def test_fixed_dates(self):
        """Known answers, independent of today."""
        import tools_util as u
        self.assertEqual(u.date_math("weekday july 4 1976"), "July 4, 1976 was a Sunday.")
        self.assertEqual(u.date_math("2 months after 2026-01-31"), "2 months after 2026-01-31 is Tuesday, March 31, 2026.")
        self.assertEqual(u.date_math("1 month after january 31 2024"), "1 month after january 31 2024 is Thursday, February 29, 2024.")
        self.assertEqual(u.date_math("ten years after 2016-02-29"), "Ten years after 2016-02-29 is Saturday, February 28, 2026.")
        self.assertEqual(u.date_math("between 9999-12-31 and 0001-01-01"), "3,652,058 days between December 31, 9999 and January 1, 1.")
        self.assertEqual(u.date_math("weekday 29th february 2024"), "February 29, 2024 was a Thursday.")

    def test_bad_and_out_of_range(self):
        """Impossible dates and years past 9999 are said, never raised."""
        import tools_util as u
        bad = u.date_math("nonsense")
        for q in ("weekday 2023-02-29", "weekday feb 30 2026", "between 2026-01-01 and someday", "3 days ago yesterday", "5 days after nowhere", "", "weekday "):
            self.assertEqual(u.date_math(q), bad, q)
        for q in ("999999 years from now", "1 day before 0001-01-01", "1 day after 9999-12-31"):
            self.assertEqual(u.date_math(q), "That date is out of range: I can do years 1 to 9999.", q)

    def test_relative_to_a_frozen_today(self):
        """"from now", "ago", tomorrow and the tense of a weekday all follow today."""
        import tools_util as u
        from datetime import date as real_date

        class Frozen(real_date):
            """Today is 2026-09-22."""
            @classmethod
            def today(cls):
                """The frozen day."""
                return real_date(2026, 9, 22)

        import util_dates
        with mock.patch.object(util_dates, "date", Frozen):  # date_math lives in util_dates, re-exported by tools_util
            self.assertEqual(u.date_math("100 days from"), "100 days from now is Thursday, December 31, 2026.")
            self.assertEqual(u.date_math("3 weeks ago"), "3 weeks ago is Tuesday, September 1, 2026.")
            self.assertEqual(u.date_math("5 days from tomorrow"), "5 days from tomorrow is Monday, September 28, 2026.")
            self.assertEqual(u.date_math("weekday today"), "September 22, 2026 is a Tuesday.")
            self.assertEqual(u.date_math("weekday christmas"), "December 25, 2026 will be a Friday.")

    def test_routes(self):
        """What people type reaches date_math, and "what day is it" still reaches the clock."""
        self.assertEqual(tools.plan("what is 100 days from now"), [("date_math", ("100 days from",))])
        self.assertEqual(tools.plan("what day of the week was july 4 1976"), [("date_math", ("weekday july 4 1976",))])
        self.assertEqual(tools.plan("how many days between 2026-01-01 and christmas"), [("date_math", ("between 2026-01-01 and christmas",))])
        self.assertEqual(tools.plan("what day is it"), [("current_date", ())])
        self.assertEqual(tools.plan("days until christmas"), [("days_until", ("christmas",))])


class TimeZones(unittest.TestCase):
    """convert_time is exact across daylight time, midnight and bad input."""

    def frozen(self, y, mo, d):
        """util_dates with today fixed to one date, so a conversion has one right answer."""
        import util_dates
        from datetime import datetime as real

        class Fixed(real):
            """now() is noon UTC on the given day, in whatever zone is asked."""
            @classmethod
            def now(cls, tz=None):
                """The frozen moment."""
                from datetime import timezone
                t = real(y, mo, d, 12, 0, tzinfo=timezone.utc)
                return t.astimezone(tz) if tz else t.replace(tzinfo=None)

        return mock.patch.object(util_dates, "datetime", Fixed)

    def test_winter_and_summer(self):
        """3pm Pacific is 8am next day in Tokyo in winter and 7am in summer: daylight time is followed, not ignored."""
        import util_dates
        with self.frozen(2026, 1, 15):
            self.assertEqual(util_dates.convert_time("3pm pst in tokyo"), "3:00 PM PST is 8:00 AM on Friday in Tokyo.")
        with self.frozen(2026, 7, 15):
            self.assertEqual(util_dates.convert_time("3pm pst in tokyo"), "3:00 PM PST is 7:00 AM on Thursday in Tokyo.")
            self.assertEqual(util_dates.convert_time("15:30 london to new york"), "3:30 PM London is 10:30 AM on Wednesday in New York.")

    def test_the_spring_forward_gap_answers(self):
        """2:30am on the night clocks jump does not exist in Pacific time; it still gets an answer, never a crash."""
        import util_dates
        with self.frozen(2026, 3, 8):
            self.assertTrue(util_dates.convert_time("2:30am pst in utc").startswith("2:30 AM PST is "))

    def test_bad_times_and_zones(self):
        """Impossible times and unknown zones are said plainly."""
        import util_dates
        self.assertEqual(util_dates.convert_time("13pm pst in tokyo"), "13pm is not a time I can read. Try 3pm, 3:30 pm or 15:30.")
        self.assertEqual(util_dates.convert_time("9:75 pst in tokyo"), "9:75 is not a time I can read. Try 3pm, 3:30 pm or 15:30.")
        self.assertEqual(util_dates.convert_time("3pm pst in narnia"), "I do not know the time zone for narnia.")
        self.assertEqual(util_dates.convert_time("3pm atlantis to tokyo"), "I do not know the time zone for atlantis.")
        self.assertEqual(util_dates.convert_time("tokyo"), 'Say it like "3pm PST in Tokyo" or "15:30 London to New York".')
        self.assertEqual(util_dates.convert_time("3pm pst in Not/AZone"), "I do not know the time zone for Not/AZone.")

    def test_routes_leave_units_alone(self):
        """A bare number is a unit, not a clock: convert 5 km to miles stays a unit conversion."""
        self.assertEqual(tools.plan("convert 5 km to miles"), [("convert_units", ("5 km to miles",))])
        self.assertEqual(tools.plan("convert 3pm pst to tokyo"), [("convert_time", ("3pm pst to tokyo",))])
        self.assertEqual(tools.plan("what time is it in tokyo"), [("time_in", ("tokyo",))])


class Logo(unittest.TestCase):
    """Her icon is hers: the committed files are exactly what her designer draws, and every layer type renders."""

    def test_the_icon_is_rebuilt_from_her_designer(self):
        """web/icon.svg and icon.svg are byte for byte tools_logo.icon_svg(): nobody hand-edits her logo."""
        import tools_logo
        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for path in ("web/icon.svg", "icon.svg"):
            with open(os.path.join(here, path)) as f:
                self.assertEqual(f.read(), tools_logo.icon_svg(), path)

    def test_the_blueprint_matches_the_icon(self):
        """docs/icon-blueprint.svg is generated from the icon's own layers, and the icon keeps the measured proportions."""
        import tools_logo
        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(here, "docs", "icon-blueprint.svg")) as f:
            self.assertEqual(f.read(), tools_logo.icon_blueprint_svg())
        m = tools_logo.icon_measures()
        self.assertTrue(0.70 <= m["fill"] <= 0.80, m["fill"])  # the mark keeps a real margin inside the tile
        self.assertGreaterEqual(m["gap"] / 1024 * 16, 0.95)  # the dark ring is still a whole pixel at 16 px
        self.assertGreaterEqual(m["contrast"]["core on tile"], 7)
        self.assertGreaterEqual(m["contrast"]["accent on tile"], 7)

    def test_flower_reads_small(self):
        """The flower: accent petals only, none inside the dark ring, one ink core drawn last, never text."""
        import math
        import tools_logo
        tile, ink, accent = tools_logo.PALETTES["ember"]
        layers = tools_logo._bloom_layers(*tools_logo.ICON)
        petals, core = layers[1:-1], layers[-1]
        self.assertEqual((core["name"], core["fill"]), ("Core", ink))
        self.assertTrue(petals and all(p["fill"] == accent for p in petals))
        self.assertTrue(all(math.hypot(p["cx"] - 512, p["cy"] - 512) > 0.4 * 335 for p in petals))
        self.assertFalse(any(l["type"] == "text" for l in layers))
        self.assertIn("flower", tools_logo._BLOOM_SCHEMA["properties"]["style"]["enum"])

    def test_every_layer_type_renders(self):
        """Tiles, ellipses (filled and stroked), rotated squares and stars all become SVG, and an unknown layer is refused."""
        import tools_logo
        for layers in (tools_logo._logo_layers("ember", "ring"), tools_logo._logo_layers("ink", "spark"),
                       tools_logo._complex_layers("forest", 3, 24, "stars", 8, 8), tools_logo._bloom_layers("paper", 55, "square", 2)):
            svg = tools_logo.layers_to_svg(layers)
            self.assertTrue(svg.startswith("<svg") and svg.rstrip().endswith("</svg>"))
            self.assertEqual(svg.count("\n  <"), len(layers))
        self.assertIn('stroke="#e8a96a"', tools_logo.layers_to_svg(tools_logo._logo_layers("ember", "ring")))
        self.assertIn("<polygon", tools_logo.layers_to_svg(tools_logo._logo_layers("ember", "spark")))
        self.assertIn("rotate(", tools_logo.layers_to_svg(tools_logo._bloom_layers("ember", 21, "square", 1)))
        self.assertIn("<!-- a -note -->", tools_logo.layers_to_svg([], "a --note"))  # a comment can never close early
        with self.assertRaises(ValueError):
            tools_logo.layers_to_svg([{"type": "text", "text": "TURING"}])


if __name__ == "__main__":
    unittest.main()
