"""library.py: her offline library. A stand-in Wikipedia fills a temporary library, so no test touches the network.

Run: python3 test_library.py
"""
import os
import sys
import tempfile
import unittest
import urllib.error
from unittest import mock

os.environ["SAMANTHA_HEADLESS"] = "1"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import library

LEADS = {
    "Kinship": "Kinship is the web of social relationships that form an important part of the lives of all humans. "
               "Anthropologists study how kinship is reckoned through descent and marriage. It varies across cultures. A fourth sentence.",
    "Cultural relativism": "Cultural relativism is the view that beliefs and practices should be understood in the terms of a person's own culture.",
    "Entropy": "Entropy is a scientific concept most commonly associated with disorder, randomness, or uncertainty.",
    "Stub": "Too short.",
}


def fake_wiki(params):
    """A stand-in Wikipedia: one vital list naming every lead above, and their leads, 20 at a time."""
    if params.get("prop") == "links":
        return {"query": {"pages": {"1": {"links": [{"title": t} for t in LEADS]}}}}
    return {"query": {"pages": {str(i): {"title": t, "extract": LEADS[t]} for i, t in enumerate(params["titles"].split("|"))}}}


class Library(unittest.TestCase):
    """What she finds, and what she declines."""

    def setUp(self):
        """A fresh library filled from the stand-in Wikipedia and a one-field fieldbook."""
        self.dir = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"SAMANTHA_LIBRARY": self.dir.name})
        self.env.start()
        book = os.path.join(self.dir.name, "fields.json")
        with open(book, "w") as f:
            f.write('[{"n": "Classical mechanics", "s": "How things move and why.", "p": "Objects keep doing what they are doing until a force acts on them."}]')
        with mock.patch.object(library, "_wiki", side_effect=fake_wiki), mock.patch.object(library, "FIELDBOOK", book), \
                mock.patch.object(library, "VITAL", ["Level/3"]), mock.patch.object(library.time, "sleep"):
            self.saved = library.fetch(log=lambda line: None)

    def tearDown(self):
        """Put the environment back."""
        self.env.stop()
        self.dir.cleanup()

    def test_fetch_saves_the_fieldbook_and_real_leads(self):
        """Every lead with some prose, plus the fieldbook; a stub is skipped."""
        self.assertEqual(self.saved, 4)  # 3 leads + 1 field, not the stub
        self.assertEqual(library.look_up("what is a stub"), (None, None))

    def test_a_page_named_what_was_asked(self):
        """"what is X" finds the page titled X, plurals and articles too, cut to three sentences, and names it."""
        answer, source = library.look_up("What is kinship?")
        self.assertEqual(source, "Wikipedia: Kinship (saved)")
        self.assertTrue(answer.startswith("Kinship is the web") and "fourth" not in answer)
        self.assertEqual(library.look_up("tell me about cultural relativism")[1], "Wikipedia: Cultural relativism (saved)")
        self.assertEqual(library.look_up("define entropy")[1], "Wikipedia: Entropy (saved)")
        self.assertEqual(library.look_up("explain classical mechanics")[1], "Fieldbook: Classical mechanics")
        self.assertEqual(library.look_up('what is "kinship')[1], "Wikipedia: Kinship (saved)")  # a stray quote is not search syntax

    def test_only_a_page_named_what_was_asked_answers(self):
        """Word overlap across pages is not reading: a question that names no page is declined even when the words are there."""
        for q in ("how do anthropologists study kinship", "kinship across cultures", "how many kinship cultures are there",
                  "social relationships of humans"):
            self.assertEqual(library.look_up(q), (None, None), q)

    def test_declines_what_it_does_not_cover(self):
        """Off-library questions and empty ones are declined, never answered with something nearby."""
        for q in ("what is quantum chromodynamics", "who won the 1998 world cup", "", "what is the", "?", 'kinship" OR "entropy'):
            self.assertEqual(library.look_up(q), (None, None), q)

    def test_no_library_yet(self):
        """No library at all is a decline, not a crash."""
        with mock.patch.dict(os.environ, {"SAMANTHA_LIBRARY": os.path.join(self.dir.name, "nope")}):
            self.assertEqual(library.look_up("what is kinship"), (None, None))

    def test_rate_limits_are_waited_out(self):
        """A 429 waits and retries; any other error is raised at once."""
        limited = urllib.error.HTTPError("u", 429, "", {"Retry-After": "1"}, None)
        ok = mock.MagicMock()
        ok.__enter__.return_value.read.return_value = b'{"ok": 1}'
        with mock.patch("urllib.request.urlopen", side_effect=[limited, ok]), mock.patch.object(library.time, "sleep") as slept:
            self.assertEqual(library._wiki({}), {"ok": 1})
        slept.assert_called_once_with(1)
        with mock.patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError("u", 500, "", {}, None)):
            with self.assertRaises(urllib.error.HTTPError):
                library._wiki({})

    def test_words(self):
        """Stopwords out, lowercased."""
        self.assertEqual(library.words("What is the Kinship of humans?"), ["kinship", "humans"])


if __name__ == "__main__":
    unittest.main()
