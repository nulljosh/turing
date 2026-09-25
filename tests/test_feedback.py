"""feedback.py: the matcher, the negatives, logging, the summary, feedback_to_data's dedupe and eval-leak
refusal, and harness.Session catching a rating before any tool runs."""
import os
import sys
import tempfile
import unittest

os.environ["SAMANTHA_HEADLESS"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "training"))
import feedback
import harness
import tools


class MatcherTests(unittest.TestCase):
    """The rating phrases, tight enough that a real sentence never fires them."""

    def test_up_phrasings(self):
        """Every documented up phrasing, and its punctuation variants."""
        for text in ("good", "Good", "good!", "thanks that's right", "thanks, that's right.", "+1", "\U0001F44D"):
            self.assertEqual(feedback.match(text), (1, None), text)

    def test_down_phrasings(self):
        """Every documented down phrasing, and its punctuation variants."""
        for text in ("bad", "wrong", "wrong.", "that's not what I meant", "-1", "\U0001F44E"):
            self.assertEqual(feedback.match(text), (-1, None), text)

    def test_correction(self):
        """"wrong, I meant X" carries the correction text along."""
        self.assertEqual(feedback.match("wrong, I meant open safari"), (-1, "open safari"))
        self.assertEqual(feedback.match("wrong i meant the weather in tokyo"), (-1, "the weather in tokyo"))

    def test_negatives_never_match(self):
        """A real sentence that merely contains a rating word is not a verdict.

        "thanks for nothing" is a judgement call: it reads negative to a person, but it is sarcasm, not one of
        the fixed phrases, and guessing at sarcasm is exactly the kind of false positive this matcher exists to
        avoid, so it stays unrated on purpose, the same as any other sentence outside the fixed list.
        """
        for text in ("good morning", "good morning joshua", "what's wrong with my wifi", "thanks for nothing",
                     "that's not what I ordered", "goodbye", "-100", "+100", "this is bad news", "my wifi is bad"):
            self.assertIsNone(feedback.match(text), text)

    def test_summary_query(self):
        """The read-only summary question, and a sentence that only sounds like it."""
        self.assertTrue(feedback.is_summary("how am I rating you"))
        self.assertTrue(feedback.is_summary("show my feedback?"))
        self.assertFalse(feedback.is_summary("how am I doing"))
        self.assertFalse(feedback.is_summary("what is my feedback about the wifi"))

    def test_parse_calls(self):
        """The tool a turn's log lines named, or "answer" when nothing was called."""
        self.assertEqual(feedback.parse_calls(["  [open_url(github.com)]"]), ("open_url", ("github.com",)))
        self.assertEqual(feedback.parse_calls([]), ("answer", ()))
        self.assertEqual(feedback.parse_calls(None), ("answer", ()))


class RecordTests(unittest.TestCase):
    """Logging to a temporary file, so the real one is never touched."""

    def setUp(self):
        """Point feedback at an empty temporary file."""
        self.path = os.path.join(tempfile.mkdtemp(), "feedback.jsonl")
        os.environ["SAMANTHA_FEEDBACK"] = self.path

    def tearDown(self):
        """Put the environment back."""
        os.environ.pop("SAMANTHA_FEEDBACK", None)

    def test_up_is_noted(self):
        """An up logs and replies plainly."""
        self.assertEqual(feedback.record("what is turing", "answer", (), "a project", 1), "Noted.")
        self.assertTrue(os.path.exists(self.path))

    def test_down_with_correction_is_noted(self):
        """A down carries the correction and says she'll learn from it."""
        reply = feedback.record("open chrom", "answer", (), "huh", -1, "open chrome")
        self.assertEqual(reply, "Noted, I'll learn from that.")

    def test_reply_is_capped(self):
        """Her reply is capped at 500 characters in the log, whatever it actually said."""
        feedback.record("q", "answer", (), "x" * 900, -1, "y")
        entries = feedback._entries()
        self.assertEqual(len(entries[0]["reply"]), 500)

    def test_summary_counts_and_lists_last_five_downs(self):
        """The summary counts both directions and lists only the most recent five downs."""
        self.assertEqual(feedback.feedback_summary(), "No feedback yet.")
        feedback.record("q1", "answer", (), "a", 1)
        for i in range(7):
            feedback.record(f"down{i}", "answer", (), "r", -1, f"meant{i}")
        s = feedback.feedback_summary()
        self.assertIn("1 up, 7 down.", s)
        self.assertNotIn("down0", s)  # only the last five
        self.assertIn("down6", s)
        self.assertIn("meant6", s)


