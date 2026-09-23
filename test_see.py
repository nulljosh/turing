"""tools_see.py: her eyes. The vision model and the screenshot are stood in for, so no test needs MLX or a screen.

Run: python3 test_see.py
"""
import os
import sys
import tempfile
import unittest
from unittest import mock

os.environ["SAMANTHA_HEADLESS"] = "1"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harness
import tools
import tools_see


class Looking(unittest.TestCase):
    """What she says back, with the model stood in for."""

    def setUp(self):
        """A real picture file inside the home folder, and not headless, so the tools really try to look."""
        self.dir = tempfile.TemporaryDirectory(dir=os.path.expanduser("~"), prefix="samantha-see-test-")
        self.png = os.path.join(self.dir.name, "cat.png")
        with open(self.png, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n" + b"\0" * 64)
        self.env = mock.patch.dict(os.environ, {"SAMANTHA_HEADLESS": "0"})
        self.env.start()

    def tearDown(self):
        """Put things back."""
        self.env.stop()
        self.dir.cleanup()

    def test_a_picture_is_looked_at_with_the_question(self):
        """see_image hands the file and the question to the model and returns what it said."""
        with mock.patch.object(tools_see, "look", return_value="A grey cat on a sofa.") as look:
            self.assertEqual(tools_see.see_image("what animal is this\t" + self.png), "A grey cat on a sofa.")
        look.assert_called_once_with(self.png, "what animal is this")

    def test_what_she_will_not_look_at(self):
        """Outside home, hidden, missing, and not a picture: each a sentence, the model never called."""
        txt = os.path.join(self.dir.name, "notes.txt")
        open(txt, "w").close()
        with mock.patch.object(tools_see, "look", side_effect=AssertionError("looked")):
            self.assertIn("do not see a picture", tools_see.see_image("/etc/hosts"))
            self.assertIn("do not see a picture", tools_see.see_image(os.path.join(self.dir.name, "nope.png")))
            self.assertIn("not a picture", tools_see.see_image(txt))

    def test_no_model_and_a_broken_model(self):
        """No mlx-vlm is an install hint; any other failure is a sentence, never a crash."""
        with mock.patch.object(tools_see, "look", side_effect=OSError("vision model unavailable")):
            self.assertIn("pip install mlx-vlm", tools_see.see_image(self.png))
        with mock.patch.object(tools_see, "look", side_effect=RuntimeError("bad image")):
            self.assertIn("could not look at that: bad image", tools_see.see_image(self.png))
        with mock.patch.object(tools_see, "look", return_value="  "):
            self.assertIn("could not make anything out", tools_see.see_image(self.png))

    def test_the_screen(self):
        """see_screen captures the screen, looks at it with the question, and removes the capture."""
        shots = []

        def capture(argv, **kw):
            """Stand in for screencapture: write a small file where it was told to."""
            shots.append(argv[-1])
            with open(argv[-1], "wb") as f:
                f.write(b"png")
        with mock.patch("subprocess.run", side_effect=capture), mock.patch.object(tools_see, "look", return_value="A chart.") as look:
            self.assertEqual(tools_see.see_screen("what's wrong with this chart"), "A chart.")
        look.assert_called_once_with(shots[0], "what's wrong with this chart")
        self.assertFalse(os.path.exists(shots[0]))


class OnlyWithAYes(unittest.TestCase):
    """Private: asked first, never on a model's menu, reached by the phrasings people use."""

    def test_asked_first_and_hidden(self):
        """A no looks at nothing; both tools are writes and hidden from models and MCP."""
        with mock.patch.object(tools_see, "see_screen", side_effect=AssertionError("looked")):
            no = harness.Session(confirm=lambda n, a: False, log=lambda l: None).ask("look at my screen")
        self.assertEqual(no, "Okay, I will not.")
        self.assertLessEqual({"see_screen", "see_image"}, tools.WRITES & tools.NOT_FOR_MODELS)

    def test_routes(self):
        """Seeing is by name; reading the screen's text stays with read_screen."""
        self.assertEqual(tools.plan("look at my screen and tell me what's wrong with this chart"),
                         [("see_screen", ("tell me what's wrong with this chart",))])
        self.assertEqual(tools.plan("describe ~/Desktop/cat.png"), [("see_image", ("\t~/Desktop/cat.png",))])
        self.assertEqual(tools.plan("what's on my screen"), [("read_screen", ("",))])


if __name__ == "__main__":
    unittest.main()
