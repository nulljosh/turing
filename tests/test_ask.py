"""ask.py: the answer chain end to end with every outside call stood in: brain search, DuckDuckGo, Wikipedia,
the library shelf, the FAQ, the tools and the generator.

Run: python3 tests/test_ask.py
"""
import io
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

os.environ["SAMANTHA_HEADLESS"] = "1"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app"))
import ask  # noqa: E402
import ask_web  # noqa: E402


class FakeResp(io.BytesIO):
    """urlopen's return value stood in."""

    def __enter__(self):
        """Hand back the stream."""
        return self

    def __exit__(self, *a):
        """Nothing to close."""
        return False


def web(**answers):
    """http_json stood in: the first key found in the URL answers; FETCH_FAILED when its value is "down"."""
    def fake(url, timeout=8, on_error=None):
        """Match the URL against the keys given."""
        for key, val in answers.items():
            if key in url:
                return on_error if val == "down" else val
        return None
    return mock.patch.object(ask, "http_json", side_effect=fake)


class Brain(unittest.TestCase):
    """brain_token and search: the private RAG degrades to nothing, never a crash."""

    def setUp(self):
        """Cache and env file in a temp dir."""
        self.dir = tempfile.mkdtemp()
        self.patches = [mock.patch.object(ask_web, "HTTP_CACHE", os.path.join(self.dir, "c.json")),
                        mock.patch.object(ask, "BRAIN_ENV", os.path.join(self.dir, ".env.local"))]
        for p in self.patches:
            p.start()
        ask_web._http_cache = None

    def tearDown(self):
        """Restore."""
        for p in self.patches:
            p.stop()
        ask_web._http_cache = None

    def test_token_and_search(self):
        """No env file means no token and no search; with one, turing's own sources come first and a failure is empty."""
        self.assertIsNone(ask.brain_token())
        self.assertEqual(ask.search("x"), [])
        with open(ask.BRAIN_ENV, "w") as f:
            f.write('OTHER=1\nBRAIN_TOKEN="tok"\n')
        self.assertEqual(ask.brain_token(), "tok")
        rows = [{"source": "/nimble/README.md", "text": "a"}, {"source": "/turing/docs/FAQ.md", "text": "b"}]
        with mock.patch("urllib.request.urlopen", return_value=FakeResp(json.dumps({"results": rows}).encode())) as up:
            self.assertEqual([r["source"] for r in ask.search("x", limit=2)], ["/turing/docs/FAQ.md", "/nimble/README.md"])
            self.assertEqual(up.call_args[0][0].headers["Authorization"], "Bearer tok")
            self.assertEqual(len(ask.search("x", limit=1)), 1)  # cached, no second request
        self.assertEqual(up.call_count, 1)
        with mock.patch("urllib.request.urlopen", side_effect=OSError("down")):
            self.assertEqual(ask.search("other"), [])


class Local(unittest.TestCase):
    """local_answer: exact answers, then the tools, and a broken tool is a sentence."""

    def test_exact_then_tools(self):
        """Arithmetic needs no tool; a command runs a tool; hands=False never reaches the tools; a crash is reported."""
        self.assertEqual(ask.local_answer("what is 2+2")[1], "arithmetic")
        import tools
        with mock.patch.object(tools, "do", return_value="Opened Chrome."):
            self.assertEqual(ask.local_answer("open chrome"), ("Opened Chrome.", "tools"))
        with mock.patch.object(tools, "do", side_effect=AssertionError("never")):
            self.assertEqual(ask.local_answer("open chrome", hands=False), (None, None))
        with mock.patch.object(tools, "do", side_effect=RuntimeError("boom")):
            answer, source = ask.local_answer("open chrome")
        self.assertEqual(source, "tools")
        self.assertTrue(answer)
        with mock.patch.object(tools, "do", return_value=None):
            self.assertEqual(ask.local_answer("open chrome"), (None, None))


