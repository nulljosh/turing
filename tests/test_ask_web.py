"""ask_web.py: the cached fetcher, the Wikidata officeholder lookup, the page reader and the title guards, with every
network call stood in and the cache pointed at a temp file.

Run: python3 tests/test_ask_web.py
"""
import io
import json
import os
import sys
import tempfile
import time
import unittest
from unittest import mock

os.environ["SAMANTHA_HEADLESS"] = "1"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app"))
import ask_web  # noqa: E402


class FakeResp(io.BytesIO):
    """urlopen's return value stood in: a context manager that reads bytes."""

    def __enter__(self):
        """Hand back the stream."""
        return self

    def __exit__(self, *a):
        """Nothing to close."""
        return False


class Cache(unittest.TestCase):
    """The on-disk cache: load, put, get, stale, unwritable."""

    def setUp(self):
        """A temp cache file and a cleared in-memory cache."""
        self.dir = tempfile.mkdtemp()
        self.p = mock.patch.object(ask_web, "HTTP_CACHE", os.path.join(self.dir, "c.json"))
        self.p.start()
        ask_web._http_cache = None

    def tearDown(self):
        """Back to the real cache path, memory cleared."""
        self.p.stop()
        ask_web._http_cache = None

    def test_roundtrip_and_stale(self):
        """A missing file loads as empty; a put is read back; an entry older than the TTL is gone."""
        self.assertEqual(ask_web._cache_load(), {})
        ask_web._cache_put("u", {"a": 1})
        self.assertEqual(ask_web._cache_get("u"), {"a": 1})
        ask_web._http_cache = None
        self.assertEqual(ask_web._cache_get("u"), {"a": 1})  # survived a reload from disk
        with mock.patch.object(ask_web.time, "time", return_value=time.time() + ask_web.HTTP_CACHE_TTL + 1):
            self.assertIsNone(ask_web._cache_get("u"))
        self.assertIsNone(ask_web._cache_get("never"))

    def test_unwritable_cache_still_answers(self):
        """A cache path that cannot be written is ignored, the value still comes back from memory."""
        with mock.patch.object(ask_web, "HTTP_CACHE", os.path.join(self.dir, "no", "such", "c.json")):
            ask_web._cache_put("u", 1)
            self.assertEqual(ask_web._cache_get("u"), 1)

    def test_http_json_caches_success_and_never_failure(self):
        """One fetch, then the cache answers; a failure returns on_error and is fetched again next time."""
        with mock.patch("urllib.request.urlopen", return_value=FakeResp(b'{"ok": 1}')) as up:
            self.assertEqual(ask_web.http_json("http://x/a"), {"ok": 1})
            self.assertEqual(ask_web.http_json("http://x/a"), {"ok": 1})
        self.assertEqual(up.call_count, 1)
        with mock.patch("urllib.request.urlopen", side_effect=OSError("down")) as up:
            self.assertIsNone(ask_web.http_json("http://x/b"))
            self.assertIs(ask_web.http_json("http://x/b", on_error=ask_web.FETCH_FAILED), ask_web.FETCH_FAILED)
        self.assertEqual(up.call_count, 2)


class Officeholder(unittest.TestCase):
    """current_officeholder against a stood-in Wikidata."""

    def wikidata(self, search=None, claims=None, entities=None, fail=()):
        """http_json stood in: each endpoint answers from these, or FETCH_FAILED when named in fail."""
        def fake(url, timeout=8, on_error=None):
            """The endpoint named in the URL answers, or on_error when it is one of the failing ones."""
            for key, val in (("wbsearchentities", search), ("wbgetclaims", claims), ("wbgetentities", entities)):
                if key in url:
                    return on_error if key in fail else val
            raise AssertionError(url)
        return mock.patch.object(ask_web, "http_json", side_effect=fake)

    def test_not_a_who_question(self):
        """Anything but "who is/who's" is not this lookup's business, no request made."""
        with mock.patch.object(ask_web, "http_json", side_effect=AssertionError("fetched")):
            self.assertEqual(ask_web.current_officeholder("prime minister of canada"), (None, None))

    def test_outages_are_unreachable_not_absent(self):
        """A failed request at any of the three steps says UNREACHABLE, never "no such office"."""
        hits = {"search": [{"id": "Q1", "label": "Prime Minister of Canada"}]}
        claims = {"claims": {"P1308": [{"rank": "preferred", "mainsnak": {"datavalue": {"value": {"id": "Q9"}}}}]}}
        for fail in ("wbsearchentities", "wbgetclaims", "wbgetentities"):
            with self.wikidata(hits, claims, {}, fail=(fail,)):
                self.assertEqual(ask_web.current_officeholder("who is the current prime minister of canada"), (None, ask_web.UNREACHABLE))

    def test_preferred_rank_wins_then_no_end_date(self):
        """The preferred claim is the holder; without one, the first claim with no end time; all ended is nothing."""
        hits = {"search": [{"id": "Q1", "label": "Prime Minister of Canada"}]}
        ent = lambda qid, name: {"entities": {qid: {"labels": {"en": {"value": name}}}}}
        snak = lambda qid, **k: {"mainsnak": {"datavalue": {"value": {"id": qid}}}, **k}
        with self.wikidata(hits, {"claims": {"P1308": [snak("Q8", qualifiers={}), snak("Q9", rank="preferred")]}}, ent("Q9", "Mark Carney")):
            self.assertEqual(ask_web.current_officeholder("who's the prime minister of canada?"), ("Mark Carney (Prime Minister of Canada).", "Wikidata"))
        with self.wikidata(hits, {"claims": {"P1308": [snak("Q7", qualifiers={"P582": []}), snak("Q8", qualifiers={})]}}, ent("Q8", "Someone")):
            self.assertEqual(ask_web.current_officeholder("who is the prime minister of canada")[0], "Someone (Prime Minister of Canada).")
        with self.wikidata(hits, {"claims": {"P1308": [snak("Q7", qualifiers={"P582": []})]}}, {}):
            self.assertEqual(ask_web.current_officeholder("who is the prime minister of canada"), (None, None))
        with self.wikidata({"search": []}, {}, {}):
            self.assertEqual(ask_web.current_officeholder("who is the king of nowhere"), (None, None))
        with self.wikidata(hits, {"claims": {"P1308": [snak("Q9", rank="preferred")]}}, {"entities": {}}):
            self.assertEqual(ask_web.current_officeholder("who is the prime minister of canada"), (None, None))


