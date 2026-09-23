"""Her memory across sessions: a file on this Mac, private, asks before it changes."""
import os
import sys
import tempfile
import unittest

os.environ["SAMANTHA_HEADLESS"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import harness
import tools
import tools_util as u


class MemoryTests(unittest.TestCase):
    """Remember, recall and forget against a temporary file, and the promises around them."""

    def setUp(self):
        """Point her memory at an empty temporary file."""
        self.path = os.path.join(tempfile.mkdtemp(), "memory.json")
        os.environ["SAMANTHA_MEMORY"] = self.path

    def tearDown(self):
        """Put the environment back."""
        os.environ.pop("SAMANTHA_MEMORY", None)

    def test_it_survives_a_new_session(self):
        """A fact written now is found by a fresh read of the file."""
        self.assertEqual(u.remember("my dog is called Biscuit"), "Remembered: my dog is called Biscuit")
        self.assertEqual(u.recall("what is my dog called"), "my dog is called Biscuit")
        self.assertTrue(os.path.exists(self.path))

    def test_repeats_and_blanks(self):
        """The same fact twice is stored once, and nothing is stored for nothing."""
        u.remember("the wifi is on the fridge")
        self.assertEqual(u.remember("The WIFI is on the fridge"), "I already know that.")
        self.assertEqual(u.remember("   "), "Tell me what to remember.")
        self.assertEqual(len(u._facts()), 1)

    def test_recall_ranks_and_says_when_it_knows_nothing(self):
        """The best match comes first, and an unknown subject is said plainly."""
        u.remember("my dog is called Biscuit")
        u.remember("my dog eats at six")
        u.remember("the car is blue")
        self.assertEqual(u.recall("when does my dog eat").splitlines()[0], "my dog eats at six")
        self.assertEqual(u.recall("cat"), "I do not remember anything about cat.")

    def test_forget_is_careful(self):
        """Forgetting needs words, matches every word, and refuses a wide sweep."""
        u.remember("my dog is called Biscuit")
        u.remember("my cat is called Pixel")
        self.assertEqual(u.forget(""), "Say what to forget.")
        self.assertEqual(u.forget("biscuit"), "Forgot 1 thing.")
        self.assertEqual(u.recall("dog"), "I do not remember anything about dog.")
        for i in range(7):
            u.remember(f"the number {i} is on the list")
        self.assertIn("Be more specific", u.forget("list"))
        self.assertEqual(len(u._facts()), 8)

    def test_only_the_last_500_are_kept(self):
        """The file cannot grow without end."""
        u._save([f"fact {i}" for i in range(600)])
        self.assertEqual(len(u._facts()), 500)

    def test_a_broken_file_reads_as_empty(self):
        """Garbage in the memory file is not a crash."""
        open(self.path, "w").write("{not json")
        self.assertEqual(u._facts(), [])
        self.assertEqual(u.remember("still works"), "Remembered: still works")

    def test_the_harness_asks_first_and_remembers_for_a_task(self):
        """A no writes nothing, a yes writes once, and what she remembers is found for a task."""
        s = harness.Session(confirm=lambda n, a: False, log=lambda line: None)
        self.assertEqual(s.ask("remember that my dog is called Biscuit"), "Okay, I will not.")
        self.assertFalse(os.path.exists(self.path))
        s = harness.Session(confirm=lambda n, a: True, log=lambda line: None)
        self.assertEqual(s.ask("remember that my dog is called Biscuit"), "Remembered: my dog is called Biscuit")
        self.assertEqual(u.recall_lines("my dog"), ["my dog is called Biscuit"])

    def test_it_is_private(self):
        """Nothing about memory reaches a model or MCP, and the tools are classified."""
        for name in ("remember", "recall", "forget"):
            self.assertIn(name, tools.NOT_FOR_MODELS)
            self.assertNotIn(name, tools.model_tools())
        self.assertLessEqual({"remember", "forget"}, tools.WRITES)


if __name__ == "__main__":
    unittest.main()
