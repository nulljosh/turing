"""tools_see.py: her eyes. The vision model and the screenshot are stood in for, so no test needs MLX or a screen.

Run: python3 tests/test_see.py
"""
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

os.environ["SAMANTHA_HEADLESS"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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


class Camera(unittest.TestCase):
    """see_camera: one frame from ffmpeg's avfoundation, handed to the same vision model see_image uses, then
    deleted. Never the pseudo screen-capture device ffmpeg always lists alongside a real camera."""

    DEVICES = ("[AVFoundation indev @ 0x0] AVFoundation video devices:\n"
               "[AVFoundation indev @ 0x0] [0] Capture screen 0\n"
               "[AVFoundation indev @ 0x0] [1] FaceTime HD Camera\n"
               "[AVFoundation indev @ 0x0] AVFoundation audio devices:\n"
               "[AVFoundation indev @ 0x0] [0] Yeti Stereo Microphone\n")
    NO_CAMERA = ("[AVFoundation indev @ 0x0] AVFoundation video devices:\n"
                 "[AVFoundation indev @ 0x0] [0] Capture screen 0\n"
                 "[AVFoundation indev @ 0x0] AVFoundation audio devices:\n")

    def setUp(self):
        """Not headless, so the tool really tries the camera."""
        self.env = mock.patch.dict(os.environ, {"SAMANTHA_HEADLESS": "0"})
        self.env.start()

    def tearDown(self):
        """Put things back."""
        self.env.stop()

    def _run(self, devices, capture=None):
        """A subprocess.run stand-in: -list_devices answers with `devices`, any other call runs `capture`."""
        def run(argv, **kw):
            """Answer -list_devices with `devices`, or run `capture` for the frame-grab call."""
            r = mock.Mock()
            if "-list_devices" in argv:
                r.stdout, r.stderr = "", devices
                return r
            if capture:
                return capture(argv, **kw)
            return r
        return run

    def test_takes_one_photo_and_answers(self):
        """The real camera (index 1, never the screen at 0) is picked, looked at with the question, then removed."""
        shots = []

        def capture(argv, **kw):
            """Stand in for ffmpeg's frame grab: check the real camera was picked, then write a small file."""
            self.assertEqual(argv[argv.index("-i") + 1], "1")
            shots.append(argv[-1])
            with open(argv[-1], "wb") as f:
                f.write(b"jpg")
            return mock.Mock()
        with mock.patch("subprocess.run", side_effect=self._run(self.DEVICES, capture)), \
                mock.patch.object(tools_see, "look", return_value="A coffee mug.") as look:
            self.assertEqual(tools_see.see_camera("what am I holding"), "A coffee mug.")
        look.assert_called_once_with(shots[0], "what am I holding")
        self.assertFalse(os.path.exists(shots[0]))

    def test_no_ffmpeg(self):
        """Missing ffmpeg is a plain sentence, never a crash."""
        with mock.patch("subprocess.run", side_effect=FileNotFoundError()):
            self.assertIn("ffmpeg", tools_see.see_camera())

    def test_no_camera(self):
        """Only the screen-capture pseudo-device is not a camera."""
        with mock.patch("subprocess.run", side_effect=self._run(self.NO_CAMERA)):
            self.assertIn("do not see a camera", tools_see.see_camera())

    def test_empty_frame_is_a_permission_hint(self):
        """ffmpeg ran but wrote nothing (a swallowed permission prompt): a sentence, not a crash."""
        with mock.patch("subprocess.run", side_effect=self._run(self.DEVICES)):
            self.assertIn("could not take a photo", tools_see.see_camera())

    def test_capture_timeout_is_a_permission_hint(self):
        """ffmpeg hanging on a permission dialog times out instead of freezing the conversation."""
        def capture(argv, **kw):
            """Stand in for a frame grab stuck behind a camera permission dialog: it never returns."""
            raise subprocess.TimeoutExpired(cmd=argv, timeout=15)
        with mock.patch("subprocess.run", side_effect=self._run(self.DEVICES, capture)):
            self.assertIn("permission", tools_see.see_camera())

    def test_frame_removed_even_when_looking_fails(self):
        """The photo is deleted whether or not the vision model can make sense of it."""
        shots = []

        def capture(argv, **kw):
            """Stand in for ffmpeg's frame grab: write a small file, same as a real photo."""
            shots.append(argv[-1])
            with open(argv[-1], "wb") as f:
                f.write(b"jpg")
            return mock.Mock()
        with mock.patch("subprocess.run", side_effect=self._run(self.DEVICES, capture)), \
                mock.patch.object(tools_see, "look", side_effect=RuntimeError("bad frame")):
            self.assertIn("could not look at that", tools_see.see_camera())
        self.assertFalse(os.path.exists(shots[0]))

    def test_headless_never_touches_the_camera(self):
        """Headless answers without ever calling ffmpeg."""
        with mock.patch.dict(os.environ, {"SAMANTHA_HEADLESS": "1"}), \
                mock.patch("subprocess.run", side_effect=AssertionError("touched the camera")):
            self.assertEqual(tools_see.see_camera(), "Would take one photo with the camera.")


class OnlyWithAYes(unittest.TestCase):
    """Private: asked first, never on a model's menu, reached by the phrasings people use."""

    def test_asked_first_and_hidden(self):
        """A no looks at nothing; all three tools are writes and hidden from models and MCP."""
        with mock.patch.object(tools_see, "see_screen", side_effect=AssertionError("looked")):
            no = harness.Session(confirm=lambda n, a: False, log=lambda l: None).ask("look at my screen")
        self.assertEqual(no, "Okay, I will not.")
        with mock.patch.object(tools_see, "see_camera", side_effect=AssertionError("looked")):
            no = harness.Session(confirm=lambda n, a: False, log=lambda l: None).ask("what am I holding")
        self.assertEqual(no, "Okay, I will not.")
        self.assertLessEqual({"see_screen", "see_image", "see_camera"}, tools.WRITES & tools.NOT_FOR_MODELS)

    def test_routes(self):
        """Seeing is by name; reading the screen's text stays with read_screen."""
        self.assertEqual(tools.plan("look at my screen and tell me what's wrong with this chart"),
                         [("see_screen", ("tell me what's wrong with this chart",))])
        self.assertEqual(tools.plan("describe ~/Desktop/cat.png"), [("see_image", ("\t~/Desktop/cat.png",))])
        self.assertEqual(tools.plan("what's on my screen"), [("read_screen", ("",))])

    def test_camera_routes(self):
        """The three camera phrasings from the roadmap, plus a named-camera catch-all."""
        self.assertEqual(tools.plan("what am I holding"), [("see_camera", ("what am I holding",))])
        self.assertEqual(tools.plan("read this label"), [("see_camera", ("read this label",))])
        self.assertEqual(tools.plan("look at this"), [("see_camera", ("describe what you see",))])
        self.assertEqual(tools.plan("use the camera"), [("see_camera", ("describe what you see",))])


if __name__ == "__main__":
    unittest.main()
