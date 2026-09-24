"""tools_code.py: run_code's sandbox. ask_llm is mocked to a fixed script for every case (never a real model
call in CI, same policy as test_llm.py); the sandbox itself runs for real, since that is the thing being
tested: a real subprocess, a real timeout, a real network block, a real output cap.

Run: python3 tests/test_run_code.py
"""
import os
import re
import sys
import tempfile
import unittest
from unittest import mock

os.environ["SAMANTHA_HEADLESS"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tools
import tools_code


def _csv_home(rows="name,price\napple,10\nbanana,20\ncherry,30\n"):
    """A temp folder standing in for home, with a tiny sales.csv on its Desktop. Caller closes the TemporaryDirectory."""
    home = tempfile.TemporaryDirectory()
    desktop = os.path.join(home.name, "Desktop")
    os.makedirs(desktop, exist_ok=True)
    with open(os.path.join(desktop, "sales.csv"), "w") as f:
        f.write(rows)
    return home


class HappyPath(unittest.TestCase):
    """A real request, a real tiny CSV, a real sandboxed run: the script's own printed answer comes back."""

    def test_stats_on_a_real_csv(self):
        """A fixed script from the mocked model runs for real and its own printed answer comes back."""
        script = (
            "```python\n"
            "import csv\n"
            "with open('data.csv') as f:\n"
            "    rows = list(csv.DictReader(f))\n"
            "prices = [float(r['price']) for r in rows]\n"
            "print(f'Average price: {sum(prices) / len(prices):.2f}')\n"
            "```\n(Answered by qwen3:8b on this Mac, not by me.)"
        )
        home = _csv_home()
        try:
            with mock.patch("os.path.expanduser", side_effect=lambda p: p.replace("~", home.name)), \
                    mock.patch("tools_llm.ask_llm", return_value=script) as ask:
                result = tools_code.run_code("stats on sales.csv")
            ask.assert_called_once()
            self.assertIn("price", ask.call_args[0][0])  # the CSV header rode along in the prompt
            self.assertEqual(result, "Average price: 20.00")
        finally:
            home.cleanup()

    def test_chart_request_saves_a_real_png(self):
        """A chart request calls the sandbox's own save_chart() and gets back a real PNG's path."""
        script = "save_chart(['a', 'b'], [1, 2], 'chart.png')\nprint('saved a chart')"
        home = _csv_home()
        try:
            with mock.patch("os.path.expanduser", side_effect=lambda p: p.replace("~", home.name)), \
                    mock.patch("tools_llm.ask_llm", return_value=script):
                result = tools_code.run_code("chart sales.csv")
            self.assertTrue(result.startswith("Saved "))
            path = re.search(r"Saved (.+\.png)\.", result).group(1)
            self.assertTrue(os.path.isfile(path), result)
            with open(path, "rb") as f:
                self.assertEqual(f.read(8), b"\x89PNG\r\n\x1a\n")  # a real PNG signature, not a stub
        finally:
            home.cleanup()

    def test_empty_request(self):
        """Nothing to run is an honest ask, the model never called."""
        with mock.patch("tools_llm.ask_llm", side_effect=AssertionError("called")):
            self.assertIn("Run code on what", tools_code.run_code("  "))

    def test_no_csv_named_never_calls_the_model(self):
        """No CSV in the sentence is an honest ask, the model never called."""
        with mock.patch("tools_llm.ask_llm", side_effect=AssertionError("called")):
            self.assertIn("Name a CSV", tools_code.run_code("stats on nothing"))

    def test_missing_csv_never_calls_the_model(self):
        """A named CSV that does not exist is an honest ask, the model never called."""
        home = tempfile.TemporaryDirectory()
        try:
            with mock.patch("os.path.expanduser", side_effect=lambda p: p.replace("~", home.name)), \
                    mock.patch("tools_llm.ask_llm", side_effect=AssertionError("called")):
                self.assertIn("Name a CSV", tools_code.run_code("stats on sales.csv"))
        finally:
            home.cleanup()


class Timeout(unittest.TestCase):
    """A script that runs long is killed, not left hanging."""

    def test_a_sleeping_script_is_stopped(self):
        """A script that outlasts the timeout is killed, not left running."""
        script = "import time\ntime.sleep(30)\nprint('should never print')"
        home = _csv_home()
        try:
            with mock.patch("os.path.expanduser", side_effect=lambda p: p.replace("~", home.name)), \
                    mock.patch("tools_code.TIMEOUT", 2), \
                    mock.patch("tools_llm.ask_llm", return_value=script):
                result = tools_code.run_code("stats on sales.csv")
            self.assertIn("2 seconds", result)
        finally:
            home.cleanup()


class NetworkBlocked(unittest.TestCase):
    """A script that tries to reach the network fails inside the sandbox, never actually reaching it."""

    def test_urllib_fails_inside_the_sandbox(self):
        """A script that tries urllib fails inside the sandbox; no real connection is ever attempted."""
        script = "import urllib.request\nprint(urllib.request.urlopen('http://example.com', timeout=5).read())"
        home = _csv_home()
        try:
            with mock.patch("os.path.expanduser", side_effect=lambda p: p.replace("~", home.name)), \
                    mock.patch("tools_llm.ask_llm", return_value=script):
                result = tools_code.run_code("stats on sales.csv")
            self.assertIn("network access is blocked", result)
        finally:
            home.cleanup()


class OutputCap(unittest.TestCase):
    """A script that prints far more than 2000 characters never comes back whole."""

    def test_long_output_is_capped(self):
        """Whatever the script prints, what comes back is never more than 2000 characters."""
        script = "print('x' * 5000)"
        home = _csv_home()
        try:
            with mock.patch("os.path.expanduser", side_effect=lambda p: p.replace("~", home.name)), \
                    mock.patch("tools_llm.ask_llm", return_value=script):
                result = tools_code.run_code("stats on sales.csv")
            self.assertLessEqual(len(result), 2000)
            self.assertEqual(len(result), 2000)
        finally:
            home.cleanup()


class OnlyByRoute(unittest.TestCase):
    """The four phrasings from the roadmap, and that it asks first like every other write."""

    def test_routes(self):
        """The four phrasings from the roadmap all reach run_code with the whole sentence as its request."""
        self.assertEqual(tools.plan("stats on sales.csv"), [("run_code", ("stats on sales.csv",))])
        self.assertEqual(tools.plan("average of the price column in sales.csv"),
                          [("run_code", ("average of the price column in sales.csv",))])
        self.assertEqual(tools.plan("chart sales.csv"), [("run_code", ("chart sales.csv",))])
        self.assertEqual(tools.plan("plot column price of sales.csv"), [("run_code", ("plot column price of sales.csv",))])

    def test_is_a_write(self):
        """Running code is a write: it is in tools.WRITES, same as write_document and save_research."""
        self.assertIn("run_code", tools.WRITES)

    def test_a_no_runs_nothing(self):
        """A no from the harness runs no sandbox and calls no model, same as every other write."""
        with mock.patch("tools_llm.ask_llm", side_effect=AssertionError("called")), \
                mock.patch("tools_code.subprocess.run", side_effect=AssertionError("called")):
            reply = tools.do("stats on sales.csv", confirm=lambda n, a: False)
        self.assertEqual(reply, "Okay, I will not.")


if __name__ == "__main__":
    unittest.main()
