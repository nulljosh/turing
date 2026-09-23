"""voice.py: what she does with what she hears. Fake ears and a fake mouth stand in, so no test needs a microphone.
VOICE_LIVE=1 also renders a question with macOS `say` and transcribes it with the real Whisper.

Run: python3 tests/test_voice.py
"""
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

os.environ["SAMANTHA_HEADLESS"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import voice


class Heard(unittest.TestCase):
    """Silence, Whisper's phantoms, goodbyes and real questions."""

    def test_sorting(self):
        """Each transcript lands in the right bucket."""
        for text in ("", "  ", "Thank you.", "you", "...", "[BLANK_AUDIO]", "(music)"):
            self.assertEqual(voice.heard(text), ("nothing", None), text)
        for text in ("Goodbye.", "bye", "stop listening", "That's all!"):
            self.assertEqual(voice.heard(text), ("stop", None), text)
        self.assertEqual(voice.heard(" What is 2 plus 2? "), ("ask", "What is 2 plus 2?"))
        self.assertEqual(voice.heard("goodbye to my old laptop, what should I buy"), ("ask", "goodbye to my old laptop, what should I buy"))


class Converse(unittest.TestCase):
    """The loop: every heard question goes through the harness and the answer chain, and the answer is said aloud."""

    def run_loop(self, transcripts, **kw):
        """Run the loop over scripted transcripts; returns (answered, said, shown)."""
        said, shown, queue = [], [], list(transcripts)
        answered = voice.converse(listen=lambda: queue.pop(0), say=said.append, show=shown.append, turns=len(transcripts), **kw)
        return answered, said, shown

    def test_a_question_is_answered_and_spoken(self):
        """A tool question is answered by the harness, shown, and said."""
        answered, said, shown = self.run_loop(["what is 2 plus 2"])
        self.assertEqual(answered, 1)
        self.assertIn("4", said[0])
        self.assertIn("You: what is 2 plus 2", shown)

    def test_silence_is_skipped_and_goodbye_stops(self):
        """Silence answers nothing; goodbye says bye and ends the loop before later turns."""
        answered, said, _ = self.run_loop(["", "Thank you.", "goodbye", "what is 2 plus 2"])
        self.assertEqual((answered, said), (0, ["Bye."]))

    def test_no_microphone_is_a_sentence(self):
        """listen() returning None (no sox, no mic) ends with a plain reason, not a crash."""
        answered, said, shown = self.run_loop([None])
        self.assertEqual(answered, 0)
        self.assertIn("install sox", shown[-1])

    def test_record_without_sox(self):
        """No rec binary: record says so by returning False."""
        with mock.patch("shutil.which", return_value=None):
            self.assertFalse(voice.record("/tmp/x.wav"))


@unittest.skipUnless(os.environ.get("VOICE_LIVE") == "1" and sys.platform == "darwin", "VOICE_LIVE=1 on a Mac runs the real Whisper")
class Live(unittest.TestCase):
    """The real ears: macOS says a question into a file, Whisper writes it back."""

    def test_she_hears_a_spoken_question(self):
        """'What is two plus two?' comes back as those words."""
        with tempfile.TemporaryDirectory() as d:
            aiff, wav = os.path.join(d, "q.aiff"), os.path.join(d, "q.wav")
            subprocess.run(["say", "-o", aiff, "What is two plus two?"], check=True)
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", aiff, "-ar", "16000", "-ac", "1", wav], check=True)
            text = voice.transcribe(wav).lower()
        self.assertTrue("2 plus 2" in text or "two plus two" in text, text)


if __name__ == "__main__":
    unittest.main()
