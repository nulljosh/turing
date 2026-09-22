"""Asking questions about documents and the screen, with the reader model faked. No Ollama, no screenshot."""
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

os.environ["SAMANTHA_HEADLESS"] = "1"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tools
import tools_util as u

DOC = "The wifi is on the fridge. The dog is called Biscuit and he eats at six. The car is blue."


def reply(text):
    """A fake Ollama response carrying this message."""
    return io.BytesIO(json.dumps({"message": {"content": text}}).encode())


class ReaderTests(unittest.TestCase):
    """Grounding, declining, the no-model fallback, retrieval on long text, and privacy."""

    def setUp(self):
        """A text file in a visible folder under home."""
        self.dir = tempfile.mkdtemp(dir=os.path.expanduser("~"), prefix="samantha-reader-test-")
        self.path = os.path.join(self.dir, "pets.txt")
        open(self.path, "w").write(DOC)

    def tearDown(self):
        """Remove the folder."""
        shutil.rmtree(self.dir, ignore_errors=True)

    def ask(self, question, answer):
        """Ask about the document with the model answering as told."""
        with mock.patch.object(u.urllib.request, "urlopen", return_value=reply(answer)):
            return u.ask_document(question + "\t" + self.path)

    def test_a_grounded_answer_comes_back(self):
        """An answer whose facts are in the document is returned."""
        self.assertEqual(self.ask("what is the dog called", "The dog is called Biscuit."), "The dog is called Biscuit.")

    def test_an_invented_fact_is_declined(self):
        """A number or name that is not in the document means she says she could not find it."""
        self.assertEqual(self.ask("what is the dog called", "The dog is called Rex."), "I could not find that in the document.")
        self.assertEqual(self.ask("when does he eat", "He eats at 9 o'clock."), "I could not find that in the document.")

    def test_unknown_is_declined(self):
        """The reader saying UNKNOWN is a decline, not an answer."""
        self.assertEqual(self.ask("what is the cat called", "UNKNOWN"), "I could not find that in the document.")

    def test_no_ollama_falls_back_to_passages(self):
        """With no model she says so and hands back the closest passages."""
        with mock.patch.object(u.urllib.request, "urlopen", side_effect=OSError("down")):
            out = u.ask_document("dog\t" + self.path)
        self.assertIn("needs Ollama", out)
        self.assertIn("Biscuit", out)

    def test_bad_paths_and_empty_questions(self):
        """Hidden files, outside paths and blank questions are refused in words."""
        self.assertIn("allowed to read", u.ask_document("what\t~/.ssh/id_rsa"))
        self.assertIn("allowed to read", u.ask_document("what\t/etc/passwd"))
        self.assertEqual(u.ask_document("  \t" + self.path), "Ask me something about the document.")

    def test_long_text_is_narrowed_to_the_relevant_passages(self):
        """A long document is cut down to the sentences that share words with the question."""
        filler = " ".join(f"Sentence number {i} is about nothing at all." for i in range(400))
        text = filler + " The dog is called Biscuit. " + filler
        got = u._passages(text, "what is the dog called", limit=1000)
        self.assertLessEqual(len(got), 1100)
        self.assertIn("Biscuit", got)

    def test_the_screen_answers_from_ocr_text(self):
        """A screen question runs the OCR text through the same grounded reader."""
        with mock.patch.object(u, "HEADLESS", False), mock.patch.object(u, "read_screen", return_value="Total | 42 dollars | Due Friday"), \
                mock.patch.object(u.urllib.request, "urlopen", return_value=reply("The total is 42 dollars.")):
            self.assertEqual(u.ask_screen("what is the total"), "The total is 42 dollars.")
        with mock.patch.object(u, "HEADLESS", False), mock.patch.object(u, "read_screen", return_value="Total | 42 dollars"), \
                mock.patch.object(u.urllib.request, "urlopen", return_value=reply("The total is 99 dollars.")):
            self.assertEqual(u.ask_screen("what is the total"), "I could not find that on the screen.")

    def test_the_screen_stays_private(self):
        """Asking about the screen asks first and never reaches a model or MCP."""
        self.assertIn("ask_screen", tools.WRITES)
        self.assertIn("ask_screen", tools.NOT_FOR_MODELS)
        self.assertEqual(u.ask_screen("anything"), "Would read the screen and answer.")


if __name__ == "__main__":
    unittest.main()
