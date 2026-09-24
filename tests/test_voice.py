"""voice.py: what she does with what she hears. Fake ears and a fake mouth stand in, so no test needs a microphone.
VOICE_LIVE=1 also renders a question with macOS `say` and transcribes it with the real Whisper.

Run: python3 tests/test_voice.py
"""
import os
import struct
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


class WakeWord(unittest.TestCase):
    """Matching a transcript against the wake word, pure, no audio."""

    def test_matches_with_and_without_a_comma_or_case(self):
        """"samantha, what time is it" and "Samantha what time is it" both match, the word gone from the rest."""
        matched, rest = voice.wake_match("samantha, what time is it")
        self.assertEqual((matched, rest), (True, "what time is it"))
        matched, rest = voice.wake_match("Samantha what time is it")
        self.assertEqual((matched, rest), (True, "what time is it"))

    def test_a_prefix_of_the_word_never_matches(self):
        """"sam what time" never matches: the wake word must stand whole, not as someone else's prefix."""
        self.assertEqual(voice.wake_match("sam what time"), (False, None))

    def test_the_word_alone_is_a_match_with_nothing_left(self):
        """Just the wake word, nothing after it: a match with an empty command."""
        self.assertEqual(voice.wake_match("samantha"), (True, ""))

    def test_a_named_word_is_honored(self):
        """A different word= is used instead of the default, and only that word matches."""
        self.assertEqual(voice.wake_match("computer, lights on", word="computer"), (True, "lights on"))
        self.assertEqual(voice.wake_match("samantha, lights on", word="computer"), (False, None))


class BargeIn(unittest.TestCase):
    """The pure decision behind cutting her off: energy per chunk in, a bool out, no audio needed."""

    def test_quiet_samples_never_interrupt(self):
        """Room-noise-level energy readings never trigger a barge-in."""
        self.assertFalse(voice.should_barge_in([10, 50, 20, 5, 0]))

    def test_a_single_loud_click_is_not_a_run(self):
        """One loud chunk surrounded by quiet ones is a click, not someone talking."""
        self.assertFalse(voice.should_barge_in([10, 5000, 10, 10]))

    def test_a_real_run_of_loud_chunks_interrupts(self):
        """Two or more consecutive loud chunks is a real run: that's a barge-in."""
        self.assertTrue(voice.should_barge_in([10, 20, 3000, 3200, 10]))

    def test_empty_levels_never_interrupt(self):
        """No samples yet: nothing to interrupt on."""
        self.assertFalse(voice.should_barge_in([]))

    def test_chunk_energy_of_silence_and_a_loud_tone(self):
        """RMS of empty and silent PCM is 0; a loud tone clears the barge-in threshold."""
        silence = b"\x00\x00" * 4000
        loud = struct.pack("<4000h", *([30000, -30000] * 2000))
        self.assertEqual(voice._chunk_energy(b""), 0)
        self.assertEqual(voice._chunk_energy(silence), 0)
        self.assertGreater(voice._chunk_energy(loud), voice.BARGE_THRESHOLD)

    def test_speak_never_opens_the_mic_when_headless(self):
        """SAMANTHA_HEADLESS=1 (set for every test in this file): no `say`, no mic, just a plain False."""
        with mock.patch("subprocess.Popen") as popen:
            self.assertFalse(voice.speak("hello"))
            popen.assert_not_called()


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

    def test_wake_off_by_default_answers_everything(self):
        """No wake= passed: every transcript is a command, exactly today's behavior, no gating at all."""
        answered, said, _ = self.run_loop(["what is 2 plus 2"])
        self.assertEqual(answered, 1)
        self.assertIn("4", said[0])

    def test_wake_word_gates_what_gets_answered(self):
        """With wake set, a transcript that doesn't start with it is ignored; one that does loses the word."""
        answered, said, shown = self.run_loop(
            ["what is 2 plus 2", "samantha, what is 2 plus 2"], wake="samantha")
        self.assertEqual(answered, 1)
        self.assertIn("4", said[0])
        self.assertIn("You: what is 2 plus 2", shown)

    def test_wake_word_case_insensitive_and_stripped(self):
        """A capitalized wake word still matches and is stripped before the rest goes to the harness."""
        answered, said, shown = self.run_loop(["Samantha what is 2 plus 2"], wake="samantha")
        self.assertEqual(answered, 1)
        self.assertIn("You: what is 2 plus 2", shown)


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
