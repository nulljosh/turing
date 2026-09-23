"""distill.py: what a teacher pair must pass before she trains on it, and how her held-out answers are scored.

Run: python3 test_distill.py
"""
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

os.environ["SAMANTHA_HEADLESS"] = "1"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import distill

PASSAGE = "Epiphany uses Supabase for auth and Upstash Redis for portfolio data. Stripe handles web payments since July."


class Check(unittest.TestCase):
    """Only short, plain, grounded pairs get through."""

    def test_a_grounded_pair_passes(self):
        """Every content word from the passage or the question."""
        self.assertIsNone(distill.check("What does Epiphany use for auth?", "Epiphany uses Supabase for auth.", PASSAGE))

    def test_what_gets_rejected(self):
        """Empty, long, em dash, emoji, talk about the passage, and outside facts."""
        cases = {("", "x"): "empty", ("q", "Supabase. " * 40): "too long",
                 ("q", "Supabase \u2014 for auth."): "em dash or emoji", ("q", "Supabase for auth \U0001F600"): "em dash or emoji",
                 ("q", "The passage says Supabase."): "talks about the passage",
                 ("What does Epiphany use for auth?", "Firebase with Google OAuth and Okta."): "not grounded"}
        for (q, a), why in cases.items():
            self.assertTrue((distill.check(q, a, PASSAGE) or "").startswith(why), (q, a))


class Score(unittest.TestCase):
    """How a held-out answer is marked."""

    def test_answerable_needs_half_the_teacher_words_and_no_decline(self):
        """Half of the teacher's content words and no decline passes; a decline or a miss fails."""
        teacher = "Epiphany uses Supabase for auth."
        self.assertTrue(distill.score("It uses Supabase for auth.", teacher, True))
        self.assertFalse(distill.score(distill.DECLINE, teacher, True))
        self.assertFalse(distill.score("It uses a database.", teacher, True))

    def test_unanswerable_needs_the_decline(self):
        """Only the decline passes when the passages do not hold the answer."""
        self.assertTrue(distill.score(distill.DECLINE, "x", False))
        self.assertFalse(distill.score("Supabase.", "x", False))


class Build(unittest.TestCase):
    """build() keeps held-out passages out of training and wraps every pair in her real prompt."""

    def test_heldout_never_trains_and_prompts_match_chat(self):
        """A tenth of the passages only reach heldout; declines ride on other passages; every prompt is chat.build_prompt's."""
        import chat
        with tempfile.TemporaryDirectory() as d, mock.patch.object(distill, "OUT", d):
            with open(os.path.join(d, "passages.jsonl"), "w") as f:
                for i in range(20):
                    f.write(json.dumps({"id": i, "source": f"repo{i}/README.md", "text": f"Project {i} ships widget{i} daily."}) + "\n")
            with open(os.path.join(d, "qa.jsonl"), "w") as f:
                for i in range(20):
                    f.write(json.dumps({"id": i, "q": f"What does project {i} ship?", "a": f"Project {i} ships widget{i}."}) + "\n")
                f.write("not json\n")
            kept, rejected = distill.build(negatives=1)
            self.assertEqual((kept, rejected), (20, {"unreadable": 1}))
            train = [json.loads(l) for l in open(os.path.join(d, "train.jsonl"))]
            held = [json.loads(l) for l in open(os.path.join(d, "heldout.jsonl"))]
        self.assertEqual(len(held), 4)  # passages 0 and 1: one answer and one decline each
        self.assertFalse(any("widget0 daily" in r["messages"][0]["content"] or "widget1 daily" in r["messages"][0]["content"] for r in train))
        for r in train + held:
            prompt, answer = r["messages"][0]["content"], r["messages"][1]["content"]
            self.assertTrue(prompt.startswith(chat.build_prompt([], "", "q").split("Context:")[0]))
            has_own = any(f"widget{i} daily" in prompt and f"project {i} ship?" in prompt for i in range(20))
            self.assertEqual(answer == distill.DECLINE, not has_own)


if __name__ == "__main__":
    unittest.main()
