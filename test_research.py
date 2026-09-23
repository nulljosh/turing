"""tools_research.py: research briefs. Wikipedia, the library, the notes and the writer are stood in for.

Run: python3 test_research.py
"""
import os
import sys
import tempfile
import unittest
from unittest import mock

os.environ["SAMANTHA_HEADLESS"] = "1"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tools
import tools_research

SOURCES = [("Wikipedia: Printing press", "Johannes Gutenberg built the printing press around 1440 in Mainz."),
           ("Wikipedia: History of printing", "Movable type spread across Europe within decades.")]


class Check(unittest.TestCase):
    """Only cited sentences whose numbers are in the sources survive."""

    def test_keeps_cited_grounded_sentences(self):
        """Uncited sentences, citations to sources that do not exist, and invented numbers are dropped."""
        brief = ("Gutenberg built the press around 1440 [1]. It spread across Europe [2]. It changed everything. "
                 "Some say 1390 instead [1]. A third source agrees [3].")
        self.assertEqual(tools_research.check(brief, [t for _, t in SOURCES]),
                         "Gutenberg built the press around 1440 [1]. It spread across Europe [2].")


class Research(unittest.TestCase):
    """The whole brief, with every source and the writer stood in for."""

    def run_it(self, found, written):
        """Research with fixed sources and a fixed writer reply."""
        with mock.patch.object(tools_research, "sources", return_value=found), \
                mock.patch("tools_llm.ask_llm", return_value=written) as ask:
            return tools_research.research("the printing press?"), ask

    def test_a_cited_brief_lists_only_the_sources_it_used(self):
        """The brief comes back with the sources it cited, the writer's own attribution line removed."""
        reply, ask = self.run_it(SOURCES, "Gutenberg built it around 1440 [1].\n(Answered by Qwen on this Mac, not by me.)")
        self.assertEqual(reply, "Gutenberg built it around 1440 [1].\n\nSources:\n[1] Wikipedia: Printing press")
        self.assertIn("[2] Wikipedia: History of printing", ask.call_args[0][0])  # every source reached the writer

    def test_nothing_it_can_stand_behind(self):
        """An uncited or invented brief, no sources, or an empty topic: each an honest sentence."""
        self.assertIn("could not write a brief I can stand behind", self.run_it(SOURCES, "It was 1390.")[0])
        self.assertIn("could not find sources", self.run_it([], "x")[0])
        self.assertIn("Research what", tools_research.research("  "))

    def test_routes(self):
        """The ways people ask for research."""
        self.assertEqual(tools.plan("research the silk road"), [("research", ("the silk road",))])
        self.assertEqual(tools.plan("deep dive into kinship"), [("research", ("kinship",))])


class SaveResearch(unittest.TestCase):
    """Saving the last brief to a file: only inside home, only after a real brief exists."""

    def setUp(self):
        """Start clean: no brief remembered from another test."""
        self.saved = dict(tools_research._last)
        tools_research._last["topic"] = tools_research._last["brief"] = None

    def tearDown(self):
        """Put any prior state back."""
        tools_research._last.update(self.saved)

    def test_nothing_to_save_yet(self):
        """Saving before ever researching is an honest sentence, no file written."""
        self.assertIn("have not researched anything", tools_research.save_research())

    def test_saves_to_a_default_path_from_the_topic(self):
        """No path given: a markdown file named after the topic lands on the Desktop."""
        tools_research._last["topic"], tools_research._last["brief"] = "the silk road", "It connected Asia and Europe [1]."
        with tempfile.TemporaryDirectory() as home:
            with mock.patch("os.path.expanduser", side_effect=lambda p: p.replace("~", home)):
                result = tools_research.save_research()
            path = os.path.realpath(os.path.join(home, "Desktop", "research-the-silk-road.md"))
            self.assertEqual(result, f"Saved to {path}.")
            self.assertIn("It connected Asia and Europe [1].", open(path).read())

    def test_saves_to_a_named_path(self):
        """A named path is honored, and .md is added if missing."""
        tools_research._last["topic"], tools_research._last["brief"] = "kinship", "A social bond [1]."
        with tempfile.TemporaryDirectory() as home:
            with mock.patch("os.path.expanduser", side_effect=lambda p: p.replace("~", home)):
                result = tools_research.save_research("~/Documents/kinship-notes")
            path = os.path.realpath(os.path.join(home, "Documents", "kinship-notes.md"))
            self.assertEqual(result, f"Saved to {path}.")

    def test_refuses_outside_home(self):
        """A path outside the home folder is refused, nothing written."""
        tools_research._last["topic"], tools_research._last["brief"] = "x", "y [1]."
        self.assertIn("only save inside your home folder", tools_research.save_research("/etc/notes.md"))

    def test_route(self):
        """The ways people ask to save what she just researched."""
        self.assertEqual(tools.plan("save that"), [("save_research", ("",))])
        self.assertEqual(tools.plan("save it to ~/Desktop/notes.md"), [("save_research", ("~/Desktop/notes.md",))])


if __name__ == "__main__":
    unittest.main()
