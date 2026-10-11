"""ask_local.py and ask_faq.py: the exact local answers (arithmetic, units, clock, small talk) and the FAQ matcher's
file parsing, embedding cache, cosine, semantic match and extractors, with the embedder and files stood in.

Run: python3 tests/test_ask_local.py
"""
import os
import re
import sys
import tempfile
import unittest
from unittest import mock

os.environ["SAMANTHA_HEADLESS"] = "1"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app"))
import ask_faq  # noqa: E402
import ask_local  # noqa: E402


class Arithmetic(unittest.TestCase):
    """Words become operators, the AST is whitelisted, and nothing but numbers ever runs."""

    def test_words_roots_and_zero(self):
        """Times, square root, powers and a division by zero all answer; a bare number does not."""
        self.assertEqual(ask_local.arithmetic("what is 10 times 7"), "10 * 7 = 70")
        self.assertEqual(ask_local.arithmetic("square root of 16"), "sqrt(16) = 4")
        self.assertEqual(ask_local.arithmetic("2 ** 3"), "2 ** 3 = 8")
        self.assertIn("divide by zero", ask_local.arithmetic("what is 1/0"))
        self.assertIsNone(ask_local.arithmetic("what is 7"))

    def test_number_words_read_like_digits(self):
        """"ten plus ten" answers like "10 plus 10"; a sentence that is not all numbers and operators still falls through."""
        self.assertEqual(ask_local.arithmetic("what is ten plus ten"), "10 + 10 = 20")
        self.assertEqual(ask_local.arithmetic("whats twenty-five minus nine"), "25 - 9 = 16")
        self.assertEqual(ask_local.arithmetic("how much is one hundred and five divided by five"), "105 / 5 = 21")
        self.assertEqual(ask_local.arithmetic("what is the square root of sixteen"), "sqrt(16) = 4")
        self.assertIsNone(ask_local.arithmetic("who is the first one"))
        self.assertIsNone(ask_local.arithmetic("what is ten"))
        self.assertEqual(ask_local.arithmetic("calculate 15% of 80"), "((15)/100)*(80) = 12")
        self.assertEqual(ask_local.arithmetic("what's 17*23"), "17*23 = 391")
        self.assertEqual(ask_local.arithmetic("whats 2+2"), "2+2 = 4")
        self.assertEqual(ask_local.arithmetic("What's 17 times 23?"), "17 * 23 = 391")
        self.assertEqual(ask_local.arithmetic("how much is 9*9"), "9*9 = 81")

    def test_nothing_but_numbers_runs(self):
        """Names, strings, attribute calls and keyword arguments are all refused before any evaluation."""
        for bad in ("import os", "__import__('os')", "1 + 'a'", "sqrt(x)", "abs(-1)", "sqrt(4, 2)", "2 + x", "(1).real"):
            self.assertIsNone(ask_local.arithmetic(bad), bad)


class Units(unittest.TestCase):
    """convert: temperatures, lengths, masses and volumes, never across dimensions."""

    def test_conversions(self):
        """Fahrenheit, kelvin, miles, litres and the how-many shape each give one tidy number."""
        self.assertEqual(ask_local.convert("convert 100 fahrenheit to celsius"), "100 fahrenheit = 37.7778 celsius")
        self.assertEqual(ask_local.convert("300 k to c"), "300 k = 26.85 c")
        self.assertEqual(ask_local.convert("how many kilometers is 5 miles"), "5 mi = 8.0467 km")
        self.assertEqual(ask_local.convert("what is 1 l in cups"), "1 L = 4.2268 cups")
        self.assertEqual(ask_local.convert("2 lbs in kg"), "2 lb = 0.9072 kg")

    def test_refusals(self):
        """Mass to length, an unknown unit, and a sentence with no units fall through."""
        self.assertIsNone(ask_local.convert("how many kg is 5 miles"))
        self.assertIsNone(ask_local.convert("5 miles to kilowatts"))
        self.assertIsNone(ask_local.convert("how far is the moon"))
        self.assertEqual(ask_local._tidy(2.0), 2)
        self.assertEqual(ask_local._tidy(1.23456), 1.2346)


class ClockAndSmallTalk(unittest.TestCase):
    """clock reads the system clock for present-tense questions only; small talk is anchored to the whole line."""

    def test_clock(self):
        """Time and year answer from the clock; a historical year question does not."""
        self.assertRegex(ask_local.clock("what time is it"), r"^\d{1,2}:\d{2} [AP]M$")
        self.assertRegex(ask_local.clock("what year is it?"), r"^\d{4}$")
        self.assertRegex(ask_local.clock("what is today"), r"^\w+day, \w+ \d{1,2}, \d{4}$")
        self.assertIsNone(ask_local.clock("what year did world war 2 end"))

    def test_small_talk(self):
        """Greetings, thanks, abilities, the pitch and the tool list; a command with a greeting in front still passes through."""
        import tools
        self.assertTrue(ask_local.small_talk("hey there!").startswith("Hi."))
        self.assertEqual(ask_local.small_talk("thanks so much"), "Any time.")
        self.assertIn(f"{len(tools.TOOLS)} tools", ask_local.small_talk("what can you do?"))
        self.assertIn("1.5B", ask_local.small_talk("sell yourself to me"))
        self.assertTrue(ask_local.small_talk("tools").startswith(f"{len(tools.TOOLS)} tools: "))
        self.assertIn("Samantha", ask_local.small_talk("who are you and what can you do"))
        self.assertIsNone(ask_local.small_talk("hey calculate 8 + 8"))
        self.assertIsNone(ask_local.small_talk("help me find a file"))


