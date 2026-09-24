"""tools_research.py: research briefs. Wikipedia, the library, the notes and the writer are stood in for.

Run: python3 tests/test_research.py
"""
import os
import sys
import tempfile
import unittest
from unittest import mock

os.environ["SAMANTHA_HEADLESS"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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


class FetchText(unittest.TestCase):
    """ask_web.fetch_text: the shared page fetcher tools.read_page and tools_research.sources both use."""

    def test_strips_tags_to_readable_text(self):
        """Style, script and tags are stripped; the real text stays."""
        import ask_web
        html_page = ("<html><head><style>.x{color:red}</style><script>var x=1;</script></head>"
                     "<body><h1>Turing</h1><p>A small AI model that learns your voice, " + "and your notes. " * 20 + "</p></body></html>")
        with mock.patch("urllib.request.urlopen") as u:
            u.return_value.__enter__.return_value.read.return_value = html_page.encode()
            text = ask_web.fetch_text("https://example.com/docs")
        self.assertNotIn("<", text)
        self.assertIn("Turing", text)
        self.assertIn("A small AI model", text)

    def test_js_only_page_declines(self):
        """A JS-only page serves an almost-empty shell server side; fetch_text refuses to call that readable."""
        import ask_web
        shell = '<html><body><div id="root"></div><script src="app.js"></script></body></html>'
        with mock.patch("urllib.request.urlopen") as u:
            u.return_value.__enter__.return_value.read.return_value = shell.encode()
            self.assertIsNone(ask_web.fetch_text("https://spa.example.com"))

    def test_network_failure_declines(self):
        """A request that raises (down, refused) is a decline, not a crash."""
        import ask_web
        with mock.patch("urllib.request.urlopen", side_effect=OSError("blocked")):
            self.assertIsNone(ask_web.fetch_text("https://example.com"))


class PagedResearch(unittest.TestCase):
    """A page named right in the question is fetched and cited, or honestly declined when it won't read back."""

    def test_named_page_is_added_as_a_source(self):
        """"research https://x.com/docs" reads that page and hands it to sources() alongside Wikipedia."""
        with mock.patch.object(tools_research, "_wikipedia", return_value=[]), \
                mock.patch("ask_web.fetch_text", return_value="The docs say the API takes a topic string.") as fetch:
            found = tools_research.sources("research https://x.com/docs")
        fetch.assert_called_once_with("https://x.com/docs")
        self.assertTrue(any(name == "Page: https://x.com/docs" for name, _ in found))

    def test_js_only_page_is_declined_honestly_not_silently(self):
        """A page that fetches to nothing (JS-only, blocked) is not added as a source, and research() says so
        instead of pretending the page was never named."""
        with mock.patch.object(tools_research, "sources", return_value=SOURCES), \
                mock.patch("tools_llm.ask_llm", return_value="Gutenberg built it around 1440 [1]."):
            reply = tools_research.research("research example.com/app on the printing press")
        self.assertIn("couldn't read", reply)
        self.assertIn("example.com/app", reply)

    def test_a_plain_topic_never_tries_to_fetch_a_page(self):
        """No URL or domain in the topic: no page fetch attempted."""
        self.assertIsNone(tools_research._named_page("the printing press"))
        self.assertEqual(tools_research._named_page("research bbc.com news"), "https://bbc.com")


class FollowUp(unittest.TestCase):
    """"tell me more about X" reuses the last brief's sources before searching again."""

    def setUp(self):
        """Start clean: no brief remembered from another test."""
        self.saved = dict(tools_research._last)

    def tearDown(self):
        """Put any prior state back."""
        tools_research._last.update(self.saved)

    def test_reuses_last_sources_first(self):
        """The follow-up hands the SAME sources back to the writer, no fresh sources() call."""
        tools_research._last["topic"] = "the printing press"
        tools_research._last["brief"] = "Gutenberg built it around 1440 [1]."
        tools_research._last["sources"] = SOURCES
        with mock.patch.object(tools_research, "sources") as fresh_sources, \
                mock.patch("tools_llm.ask_llm", return_value="It spread across Europe within decades [2]."):
            reply = tools_research.research_more("how it spread")
        fresh_sources.assert_not_called()
        self.assertIn("It spread across Europe within decades [2].", reply)

    def test_searches_again_when_old_sources_do_not_cover_it(self):
        """When the old sources can't stand behind anything, research_more falls back to a real search."""
        tools_research._last["topic"] = "the printing press"
        tools_research._last["brief"] = "Gutenberg built it around 1440 [1]."
        tools_research._last["sources"] = SOURCES
        with mock.patch("tools_llm.ask_llm", return_value="It was 1390.  Nothing citable."), \
                mock.patch.object(tools_research, "sources", return_value=[]) as fresh_sources:
            reply = tools_research.research_more("something unrelated")
        fresh_sources.assert_called_once()
        self.assertIn("could not find sources", reply)

    def test_nothing_researched_yet(self):
        """A follow-up before any research is an honest sentence."""
        tools_research._last["topic"] = tools_research._last["brief"] = tools_research._last["sources"] = None
        self.assertIn("have not researched anything", tools_research.research_more("more"))

    def test_route(self):
        """The ways people ask a follow-up."""
        self.assertEqual(tools.plan("tell me more about the silk road"), [("research_more", ("the silk road",))])
        self.assertEqual(tools.plan("tell me more"), [("research_more", ("",))])


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
