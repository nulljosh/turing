"""tools_research.py: research briefs. Wikipedia, the library, the notes and the writer are stood in for.

Run: python3 test_research.py
"""
import os
import sys
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


if __name__ == "__main__":
    unittest.main()
