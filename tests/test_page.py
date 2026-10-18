"""tools_page.py: check_page, with subprocess mocked so Chrome and ImageMagick are never run.

Covers the routes, the home-only and no-hidden-files fence, the log parser (errors once each, network misses named),
the verdicts for black, blown-out, flat, dark and fine pictures, the Chrome flags that keep the run offline, and a
missing Chrome or a timeout getting a plain reply. A throwaway home folder stands in for ~.

Run: python3 tests/test_page.py
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

os.environ["SAMANTHA_HEADLESS"] = "1"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app"))
import tools_files  # noqa: E402
import tools_page  # noqa: E402

BOOM = '[1:2:3:INFO:CONSOLE:26] "Uncaught Error: boom", source: file:///a.html (26)\n'


class Base(unittest.TestCase):
    """Each test gets a throwaway home folder with one page, one hidden page and one text file."""

    def setUp(self):
        """Point tools_files at a temp home and make the files."""
        self.home = tempfile.mkdtemp()
        self.real_home = tools_files.HOME
        tools_files.HOME = os.path.realpath(self.home)
        self.page = os.path.join(tools_files.HOME, "room.html")
        with open(self.page, "w") as f:
            f.write("<html></html>")
        os.makedirs(os.path.join(tools_files.HOME, ".hidden"))
        open(os.path.join(tools_files.HOME, ".hidden", "secret.html"), "w").close()
        open(os.path.join(tools_files.HOME, "notes.txt"), "w").close()

    def tearDown(self):
        """Restore the real home and delete the temp one."""
        tools_files.HOME = self.real_home
        shutil.rmtree(self.home, ignore_errors=True)


class Routes(unittest.TestCase):
    """The exact phrases hand the tool its path."""

    def route(self, text):
        """(tool, argument) for the first ROUTES pattern that matches, or (None, None)."""
        for pat, name, arg in tools_page.ROUTES:
            m = pat.match(text)
            if m:
                return name, arg(m)
        return None, None

    def test_each_phrase(self):
        """check and why-is phrasings route; plain talk does not."""
        self.assertEqual(self.route("check ~/Sites/index.html"), ("check_page", "~/Sites/index.html"))
        self.assertEqual(self.route("debug my page ~/a.htm"), ("check_page", "~/a.htm"))
        self.assertEqual(self.route("why is ~/room.html black"), ("check_page", "~/room.html"))
        self.assertEqual(self.route("why is the sky black"), (None, None))
        self.assertEqual(self.route("check my email"), (None, None))


class Fence(Base):
    """Only a page inside home, not hidden, ending in .html or .htm."""

    def test_refusals_run_nothing(self):
        """Outside home, hidden, wrong type and missing all get one sentence and no Chrome."""
        with mock.patch.object(tools_page.subprocess, "run") as run:
            for bad in ("/etc/a.html", "~/.hidden/secret.html", "~/notes.txt", "~/nope.html", "~/../../etc/x.html"):
                self.assertIn("allowed", tools_page.check_page(bad))
            run.assert_not_called()

    def test_no_chrome(self):
        """A Mac without Chrome is told so."""
        with mock.patch.object(tools_page, "_chrome", return_value=None):
            self.assertIn("Chrome is not installed", tools_page.check_page(self.page))


class Log(unittest.TestCase):
    """The errors read out of Chrome's stderr."""

    def test_errors_once_each_and_noise_ignored(self):
        """A repeated error shows once; a performance note is not an error."""
        noise = '[1:2:3:INFO:CONSOLE:9] "GL Driver Message (OpenGL, Performance): GPU stall due to ReadPixels", source: file:///a.html (9)\n'
        self.assertEqual(tools_page._errors(BOOM + BOOM + noise), ["Uncaught Error: boom (line 26)"])

    def test_a_blocked_network_is_named(self):
        """A page that needs a CDN script says which address."""
        log = "net::ERR_NAME_NOT_RESOLVED while fetching https://cdn.example.com/three.js\n"
        self.assertTrue(any("cdn.example.com/three.js" in e for e in tools_page._errors(log)))


class Verdict(unittest.TestCase):
    """What she says about the picture and the errors."""

    def test_each_picture(self):
        """Black, blown out, flat, dark and fine each get their own words."""
        self.assertIn("black", tools_page._verdict([], (0.9, 0.0, 3, 5)))
        self.assertIn("blown-out", tools_page._verdict([], (0.0, 0.5, 200, 30)))
        self.assertIn("flat colour", tools_page._verdict([], (0.1, 0.0, 120, 2)))
        self.assertIn("very dark", tools_page._verdict([], (0.1, 0.0, 25, 20)))
        self.assertIn("loads without errors", tools_page._verdict([], (0.0, 0.0, 120, 40)))

    def test_errors_come_first_and_only_three(self):
        """Four errors: three are named, and a fine picture does not cancel them."""
        got = tools_page._verdict(["a (line 1)", "b (line 2)", "c (line 3)", "d (line 4)"], (0.0, 0.0, 120, 40))
        self.assertIn("4 errors", got)
        self.assertNotIn("d (line 4)", got)
        self.assertNotIn("loads without errors", got)


class Run(Base):
    """check_page end to end with Chrome and the picture check faked."""

    def fake_chrome(self, stderr, shot=True):
        """A subprocess.run stand-in that writes the screenshot Chrome would and returns its log."""
        def run(cmd, **kw):
            """Write the png Chrome was asked for, and hand back the canned stderr."""
            if shot:
                open(next(a for a in cmd if a.startswith("--screenshot=")).split("=", 1)[1], "wb").write(b"png")
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr=stderr)
        return run

    def test_reports_errors_and_a_dark_picture(self):
        """The answer names the file, the error with its line, and the dark picture; Chrome ran offline with a temp profile."""
        with mock.patch.object(tools_page, "_chrome", return_value="/chrome"), mock.patch.object(tools_page, "_look", return_value=(0.1, 0.0, 25, 20)), \
                mock.patch.object(tools_page.subprocess, "run", side_effect=self.fake_chrome(BOOM)) as run:
            got = tools_page.check_page(self.page)
        self.assertTrue(got.startswith("room.html: It threw an error: Uncaught Error: boom (line 26)."))
        self.assertIn("very dark", got)
        cmd = run.call_args[0][0]
        self.assertIn("--host-resolver-rules=MAP * ~NOTFOUND , EXCLUDE localhost", cmd)
        self.assertTrue(any(a.startswith("--user-data-dir=") for a in cmd))
        self.assertEqual(cmd[-1], "file://" + self.page)

    def test_no_screenshot_still_answers(self):
        """If Chrome leaves no picture the errors still come back and she says she could not look."""
        with mock.patch.object(tools_page, "_chrome", return_value="/chrome"), mock.patch.object(tools_page.subprocess, "run", side_effect=self.fake_chrome(BOOM, shot=False)):
            self.assertIn("could not look at the picture", tools_page.check_page(self.page))

    def test_timeout_is_a_sentence(self):
        """Chrome hanging is a reply, not a crash."""
        with mock.patch.object(tools_page, "_chrome", return_value="/chrome"), mock.patch.object(tools_page.subprocess, "run", side_effect=subprocess.TimeoutExpired("c", 60)):
            self.assertIn("did not answer", tools_page.check_page(self.page))


if __name__ == "__main__":
    unittest.main()