class Reader(unittest.TestCase):
    """fetch_text, read_article and the guards around a found page."""

    def setUp(self):
        """Cache in a temp file."""
        self.dir = tempfile.mkdtemp()
        self.p = mock.patch.object(ask_web, "HTTP_CACHE", os.path.join(self.dir, "c.json"))
        self.p.start()
        ask_web._http_cache = None

    def tearDown(self):
        """Restore."""
        self.p.stop()
        ask_web._http_cache = None

    def test_fetch_text_strips_tags_and_declines_thin_pages(self):
        """Script and style go, tags go, whitespace folds; under 200 characters or an error is None."""
        page = b"<html><script>var x=1</script><style>p{}</style><p>Hello &amp; welcome. " + b"word " * 60 + b"</p></html>"
        with mock.patch("urllib.request.urlopen", return_value=FakeResp(page)):
            text = ask_web.fetch_text("http://x")
        self.assertTrue(text.startswith("Hello & welcome. word word"))
        self.assertNotIn("var x", text)
        with mock.patch("urllib.request.urlopen", return_value=FakeResp(b"<p>tiny</p>")):
            self.assertIsNone(ask_web.fetch_text("http://x"))
        with mock.patch("urllib.request.urlopen", side_effect=OSError("down")):
            self.assertIsNone(ask_web.fetch_text("http://x"))

    def test_normalize_and_definition(self):
        """Filler is stripped before a search; a title that is the thing asked counts as its definition."""
        self.assertEqual(ask_web.normalize_query("tell me about the tokyo"), "tokyo")
        self.assertEqual(ask_web.normalize_query("???"), "???")
        self.assertTrue(ask_web._is_definition_of("who is marie curie", "Marie Curie"))
        self.assertTrue(ask_web._is_definition_of("what is mercury", "Mercury (planet)"))
        self.assertFalse(ask_web._is_definition_of("who invented the telephone", "Telephone"))
        self.assertFalse(ask_web._is_definition_of("why is the sky blue", "Sky blue"))  # a why question wants a reason, not a colour

    def page(self, extract):
        """http_json stood in with one Wikipedia extract."""
        return mock.patch.object(ask_web, "http_json", return_value={"query": {"pages": {"1": {"extract": extract}}}})

    def ollama(self, answer):
        """urlopen stood in with one reader reply."""
        return mock.patch("urllib.request.urlopen", return_value=FakeResp(json.dumps({"message": {"content": answer}}).encode()))

    def test_read_article_grounds_declines_and_caches(self):
        """A grounded answer is kept and cached; a name the page never said, a decline, or an echo is dropped; no Ollama is None and not cached."""
        text = "World War II ended in 1945. It began in 1939."
        with self.page(text), self.ollama("<think>hm</think>It ended in 1945."):
            self.assertEqual(ask_web.read_article("what year did world war 2 end", "World War II"), "It ended in 1945.")
        with mock.patch.object(ask_web, "http_json", side_effect=AssertionError("refetched")):
            self.assertEqual(ask_web.read_article("what year did world war 2 end", "World War II"), "It ended in 1945.")
        for bad in ("It ended in 1946.", "The text does not say.", "UNKNOWN", "World war 2 end"):
            with self.page(text), self.ollama(bad):
                self.assertIsNone(ask_web.read_article(f"when did world war 2 end {bad[:3]}", "World War II"))
        with self.page("Mercury may refer to: the planet, the element."), self.ollama("x"):
            self.assertIsNone(ask_web.read_article("what is mercury", "Mercury"))
        with self.page(text), mock.patch("urllib.request.urlopen", side_effect=OSError("no ollama")):
            self.assertIsNone(ask_web.read_article("who started it", "World War II"))
        self.assertIsNone(ask_web._cache_get(f"reader3:{ask_web.READER_MODEL}:World War II:who started it"))

    def test_reading_order_and_plausibility(self):
        """Lists and question-titled pages are skipped, pages named by the question's words go first, hedged snippets do not count."""
        asked = set(ask_web._keywords("largest ocean"))
        found = [{"title": "List of oceans", "snippet": "largest ocean"}, {"title": "What Is an Ocean", "snippet": ""},
                 {"title": "Ocean sunfish", "snippet": "one of the largest ocean fish"}, {"title": "Pacific Ocean", "snippet": "the largest ocean"},
                 {"title": "Ocean", "snippet": ""}, {"title": "Blue whale", "snippet": "the largest animal in the ocean"}]
        self.assertEqual(ask_web._reading_order(asked, found), ["Ocean", "Ocean sunfish", "Pacific Ocean", "Blue whale"])
        self.assertTrue(ask_web._wikipedia_answer_is_plausible("how tall is everest", "Mount Everest", "Everest is 8,848 m."))
        self.assertFalse(ask_web._wikipedia_answer_is_plausible("how many days in a week", "Bodybuilding.com", "A fitness site."))
        self.assertTrue(ask_web._wikipedia_answer_is_plausible("tell me something", "Anything", "Prose."))


if __name__ == "__main__":
    unittest.main()
