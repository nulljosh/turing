"""chat_pipe.py: the JSON-line protocol a native GUI drives instead of a terminal. A fake ask_fn stands in, so no
test needs a real model; a separate live test drives the real subprocess.

Run: python3 test_chat_pipe.py
"""
import json
import os
import subprocess
import sys
import unittest

os.environ["SAMANTHA_HEADLESS"] = "1"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chat_pipe


def drive(inputs, ask_fn):
    """Run the protocol loop over a fixed list of input lines, return every line it wrote."""
    lines = iter(inputs)
    got = []
    chat_pipe.run(lambda: next(lines, None), got.append, ask_fn)
    return got


class Protocol(unittest.TestCase):
    """The loop itself: working lines, the confirm round trip, and always exactly one final answer."""

    def test_a_plain_answer(self):
        """One ask, one answer, no confirm round trip when the tool never asks for one."""
        got = drive([json.dumps({"ask": "hi"})], lambda q, log, confirm: "hello")
        self.assertEqual(got, [{"answer": "hello"}])

    def test_working_lines_precede_the_confirm(self):
        """Every log() call becomes its own working line, in order, before the confirm."""
        def ask_fn(q, log, confirm):
            """Two working lines, then a confirmed step, then done."""
            log("open_app(chrome)")
            log("read_page(x)")
            confirm("close_tab", ())
            return "done"
        got = drive([json.dumps({"ask": "go"}), json.dumps({"yes": True})], ask_fn)
        self.assertEqual(got, [{"working": "open_app(chrome)"}, {"working": "read_page(x)"},
                               {"confirm": {"name": "close_tab", "args": []}}, {"answer": "done"}])

    def test_a_no_is_a_real_no(self):
        """The confirm reply reaches the tool exactly as sent, true or false."""
        def ask_fn(q, log, confirm):
            """Answer depends only on what confirm() returns."""
            return "yes path" if confirm("x", ()) else "no path"
        confirm_line = {"confirm": {"name": "x", "args": []}}
        self.assertEqual(drive([json.dumps({"ask": "q"}), json.dumps({"yes": True})], ask_fn), [confirm_line, {"answer": "yes path"}])
        self.assertEqual(drive([json.dumps({"ask": "q"}), json.dumps({"yes": False})], ask_fn), [confirm_line, {"answer": "no path"}])

    def test_garbage_input_is_an_honest_answer_not_a_crash(self):
        """Bad JSON, missing 'ask', and a None answer are all handled, never an exception out of the loop."""
        got = drive(["not json", json.dumps({"nope": 1}), json.dumps({"ask": "q"})], lambda q, log, confirm: None)
        self.assertEqual(got, [{"answer": "That did not look like a question."}, {"answer": "That did not look like a question."},
                               {"answer": "That is not a command I know."}])

    def test_eof_ends_the_loop_cleanly(self):
        """No input at all: the loop returns without writing anything."""
        self.assertEqual(drive([], lambda q, log, confirm: "never"), [])

    def test_a_confirm_reply_that_is_not_json_is_a_no(self):
        """Garbage instead of a real yes/no reply is read as a refusal, never a crash."""
        def ask_fn(q, log, confirm):
            """Same as above: answer depends only on what confirm() returns."""
            return "yes" if confirm("x", ()) else "no"
        self.assertEqual(drive([json.dumps({"ask": "q"}), "not json"], ask_fn), [{"confirm": {"name": "x", "args": []}}, {"answer": "no"}])


class RealAsk(unittest.TestCase):
    """_real_ask actually reaches the same answer chain chat.py and harness.py use."""

    def test_a_command_goes_through_the_harness(self):
        """A recognisable command is answered by the harness, tool calls logged, writes confirmed."""
        logged, asked = [], []
        answer = chat_pipe._real_ask("what is 2+2", log=logged.append, confirm=lambda n, a: asked.append((n, a)) or True)
        self.assertEqual(answer, "2+2 = 4")


@unittest.skipUnless(os.environ.get("PIPE_LIVE") == "1", "PIPE_LIVE=1 drives the real subprocess with the real model")
class Live(unittest.TestCase):
    """The real thing: a real subprocess, real stdin/stdout, a real answer and a real confirm."""

    def test_a_real_turn_and_a_real_confirm(self):
        """An arithmetic question answers directly; a note asks first, and a no is honored."""
        p = subprocess.Popen([sys.executable, "-u", "chat_pipe.py"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
        try:
            p.stdin.write(json.dumps({"ask": "what is 2+2"}) + "\n"); p.stdin.flush()
            self.assertEqual(json.loads(p.stdout.readline()), {"answer": "2+2 = 4"})
            p.stdin.write(json.dumps({"ask": "take a note buy milk"}) + "\n"); p.stdin.flush()
            self.assertIn("new_note", json.loads(p.stdout.readline())["working"])
            self.assertEqual(json.loads(p.stdout.readline())["confirm"]["name"], "new_note")
            p.stdin.write(json.dumps({"yes": False}) + "\n"); p.stdin.flush()
            self.assertEqual(json.loads(p.stdout.readline()), {"answer": "Okay, I will not."})
        finally:
            p.terminate()


if __name__ == "__main__":
    unittest.main()