class GeneralKnowledge(unittest.TestCase):
    """general_knowledge: officeholder, DuckDuckGo, Wikipedia search, reader, summary, shelf, and the unreachable verdict."""

    def setUp(self):
        """No tools, no shelf unless a test says so."""
        import tools
        self.patches = [mock.patch.object(tools, "do", return_value=None), mock.patch.object(ask.library, "look_up", return_value=(None, None))]
        for p in self.patches:
            p.start()

    def tearDown(self):
        """Restore."""
        for p in self.patches:
            p.stop()

    def test_nothing_to_look_up(self):
        """A question with no content word never reaches the web."""
        with mock.patch.object(ask, "http_json", side_effect=AssertionError("fetched")):
            self.assertEqual(ask.general_knowledge("why"), (None, None))

    def test_officeholder_first(self):
        """A live office answer wins before any search; skip_officeholder skips it."""
        with mock.patch.object(ask, "current_officeholder", return_value=("Mark Carney (PM).", "Wikidata")) as co, web():
            self.assertEqual(ask.general_knowledge("who is the prime minister of canada"), ("Mark Carney (PM).", "Wikidata"))
            self.assertEqual(ask.general_knowledge("who is the prime minister of canada", skip_officeholder=True), (None, None))
        self.assertEqual(co.call_count, 1)

    def test_duckduckgo_fields(self):
        """An Answer is taken as is; an abstract counts only when the heading is the thing asked."""
        with web(duckduckgo={"Answer": "42"}):
            self.assertEqual(ask.general_knowledge("what is six times seven"), ("42", "DuckDuckGo"))
        with web(duckduckgo={"AbstractText": "Marie Curie was a physicist.", "AbstractSource": "Wikipedia", "Heading": "Marie Curie"}):
            self.assertEqual(ask.general_knowledge("who is marie curie"), ("Marie Curie was a physicist.", "Wikipedia"))
        with web(duckduckgo={"AbstractText": "A telephone is a device.", "Heading": "Telephone"}, **{"list=search": {}}):
            self.assertEqual(ask.general_knowledge("who invented the telephone"), (None, None))

    def test_wikipedia_summary_reader_and_disambiguation(self):
        """A definition page's summary answers; a non-definition page is read; a disambiguation page is skipped."""
        hit = {"query": {"search": [{"title": "Marie Curie", "snippet": ""}]}}
        with web(duckduckgo={}, **{"list=search": hit, "page/summary": {"extract": "Marie Curie was a physicist."}}):
            self.assertEqual(ask.general_knowledge("who is marie curie"), ("Marie Curie was a physicist.", "Wikipedia: Marie Curie"))
        hit = {"query": {"search": [{"title": "Telephone", "snippet": "the telephone was invented"}]}}
        with web(duckduckgo={}, **{"list=search": hit, "page/summary": {"extract": "A telephone is a device."}}), \
                mock.patch.object(ask, "read_article", return_value="Alexander Graham Bell invented it.") as rd:
            self.assertEqual(ask.general_knowledge("who invented the telephone"), ("Alexander Graham Bell invented it.", "Wikipedia: Telephone"))
        rd.assert_called_once_with("who invented the telephone", "Telephone")
        with web(duckduckgo={}, **{"list=search": hit, "page/summary": {"extract": "A telephone is a device."}}), \
                mock.patch.object(ask, "read_article", return_value=None):
            self.assertEqual(ask.general_knowledge("who invented the telephone"), (None, None))
        hit = {"query": {"search": [{"title": "Mercury", "snippet": ""}]}}
        with web(duckduckgo={}, **{"list=search": hit, "page/summary": {"type": "disambiguation", "extract": "Mercury may refer to"}}):
            self.assertEqual(ask.general_knowledge("what is mercury"), (None, None))

    def test_opensearch_fallback_and_shelf(self):
        """No fulltext hit: opensearch names the page; and the shelf answers when the web has nothing."""
        with web(duckduckgo={}, **{"list=search": {"query": {"search": []}}, "opensearch": ["q", ["Ada Lovelace"]], "page/summary": {"extract": "Ada Lovelace was a mathematician."}}):
            self.assertEqual(ask.general_knowledge("who is ada lovelace")[1], "Wikipedia: Ada Lovelace")
        with web(duckduckgo={}, **{"list=search": {"query": {"search": []}}, "opensearch": None}), \
                mock.patch.object(ask.library, "look_up", return_value=("From the shelf.", "Library: Tides")):
            self.assertEqual(ask.general_knowledge("what causes tides"), ("From the shelf.", "Library: Tides"))

    def test_unreachable_is_not_absent(self):
        """Every service down is UNREACHABLE; services up with nothing to say is plain nothing."""
        with web(duckduckgo="down", **{"list=search": "down"}):
            self.assertEqual(ask.general_knowledge("what causes tides"), (None, ask.UNREACHABLE))
        with web(duckduckgo={}, **{"list=search": {"query": {"search": []}}}):
            self.assertEqual(ask.general_knowledge("what causes tides"), (None, None))


class Shapes(unittest.TestCase):
    """is_project_question and is_question."""

    def test_project_and_question_shape(self):
        """Project words and bare "model"/"project" scope a question; Alan Turing is a person; tasks are not questions."""
        self.assertTrue(ask.is_project_question("is the model good?"))
        self.assertTrue(ask.is_project_question("is this project blocked"))
        self.assertFalse(ask.is_project_question("who was alan turing"))
        self.assertFalse(ask.is_project_question("what causes tides"))
        self.assertTrue(ask.is_question("tell me about photosynthesis"))
        self.assertTrue(ask.is_question("tides?"))
        self.assertFalse(ask.is_question("write a commit message for X"))


