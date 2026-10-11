"""chat.py's loops and model plumbing: the terminal chat, the curses TUI, the mode switches, safe_turn, and generate()
with the model stood in. test_chat.py covers the pure text logic; this covers what it skipped.

Run: python3 tests/test_chat_loop.py
"""
import io
import os
import sys
import types
import unittest
from unittest import mock

os.environ["SAMANTHA_HEADLESS"] = "1"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app"))
import chat  # noqa: E402


class Switches(unittest.TestCase):
    """toggle and safe_turn."""

    def test_toggle(self):
        """The voice and face switches, and anything else is None."""
        self.assertEqual(chat.toggle(" /voice "), "voice")
        self.assertEqual(chat.toggle("Voice On"), "voice")
        self.assertEqual(chat.toggle("video off"), "face")
        self.assertIsNone(chat.toggle("hello"))

    def test_safe_turn_turns_a_crash_into_a_reply(self):
        """A failure in the answer chain is a sentence, with the topic and subject kept."""
        with mock.patch.object(chat, "answer_turn", side_effect=RuntimeError("model gone")):
            answer, topic, subject = chat.safe_turn("why", [], True, "tides")
        self.assertIn("RuntimeError: model gone", answer)
        self.assertEqual((topic, subject), (True, "tides"))
        with mock.patch.object(chat, "answer_turn", return_value=("fine", False, None)):
            self.assertEqual(chat.safe_turn("why", [], False, None), ("fine", False, None))


class Generate(unittest.TestCase):
    """generate() streams the model's pieces, stops at scaffold and at the sentence cap; _model() fails plainly."""

    def fake_mlx(self, pieces):
        """An mlx_lm module whose stream_generate yields these pieces."""
        m = types.ModuleType("mlx_lm")
        m.stream_generate = lambda model, tok, prompt, max_tokens=80, logits_processors=None: (types.SimpleNamespace(text=p) for p in pieces)
        m.load = lambda *a, **k: ("model", "tok")
        su = types.ModuleType("mlx_lm.sample_utils")
        su.make_logits_processors = lambda repetition_penalty=1.0: ["penalty"]
        m.sample_utils = su
        return {"mlx_lm": m, "mlx_lm.sample_utils": su}

    def test_streams_and_stops_at_two_sentences(self):
        """Pieces stream to on_text behind a hold, and generation stops once two sentences are written."""
        tok = mock.Mock()
        tok.apply_chat_template = lambda msgs, add_generation_prompt, tokenize: msgs[0]["content"]
        pieces = ["The sky ", "is blue. ", "Water is ", "wet. ", "Rocks are hard."]
        got = []
        with mock.patch.dict(sys.modules, self.fake_mlx(pieces)), mock.patch.object(chat, "_model", return_value=("m", tok)):
            text = chat.generate("why is the sky blue", on_text=got.append)
        self.assertEqual(text, "The sky is blue. Water is wet. ")
        self.assertTrue("".join(got).startswith("The sky"))
        self.assertTrue(text.startswith("".join(got)))

    def test_stops_at_echoed_scaffold_and_no_penalty_path(self):
        """An echoed "User:" marker ends the reply; REPETITION 0 skips the penalty."""
        tok = mock.Mock()
        tok.apply_chat_template = lambda msgs, add_generation_prompt, tokenize: msgs[0]["content"]
        stop = chat.STOPS[0]
        with mock.patch.dict(sys.modules, self.fake_mlx(["MIT.", stop, "never"])), mock.patch.object(chat, "_model", return_value=("m", tok)), \
                mock.patch.object(chat, "REPETITION", 0):
            self.assertEqual(chat.generate("license?"), "MIT." + stop)

    def test_model_load_failure_is_an_oserror(self):
        """No MLX means OSError with the reason, and a loaded model is kept."""
        chat._answerer = None
        with mock.patch.dict(sys.modules, {"mlx_lm": None}):
            with self.assertRaises(OSError):
                chat._model()
        with mock.patch.dict(sys.modules, self.fake_mlx([])):
            self.assertEqual(chat._model(), ("model", "tok"))
            self.assertEqual(chat._model(), ("model", "tok"))
        chat._answerer = None


