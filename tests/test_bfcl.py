"""eval/bfcl.py: the AST scorer, the loose value compare, reply parsing, the prompt, and the endpoint call.

The model is never called. The chat function is a stand-in passed to run(), and the HTTP test mocks urlopen, so
localhost:8000 is never touched. The dry run scores the cached possible answers, which must give 100 percent.

Run: python3 tests/test_bfcl.py
"""
import io
import json
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "eval"))
import bfcl  # noqa: E402

TRUTH = [{"calculate_triangle_area": {"base": [10], "height": [5], "unit": ["units", ""]}}]


class Scorer(unittest.TestCase):
    """The AST rules: name, required values, optional arguments, and no invented arguments."""

    def test_exact_match_passes(self):
        """A call with the right name and both required values passes."""
        self.assertTrue(bfcl.score({"name": "calculate_triangle_area", "arguments": {"base": 10, "height": 5}}, TRUTH))

    def test_optional_argument_may_be_left_out(self):
        """Leaving out an argument listed with an empty-string option is fine."""
        self.assertTrue(bfcl.score({"name": "calculate_triangle_area", "arguments": {"base": 10, "height": 5, "unit": "units"}}, TRUTH))
        self.assertTrue(bfcl.score({"name": "calculate_triangle_area", "arguments": {"base": 10, "height": 5}}, TRUTH))

    def test_wrong_name_fails(self):
        """A different function name fails even with the right arguments."""
        self.assertFalse(bfcl.score({"name": "triangle_area", "arguments": {"base": 10, "height": 5}}, TRUTH))

    def test_missing_required_argument_fails(self):
        """Dropping a required argument fails."""
        self.assertFalse(bfcl.score({"name": "calculate_triangle_area", "arguments": {"base": 10}}, TRUTH))

    def test_wrong_value_fails(self):
        """A required value outside the accepted set fails."""
        self.assertFalse(bfcl.score({"name": "calculate_triangle_area", "arguments": {"base": 10, "height": 6}}, TRUTH))

    def test_invented_argument_fails(self):
        """An argument the possible answer never lists fails, as BFCL counts it."""
        self.assertFalse(bfcl.score({"name": "calculate_triangle_area", "arguments": {"base": 10, "height": 5, "color": "red"}}, TRUTH))

    def test_non_dict_and_missing_arguments(self):
        """A non-object reply fails; a call with no arguments key is treated as empty and fails on a required one."""
        self.assertFalse(bfcl.score(None, TRUTH))
        self.assertFalse(bfcl.score({"name": "calculate_triangle_area"}, TRUTH))
        self.assertFalse(bfcl.score({"name": "calculate_triangle_area", "arguments": ["10", "5"]}, TRUTH))


class LooseCompare(unittest.TestCase):
    """Numbers as floats, strings case-insensitive and stripped, lists and dicts element by element."""

    def test_numbers_compare_as_floats(self):
        """10, 10.0 and "10" are the same value; 10 and 11 are not."""
        self.assertTrue(bfcl.loose(10, 10.0))
        self.assertTrue(bfcl.loose("10", 10))
        self.assertFalse(bfcl.loose(10, 11))

    def test_strings_ignore_case_and_outer_space(self):
        """" Paris " matches "paris"."""
        self.assertTrue(bfcl.loose(" Paris ", "paris"))
        self.assertFalse(bfcl.loose("Paris", "London"))

    def test_bool_is_not_a_number(self):
        """True does not equal 1 in an argument."""
        self.assertFalse(bfcl.loose(True, 1))
        self.assertTrue(bfcl.loose(True, True))

    def test_lists_and_dicts(self):
        """Nested values compare element by element and key by key."""
        self.assertTrue(bfcl.loose([1, "A"], [1.0, "a"]))
        self.assertFalse(bfcl.loose([1, 2], [1]))
        self.assertTrue(bfcl.loose({"x": "Hi"}, {"x": "hi"}))
        self.assertFalse(bfcl.loose({"x": 1}, {"y": 1}))


class Parsing(unittest.TestCase):
    """Pulling the first JSON object out of a reply, with or without fences and prose."""

    def test_plain_json(self):
        """A bare object parses."""
        self.assertEqual(bfcl.parse_call('{"name": "f", "arguments": {}}'), {"name": "f", "arguments": {}})

    def test_fenced_and_prose(self):
        """A fenced block and a sentence before or after still give the object."""
        reply = 'Sure.\n```json\n{"name": "f", "arguments": {"a": 1}}\n```\nDone.'
        self.assertEqual(bfcl.parse_call(reply)["arguments"], {"a": 1})

    def test_garbage_is_none(self):
        """No object, broken JSON, or a JSON list all come back as None."""
        self.assertIsNone(bfcl.parse_call("no json here"))
        self.assertIsNone(bfcl.parse_call('{"name": "f", "arguments": {'))
        self.assertIsNone(bfcl.parse_call("[1, 2]"))
        self.assertIsNone(bfcl.parse_call(None))


