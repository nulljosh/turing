"""The desk robot's pieces that need no hardware: the spoken yes, and a loop that says what she answers."""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))
os.environ["SAMANTHA_HEADLESS"] = "1"
import robot  # noqa: E402
import voice  # noqa: E402


class Robot(unittest.TestCase):
    """spoken_yes only accepts a plain yes; converse speaks her reply through the robot's mouth."""

    def test_only_a_plain_yes_confirms(self):
        """Yes, yeah and okay confirm; no, silence and an unrelated sentence do not; she asks out loud first."""
        said = []
        for heard, want in (("Yes.", True), ("yeah sure", True), ("no", False), ("", False), ("play some jazz", False)):
            confirm = robot.spoken_yes(lambda h=heard: h, said.append)
            self.assertEqual(confirm("trash_file", ("a.txt",)), want, heard)
        self.assertIn("trash file a.txt", said[0])

    def test_loop_speaks_her_answer(self):
        """One typed-in turn goes through the harness and comes out of say()."""
        said, turns = [], iter(["hello", "goodbye"])
        voice.converse(listen=lambda: next(turns), say=said.append, show=lambda *_: None, turns=2)
        self.assertTrue(any("Hi" in s for s in said), said)


if __name__ == "__main__":
    unittest.main()