class TerminalChat(unittest.TestCase):
    """chat(): commands through the harness, questions through safe_turn, the switches, and the exits."""

    def run_chat(self, lines, ask=None, turn=None):
        """Drive chat() with these input lines; returns what it printed."""
        inputs = iter(lines)
        session = mock.Mock()
        session.ask.side_effect = ask or (lambda q, or_none=True: None)
        out = io.StringIO()
        import harness
        with mock.patch("builtins.input", side_effect=lambda prompt="": next(inputs)), mock.patch.object(harness, "Session", return_value=session), \
                mock.patch.object(chat, "safe_turn", side_effect=turn or (lambda q, h, t, s, on_text=None: ("An answer.", t, s))), \
                mock.patch("sys.stdout", out):
            chat.chat()
        return out.getvalue(), session

    def test_command_question_and_exit(self):
        """A command's reply is printed and remembered; a question streams then finishes; exit ends the loop."""
        def turn(q, h, t, s, on_text=None):
            """A streamed answer: two pieces, then the whole."""
            on_text("Tides come ")
            on_text("from the Moon.")
            return "Tides come from the Moon.", True, "tides"
        printed, session = self.run_chat(["set the volume to 30", "what causes tides", "exit"],
                                         ask=lambda q, or_none=True: "Volume set." if "volume" in q else None, turn=turn)
        self.assertIn("Samantha: Volume set.", printed)
        self.assertIn("Samantha: Tides come from the Moon.", printed)
        session.record.assert_called_once_with("what causes tides", "Tides come from the Moon.")

    def test_switches_and_eof(self):
        """/voice hands off to voice.converse, /face opens then closes the window, and EOF ends the loop."""
        import voice, face
        window = mock.Mock()
        def inputs():
            """The lines, then EOF."""
            for line in ("/voice", "/face", "/face"):
                yield line
            raise EOFError
        it = inputs()
        session = mock.Mock()
        import harness
        with mock.patch("builtins.input", side_effect=lambda prompt="": next(it)), mock.patch.object(harness, "Session", return_value=session), \
                mock.patch.object(voice, "converse") as converse, mock.patch.object(face, "start", return_value=window), mock.patch("sys.stdout", io.StringIO()):
            chat.chat()
        converse.assert_called_once()
        window.shutdown.assert_called_once()
        session.ask.assert_not_called()


class Tui(unittest.TestCase):
    """tui(): the curses loop with the screen stood in."""

    def test_tui_runs_a_command_and_a_question(self):
        """Two lines typed: a command answered by the harness, a question answered by safe_turn, then exit."""
        screen = mock.Mock()
        screen.getmaxyx.return_value = (24, 80)
        screen.getstr.side_effect = [b"git status", b"what causes tides", b"exit"]
        screen.getkey.return_value = "y"
        curses = types.ModuleType("curses")
        curses.wrapper = lambda fn: fn(screen)
        curses.curs_set = curses.echo = curses.noecho = lambda *a: None
        session = mock.Mock()
        session.ask.side_effect = lambda q, or_none=True: "Clean tree." if "git" in q else None
        import harness
        with mock.patch.dict(sys.modules, {"curses": curses}), mock.patch.object(harness, "Session", return_value=session) as S, \
                mock.patch.object(chat, "safe_turn", side_effect=lambda q, h, t, s, on_text=None: (on_text("Tides.") or ("Tides.", t, s))):
            chat.tui()
        confirm, working = S.call_args[1]["confirm"], S.call_args[1]["log"]
        self.assertTrue(confirm("new_note", ["x"]))  # the y on the bottom line
        working("  new_note(x)")  # draws without error
        session.record.assert_called_once_with("what causes tides", "Tides.")
        drawn = " ".join(str(c) for c in screen.addstr.call_args_list)
        self.assertIn("Clean tree.", drawn)
        self.assertIn("Samantha: Tides.", drawn)


if __name__ == "__main__":
    unittest.main()
