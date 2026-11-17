"""tools_video.py: compress_video and still_frame, with subprocess mocked so ffmpeg is never run (split from test_video.py)."""
import os
import subprocess
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_video import Base, tools_files, tools_video  # noqa: E402


class Still(Base):
    """still_frame: one frame of a video as <name>-frame.png beside it."""

    def test_routes(self):
        """With and without a time, and the screenshot phrasing; a plain screenshot is not a video."""
        def route(q):
            """The (tool, argument) the video routes give q, or None."""
            for pat, name, arg in tools_video.ROUTES:
                m = pat.match(q)
                if m and name == "still_frame":
                    return arg(m)
        self.assertEqual(route("grab a still from ~/Movies/a.mp4 at 0:12"), "~/Movies/a.mp4\t0:12")
        self.assertEqual(route("save a frame of my ~/a.mov"), "~/a.mov")
        self.assertEqual(route("screenshot ~/a.mp4 at 30"), "~/a.mp4\t30")
        self.assertIsNone(route("take a screenshot"))

    def test_refusals_and_run(self):
        """Hidden files, bad times and an existing frame are plain replies; a live run seeks first and moves the .part file into place."""
        with mock.patch.object(tools_video.subprocess, "run") as run:
            self.assertIn("allowed", tools_video.still_frame(os.path.join(tools_files.HOME, ".hidden", "secret.mp4")))
            self.assertIn("like 0:12", tools_video.still_frame(self.clip + "\trm -rf"))
            self.assertEqual(tools_video.still_frame(self.clip + "\t0:12"), "Saved the frame at 0:12 as ~/Movies/a-frame.png.")
        run.assert_not_called()

        def fake(cmd, **kw):
            """A stand-in that writes the frame the way ffmpeg would."""
            open(cmd[-1], "wb").write(b"png")
            return subprocess.CompletedProcess(cmd, 0, stdout=b"", stderr=b"")
        with mock.patch.object(tools_files, "HEADLESS", False), mock.patch.object(tools_video, "_exe", return_value="ffmpeg"), \
                mock.patch.object(tools_video.subprocess, "run", side_effect=fake) as run:
            self.assertEqual(tools_video.still_frame(self.clip + "\t0:12"), "Saved the frame at 0:12 as ~/Movies/a-frame.png.")
            self.assertEqual(tools_video.still_frame(self.clip), "~/Movies/a-frame.png already exists.")
        cmd = run.call_args[0][0]
        self.assertLess(cmd.index("-ss"), cmd.index("-i"))
        self.assertFalse(os.path.exists(os.path.join(tools_files.HOME, "Movies", "a-frame.part.png")))


class Compress(Base):
    """compress_video: a smaller copy of a video, <name>-small.mp4 beside it."""

    def test_route_and_refusals(self):
        """Both phrasings route; a hidden file and an existing copy are plain replies; "compress my files" is not a video."""
        routes = [r for r in tools_video.ROUTES if r[1] == "compress_video"]
        self.assertEqual(len(routes), 2)
        self.assertEqual(routes[0][2](routes[0][0].match("compress my ~/Movies/a.mp4")), "~/Movies/a.mp4")
        self.assertEqual(routes[1][2](routes[1][0].match("make ~/a.mov smaller")), "~/a.mov")
        self.assertFalse(any(r[0].match("compress my files") for r in routes))
        with mock.patch.object(tools_video.subprocess, "run") as run:
            self.assertIn("allowed", tools_video.compress_video(os.path.join(tools_files.HOME, ".hidden", "secret.mp4")))
            open(os.path.join(tools_files.HOME, "Movies", "a-small.mp4"), "wb").close()
            self.assertEqual(tools_video.compress_video(self.clip), "~/Movies/a-small.mp4 already exists.")
        run.assert_not_called()

    def test_headless_and_run(self):
        """Headless runs nothing; a live run caps the width, sets a quality, and reports both sizes."""
        with mock.patch.object(tools_video.subprocess, "run") as run:
            self.assertEqual(tools_video.compress_video(self.clip), "Made a smaller copy at ~/Movies/a-small.mp4.")
        run.assert_not_called()

        def fake(cmd, **kw):
            """A stand-in that writes a small output the way ffmpeg would."""
            open(cmd[-1], "wb").write(b"x")
            return subprocess.CompletedProcess(cmd, 0, stdout=b"", stderr=b"")
        with mock.patch.object(tools_files, "HEADLESS", False), mock.patch.object(tools_video, "_exe", return_value="ffmpeg"), \
                mock.patch.object(tools_video.subprocess, "run", side_effect=fake) as run:
            reply = tools_video.compress_video(self.clip)
        self.assertTrue(reply.startswith("Made a smaller copy at ~/Movies/a-small.mp4: "), reply)
        self.assertIn("down to", reply)
        cmd = run.call_args[0][0]
        self.assertIn("scale='min(1280,iw)':-2", cmd)
        self.assertIn("-crf", cmd)


if __name__ == "__main__":
    unittest.main()