class Faq(unittest.TestCase):
    """ask_faq: the file, the embedding cache, cosine, the semantic match and the extractors."""

    def setUp(self):
        """FAQ and embedding cache in a temp dir."""
        self.dir = tempfile.mkdtemp()
        self.faq = os.path.join(self.dir, "FAQ.md")
        self.patches = [mock.patch.object(ask_faq, "FAQ_PATH", self.faq), mock.patch.object(ask_faq, "EMBED_CACHE", os.path.join(self.dir, "emb.json"))]
        for p in self.patches:
            p.start()

    def tearDown(self):
        """Restore."""
        for p in self.patches:
            p.stop()

    def test_load_faq(self):
        """A missing file is empty; a heading with no answer is skipped; the rest pair up."""
        self.assertEqual(ask_faq.load_faq(), [])
        with open(self.faq, "w") as f:
            f.write("# FAQ\n\n## Who maintains this project?\nJoshua does.\n\n## Empty one\n\n## What is it?\nA small model.\n")
        self.assertEqual(ask_faq.load_faq(), [("Who maintains this project?", "Joshua does."), ("What is it?", "A small model.")])

    def test_vectors_cache_and_cosine(self):
        """Vectors are embedded once and read from the cache after; no embedder means None; cosine handles a zero vector."""
        with mock.patch.object(ask_faq, "_embed", return_value=[[1.0, 0.0]]) as emb:
            self.assertEqual(ask_faq._faq_vectors(["q"]), [[1.0, 0.0]])
        self.assertEqual(emb.call_count, 1)
        with mock.patch.object(ask_faq, "_embed", side_effect=AssertionError("re-embedded")):
            self.assertEqual(ask_faq._faq_vectors(["q"]), [[1.0, 0.0]])
        with mock.patch.object(ask_faq, "_embed", return_value=None):
            self.assertIsNone(ask_faq._faq_vectors(["other"]))
        self.assertEqual(ask_faq._cosine([1, 0], [1, 0]), 1.0)
        self.assertEqual(ask_faq._cosine([0, 0], [1, 0]), 0.0)

    def test_semantic_match_threshold(self):
        """Above the threshold the FAQ answer comes back; below it, or with no embedder, nothing."""
        pairs = [("Who maintains this project?", "Joshua does.")]
        with mock.patch.object(ask_faq, "_faq_vectors", return_value=[[1.0, 0.0]]):
            with mock.patch.object(ask_faq, "_embed", return_value=[[1.0, 0.0]]):
                self.assertEqual(ask_faq.semantic_faq_match("who works on this", pairs), "Joshua does.")
            with mock.patch.object(ask_faq, "_embed", return_value=[[0.0, 1.0]]):
                self.assertIsNone(ask_faq.semantic_faq_match("is my sink blocked", pairs))
            with mock.patch.object(ask_faq, "_embed", return_value=None):
                self.assertIsNone(ask_faq.semantic_faq_match("who works on this", pairs))
        with mock.patch.object(ask_faq, "_faq_vectors", return_value=None):
            self.assertIsNone(ask_faq.semantic_faq_match("who works on this", pairs))

    def test_try_extract(self):
        """A fixed fact wins; an extractor pulls its pattern out of the context or admits it cannot pin it down; else None."""
        with mock.patch.object(ask_faq, "FIXED_FACTS", [(re.compile(r"what base model"), "Qwen2.5-0.5B")]), \
                mock.patch.object(ask_faq, "EXTRACTORS", [(re.compile(r"what tool trains"), re.compile(r"mlx_lm\.lora"))]):
            self.assertEqual(ask_faq.try_extract("what base model is it", []), "Qwen2.5-0.5B")
            self.assertEqual(ask_faq.try_extract("what tool trains the adapter", [{"text": "run mlx_lm.lora on it"}]), "mlx_lm.lora")
            self.assertEqual(ask_faq.try_extract("what tool trains the adapter", [{"text": "nothing here"}]), ask_faq._CANT_PIN_DOWN)
            self.assertIsNone(ask_faq.try_extract("what colour is the sky", [{"text": "blue"}]))


class Vocative(unittest.TestCase):
    """Her name as an address is not a project keyword and does not hide a greeting (dogfood 5.11.14)."""
    def test_greeting_with_her_name(self):
        """"hey samantha, how's it going" is small talk, and "what is samantha" is still about the project."""
        import ask
        self.assertEqual(ask_local.strip_vocative("hey samantha, how's it going"), "how's it going")
        self.assertEqual(ask_local.strip_vocative("what's the time, samantha"), "what's the time")
        self.assertEqual(ask_local.strip_vocative("what is samantha"), "what is samantha")
        self.assertIsNotNone(ask.local_answer("hey samantha, how's it going")[0])
        self.assertFalse(ask.is_project_question("hey samantha, how's it going"))
        self.assertTrue(ask.is_project_question("samantha, what is turing"))


if __name__ == "__main__":
    unittest.main()