class HarnessCatchesRatingTests(unittest.TestCase):
    """The rating phrase is caught before routing: no tool ever sees "good" or "wrong"."""

    def setUp(self):
        """Point feedback at an empty temporary file."""
        self.path = os.path.join(tempfile.mkdtemp(), "feedback.jsonl")
        os.environ["SAMANTHA_FEEDBACK"] = self.path

    def tearDown(self):
        """Put the environment back."""
        os.environ.pop("SAMANTHA_FEEDBACK", None)

    def session(self):
        """A session that records what it was asked to confirm, and never confirms."""
        asked = []
        return harness.Session(confirm=lambda n, a: asked.append((n, a)) or False, log=lambda line: None), asked

    def test_rating_after_a_tool_call_never_reaches_a_tool(self):
        """A command runs, then "good" rates it without going near tools.do again."""
        s, asked = self.session()
        s.ask("what time is it")
        reply = s.ask("good")
        self.assertEqual(reply, "Noted.")
        self.assertEqual(asked, [])  # nothing was ever offered up for a write confirmation
        entries = feedback._entries()
        self.assertEqual(entries[-1]["rating"], 1)
        self.assertEqual(entries[-1]["query"], "what time is it")

    def test_correction_is_logged_against_the_last_query(self):
        """"wrong, I meant X" logs the previous turn's own query with the correction."""
        s, _ = self.session()
        s.ask("what time is it")
        reply = s.ask("wrong, I meant the weather")
        self.assertEqual(reply, "Noted, I'll learn from that.")
        entries = feedback._entries()
        self.assertEqual(entries[-1]["correction"], "the weather")

    def test_no_history_is_honest(self):
        """A rating with nothing said yet this session is a plain answer, never a crash."""
        s, _ = self.session()
        self.assertEqual(s.ask("good"), "Nothing to rate yet.")

    def test_good_morning_is_not_a_rating(self):
        """A real sentence that starts with "good" still reaches the normal answer chain, not the logger."""
        s, _ = self.session()
        reply = s.ask("good morning")
        self.assertNotIn(reply, ("Noted.", "Noted, I'll learn from that."))

    def test_record_lets_a_generated_answer_be_rated(self):
        """chat.py's Session.record files a turn that never went through tools.do, so a rating right after it
        still has something to rate."""
        s, _ = self.session()
        s.record("what is the capital of france", "Paris.")
        reply = s.ask("good")
        self.assertEqual(reply, "Noted.")
        entries = feedback._entries()
        self.assertEqual(entries[-1]["query"], "what is the capital of france")
        self.assertEqual(entries[-1]["tool"], "answer")

    def test_summary_question_is_read_only(self):
        """"how am I rating you" answers straight from the log, no history needed."""
        s, _ = self.session()
        self.assertEqual(s.ask("how am I rating you"), "No feedback yet.")
        feedback.record("q", "answer", (), "r", 1)
        self.assertIn("1 up, 0 down.", s.ask("show my feedback"))


class FeedbackToDataTests(unittest.TestCase):
    """training/feedback_to_data.py: dedupe, and the refusal to copy an eval phrasing into training."""

    def build(self, entries):
        """build() from feedback_to_data.py, imported lazily so eval/actions.py loads with sys.path set."""
        import feedback_to_data
        return feedback_to_data.build(entries)

    def test_down_without_correction_is_skipped(self):
        """A down that only says something was wrong, with no correction, teaches nothing: skip it."""
        rows = self.build([{"query": "open chrom", "tool": "answer", "args": [], "rating": -1, "correction": None}])
        self.assertEqual(rows, [])

    def test_down_with_correction_is_retargeted(self):
        """The correction is run through the real router, not guessed."""
        rows = self.build([{"query": "open chrom", "tool": "answer", "args": [], "rating": -1, "correction": "open chrome"}])
        self.assertEqual(len(rows), 1)
        self.assertIn("open chrom", rows[0])
        self.assertIn("open_app", rows[0])

    def test_up_confirms_the_tool_already_picked(self):
        """An up becomes a row confirming the same tool and argument. Uses a phrasing eval/actions.py does not
        own, so this checks the confirm path, not the reserved-phrase refusal (see test_never_copies_an_eval_phrasing)."""
        rows = self.build([{"query": "fire up google chrome for me", "tool": "open_app", "args": ["chrome"], "rating": 1}])
        self.assertEqual(len(rows), 1)
        self.assertIn("open_app", rows[0])
        self.assertIn("chrome", rows[0])

    def test_dedupes_by_query(self):
        """The same query twice becomes one row."""
        entries = [{"query": "fire up google chrome for me", "tool": "open_app", "args": ["chrome"], "rating": 1}] * 3
        self.assertEqual(len(self.build(entries)), 1)

    def test_never_copies_an_eval_phrasing(self):
        """A query eval/actions.py's CASES already uses is refused, whatever its rating."""
        import feedback_to_data
        from actions import CASES
        reserved_query = CASES[0][0]
        rows = self.build([{"query": reserved_query, "tool": "open_app", "args": ["chrome"], "rating": 1}])
        self.assertEqual(rows, [])
        self.assertIn(reserved_query.lower().rstrip(".?!"), feedback_to_data.reserved_phrases())


if __name__ == "__main__":
    unittest.main()