class Chain(unittest.TestCase):
    """ask(): each stop in the chain, with the ones after it forbidden."""

    def setUp(self):
        """No tools, no FAQ, no brain, no shelf, cache in a temp file."""
        import tools
        self.dir = tempfile.mkdtemp()
        self.patches = [mock.patch.object(tools, "do", return_value=None), mock.patch.object(ask, "faq_match", return_value=None),
                        mock.patch.object(ask, "search", return_value=[]), mock.patch.object(ask.library, "look_up", return_value=(None, None)),
                        mock.patch.object(ask_web, "HTTP_CACHE", os.path.join(self.dir, "c.json"))]
        for p in self.patches:
            p.start()
        ask_web._http_cache = None

    def tearDown(self):
        """Restore."""
        for p in self.patches:
            p.stop()
        ask_web._http_cache = None

    def test_exact_officeholder_faq_and_knowledge(self):
        """Arithmetic, a live office, the FAQ and the encyclopedia each answer with their own source."""
        self.assertEqual(ask.ask("what is 2+2"), ("2+2 = 4", ["arithmetic"]))
        with mock.patch.object(ask, "current_officeholder", return_value=("Mark Carney (PM).", "Wikidata")):
            self.assertEqual(ask.ask("who is the prime minister of canada"), ("Mark Carney (PM).", ["Wikidata"]))
        with mock.patch.object(ask, "faq_match", return_value="She is a small local model."):
            self.assertEqual(ask.ask("what is samantha"), ("She is a small local model.", [ask.FAQ_PATH]))
        with mock.patch.object(ask, "general_knowledge", return_value=("Tides come from the Moon.", "Wikipedia: Tide")):
            self.assertEqual(ask.ask("what causes tides"), ("Tides come from the Moon.", ["Wikipedia: Tide"]))

    def test_outages_and_out_of_scope(self):
        """Wikidata down skips the FAQ and still tries the encyclopedia; the web down is NETWORK_DOWN; nothing found is OUT_OF_SCOPE."""
        with mock.patch.object(ask, "current_officeholder", return_value=(None, ask.UNREACHABLE)), \
                mock.patch.object(ask, "faq_match", side_effect=AssertionError("faq")), \
                mock.patch.object(ask, "general_knowledge", return_value=("Steve Jobs co-founded Apple.", "Wikipedia: Steve Jobs")) as gk:
            self.assertEqual(ask.ask("who is steve jobs")[0], "Steve Jobs co-founded Apple.")
            self.assertTrue(gk.call_args[1]["skip_officeholder"])
            gk.return_value = (None, None)
            self.assertEqual(ask.ask("who is steve jobs"), (ask.LOOKUP_FAILED, []))
        with mock.patch.object(ask, "current_officeholder", return_value=(None, ask.UNREACHABLE)), \
                mock.patch.object(ask, "general_knowledge", return_value=("The prime minister of Canada is the head of government.", "Wikipedia: Prime Minister of Canada")):
            self.assertEqual(ask.ask("who is the prime minister of canada"), (ask.LOOKUP_FAILED, []))  # the office page is not the holder
        with mock.patch.object(ask, "general_knowledge", return_value=(None, ask.UNREACHABLE)):
            self.assertEqual(ask.ask("what causes tides"), (ask.NETWORK_DOWN, []))
        with mock.patch.object(ask, "general_knowledge", return_value=(None, None)):
            self.assertEqual(ask.ask("what causes tides"), (ask.OUT_OF_SCOPE, []))

    def test_project_question_extracts_then_generates_and_caches(self):
        """A project question answers from retrieval when a passage fits, else the generator runs once and is cached."""
        rows = [{"source": "/turing/docs/FAQ.md", "text": "The picker is a 1.5B model."}]
        with mock.patch.object(ask, "search", return_value=rows), mock.patch.object(ask, "try_extract", return_value="The picker is a 1.5B model."):
            self.assertEqual(ask.ask("how big is the picker model"), ("The picker is a 1.5B model.", ["/turing/docs/FAQ.md"]))
        fake = mock.Mock(stdout="prompt echo\n==========\nShe runs on this Mac.\n==========\n")
        with mock.patch.object(ask, "search", return_value=rows), mock.patch.object(ask, "try_extract", return_value=None), \
                mock.patch.object(ask.subprocess, "run", return_value=fake) as run:
            self.assertEqual(ask.ask("where does the model run"), ("She runs on this Mac.", ["/turing/docs/FAQ.md"]))
            self.assertEqual(ask.ask("where does the model run")[0], "She runs on this Mac.")
        self.assertEqual(run.call_count, 1)
        self.assertIn("--adapter-path", run.call_args[0][0])


if __name__ == "__main__":
    unittest.main()