class Data(unittest.TestCase):
    """The cached BFCL files join into cases, and the dry run gives 100 percent."""

    def test_cases_load_and_join(self):
        """Every question has a possible answer, and the first case is the triangle one."""
        cases = bfcl.load_cases()
        self.assertGreater(len(cases), 0)
        self.assertEqual(cases[0]["id"], "simple_0")
        self.assertEqual(cases[0]["truth"], TRUTH)
        self.assertIn("triangle", cases[0]["question"])

    def test_dry_run_scores_every_case(self):
        """Scoring each possible answer as the reply gives 100 percent."""
        correct, total = bfcl.run(dry=True)
        self.assertEqual(correct, total)
        self.assertGreater(total, 0)

    def test_dry_limit_runs_first_n(self):
        """--limit N runs exactly the first N cases."""
        correct, total = bfcl.run(dry=True, limit=5)
        self.assertEqual((correct, total), (5, 5))

    def test_prompt_carries_question_and_schema(self):
        """The user's words go in the user turn; the function schema goes in the system turn."""
        messages = bfcl.build_messages("Find the area.", [{"name": "calculate_triangle_area"}])
        self.assertEqual(messages[0]["role"], "system")
        self.assertIn("calculate_triangle_area", messages[0]["content"])
        self.assertEqual(messages[1], {"role": "user", "content": "Find the area."})


class Runner(unittest.TestCase):
    """run() with a stand-in model: good replies score, garbage scores zero, and the failures are printed."""

    def test_good_replies_score_full(self):
        """A chat function that returns the right call gets every case."""
        cases = bfcl.load_cases()
        answers = {c["question"]: c["truth"] for c in cases}

        def oracle(model, messages):
            """Look the case up by its user question and reply with the possible answer."""
            return bfcl.dry_reply(answers[messages[-1]["content"]])
        correct, total = bfcl.run(model="m", limit=10, caller=oracle, out=lambda s: None)
        self.assertEqual((correct, total), (10, 10))

    def test_garbage_replies_score_zero_and_are_printed(self):
        """Replies with no JSON score zero, and each failure is printed with its case id."""
        printed = []
        correct, total = bfcl.run(model="m", limit=3, caller=lambda m, msgs: "I cannot do that.", out=printed.append)
        self.assertEqual((correct, total), (0, 3))
        self.assertEqual(len(printed), 3)
        self.assertIn("simple_0", printed[0])

    def test_model_id_is_passed_through(self):
        """The model id from --model reaches the chat function unchanged."""
        seen = []
        bfcl.run(model="my-model", limit=1, caller=lambda m, msgs: seen.append(m) or "", out=lambda s: None)
        self.assertEqual(seen, ["my-model"])

    def test_default_model_and_endpoint(self):
        """The default model is the 1.5B hands model and the endpoint is oMLX on port 8000."""
        self.assertEqual(bfcl.DEFAULT_MODEL, "trommatic--samantha-hands-1.5b-mlx")
        self.assertEqual(bfcl.ENDPOINT, "http://localhost:8000/v1/chat/completions")


class Endpoint(unittest.TestCase):
    """call_model posts an OpenAI-style body and reads the first choice; urlopen is mocked."""

    def test_posts_chat_and_reads_reply(self):
        """The request goes to the endpoint with the model id and messages, and the reply text comes back."""
        body = json.dumps({"choices": [{"message": {"content": '{"name": "f", "arguments": {}}'}}]}).encode()
        fake = io.BytesIO(body)
        fake.__enter__ = lambda s: s
        fake.__exit__ = lambda s, *a: False
        with mock.patch.object(bfcl.urllib.request, "urlopen", return_value=fake) as opened:
            reply = bfcl.call_model("my-model", [{"role": "user", "content": "hi"}])
        self.assertEqual(reply, '{"name": "f", "arguments": {}}')
        req = opened.call_args[0][0]
        self.assertEqual(req.full_url, bfcl.ENDPOINT)
        sent = json.loads(req.data.decode())
        self.assertEqual(sent["model"], "my-model")
        self.assertEqual(sent["messages"], [{"role": "user", "content": "hi"}])
        self.assertEqual(sent["temperature"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
