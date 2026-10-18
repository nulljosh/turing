"""tools_video.py: video_info, trim_video and vertical_video, with subprocess mocked so ffmpeg is never run.

Covers the routes, the home-only and no-hidden-files fence, the time check, the headless answer (nothing runs), the
no-overwrite rule, and a missing ffmpeg getting a plain reply. A throwaway home folder stands in for ~.

Run: python3 tests/test_video.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

os.environ["SAMANTHA_HEADLESS"] = "1"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app"))
import tools_files  # noqa: E402
import tools_video  # noqa: E402

PROBE = json.dumps({"format": {"duration": "83.4", "size": "2097152"},
                    "streams": [{"codec_type": "video", "codec_name": "h264", "width": 1920, "height": 1080}, {"codec_type": "audio", "codec_name": "aac"}]})


class Base(unittest.TestCase):
    """Each test gets a throwaway home folder with one video and one hidden video."""

    def setUp(self):
        """Point tools_files at a temp home and make the files."""
        self.home = tempfile.mkdtemp()
        self.real_home = tools_files.HOME
        tools_files.HOME = os.path.realpath(self.home)
        os.makedirs(os.path.join(tools_files.HOME, "Movies"))
        self.clip = os.path.join(tools_files.HOME, "Movies", "a.mp4")
        open(self.clip, "wb").close()
        os.makedirs(os.path.join(tools_files.HOME, ".hidden"))
        open(os.path.join(tools_files.HOME, ".hidden", "secret.mp4"), "wb").close()

    def tearDown(self):
        """Restore the real home and delete the temp one."""
        tools_files.HOME = self.real_home
        shutil.rmtree(self.home, ignore_errors=True)


class Routes(unittest.TestCase):
    """The exact phrases hand each tool its argument."""

    def route(self, text):
        """(tool, argument) for the first ROUTES pattern that matches, or (None, None)."""
        for pat, name, arg in tools_video.ROUTES:
            m = pat.match(text)
            if m:
                return name, arg(m)
        return None, None

    def test_each_phrase(self):
        """info, trim and both vertical phrasings route; plain talk does not."""
        self.assertEqual(self.route("how long is ~/Movies/a.mov"), ("video_info", "~/Movies/a.mov"))
        self.assertEqual(self.route("trim ~/Movies/a.mp4 from 0:10 to 0:25"), ("trim_video", "~/Movies/a.mp4\t0:10\t0:25"))
        self.assertEqual(self.route("make ~/a.mp4 vertical"), ("vertical_video", "~/a.mp4"))
        self.assertEqual(self.route("make a vertical version of my ~/a.mp4"), ("vertical_video", "~/a.mp4"))
        for text in ("how long is the movie", "trim my hedge", "make dinner vertical", "cut ~/notes.txt from 1 to 2"):
            self.assertEqual(self.route(text), (None, None), text)


class Fence(Base):
    """Outside home, hidden and non-video paths are refused and nothing runs."""

    def test_refusals(self):
        """Every tool says it is not allowed and never starts a process."""
        with mock.patch.object(tools_video.subprocess, "run") as run:
            self.assertIn("allowed", tools_video.video_info("/etc/a.mp4"))
            self.assertIn("allowed", tools_video.video_info("~/.hidden/secret.mp4"))
            self.assertIn("allowed", tools_video.video_info("~/Movies/notes.txt"))
            self.assertIn("allowed", tools_video.trim_video("~/.hidden/secret.mp4\t0:01\t0:09"))
            self.assertIn("allowed", tools_video.vertical_video("~/../../etc/a.mp4"))
        run.assert_not_called()

    def test_bad_times_and_shape(self):
        """Odd times and a missing time are turned away before ffmpeg."""
        with mock.patch.object(tools_video.subprocess, "run") as run:
            self.assertIn("times", tools_video.trim_video(self.clip + "\t0:10\trm -rf"))
            self.assertIn("which video", tools_video.trim_video(self.clip))
        run.assert_not_called()


class Info(Base):
    """video_info reads ffprobe's JSON and says one plain sentence."""

    def test_sentence(self):
        """Length, size, picture and sound come back in one line."""
        with mock.patch.object(tools_video, "_exe", return_value="ffprobe"), \
                mock.patch.object(tools_video.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, stdout=PROBE, stderr="")):
            got = tools_video.video_info(self.clip)
        self.assertEqual(got, "~/Movies/a.mp4 is 1:23 long, 2.0 MB, 1920x1080 h264, aac sound.")

    def test_plain_failures(self):
        """No ffprobe, a hang and garbage output each get a plain reply."""
        with mock.patch.object(tools_video, "_exe", return_value=None):
            self.assertEqual(tools_video.video_info(self.clip), tools_video._NO_FFMPEG)
        with mock.patch.object(tools_video, "_exe", return_value="ffprobe"), \
                mock.patch.object(tools_video.subprocess, "run", side_effect=subprocess.TimeoutExpired("ffprobe", 60)):
            self.assertEqual(tools_video.video_info(self.clip), "ffprobe did not answer.")
        with mock.patch.object(tools_video, "_exe", return_value="ffprobe"), \
                mock.patch.object(tools_video.subprocess, "run", return_value=subprocess.CompletedProcess([], 1, stdout="", stderr="")):
            self.assertIn("could not read", tools_video.video_info(self.clip))


class Writes(Base):
    """trim_video and vertical_video: headless runs nothing, never overwrite, name files beside the original."""

    def test_headless(self):
        """Headless answers with the new name and starts nothing."""
        with mock.patch.object(tools_video.subprocess, "run") as run:
            self.assertEqual(tools_video.trim_video(self.clip + "\t0:10\t0:25"), "Cut 0:10 to 0:25 into ~/Movies/a-clip.mp4.")
            self.assertEqual(tools_video.vertical_video(self.clip), "Made a vertical version at ~/Movies/a-vertical.mp4.")
        run.assert_not_called()

    def test_never_overwrites(self):
        """An existing output is left alone and ffmpeg never starts."""
        open(os.path.join(tools_files.HOME, "Movies", "a-clip.mp4"), "wb").close()
        with mock.patch.object(tools_video.subprocess, "run") as run:
            self.assertEqual(tools_video.trim_video(self.clip + "\t0:10\t0:25"), "~/Movies/a-clip.mp4 already exists.")
        run.assert_not_called()

    def test_real_run_command(self):
        """Not headless: the right ffmpeg arguments, written to a .part file then moved into place."""
        def fake(cmd, **kw):
            """A stand-in for subprocess.run that writes the output file the way ffmpeg would."""
            open(cmd[-1], "wb").write(b"x")
            return subprocess.CompletedProcess(cmd, 0, stdout=b"", stderr=b"")
        with mock.patch.object(tools_files, "HEADLESS", False), mock.patch.object(tools_video, "_exe", return_value="ffmpeg"), \
                mock.patch.object(tools_video.subprocess, "run", side_effect=fake) as run:
            got = tools_video.vertical_video(self.clip)
        cmd = run.call_args[0][0]
        self.assertEqual(got, "Made a vertical version at ~/Movies/a-vertical.mp4.")
        self.assertIn("-vf", cmd)
        self.assertIn("scale=1080:1920", cmd[cmd.index("-vf") + 1])
        self.assertTrue(os.path.exists(os.path.join(tools_files.HOME, "Movies", "a-vertical.mp4")))
        self.assertFalse(os.path.exists(os.path.join(tools_files.HOME, "Movies", "a-vertical.mp4.part.mp4")))

    def test_failures(self):
        """A bad exit leaves no partial file; no ffmpeg and a hang get plain replies."""
        with mock.patch.object(tools_files, "HEADLESS", False), mock.patch.object(tools_video, "_exe", return_value=None):
            self.assertEqual(tools_video.trim_video(self.clip + "\t1\t2"), tools_video._NO_FFMPEG)
        with mock.patch.object(tools_files, "HEADLESS", False), mock.patch.object(tools_video, "_exe", return_value="ffmpeg"), \
                mock.patch.object(tools_video.subprocess, "run", side_effect=subprocess.TimeoutExpired("ffmpeg", 900)):
            self.assertEqual(tools_video.vertical_video(self.clip), "ffmpeg did not finish.")
        with mock.patch.object(tools_files, "HEADLESS", False), mock.patch.object(tools_video, "_exe", return_value="ffmpeg"), \
                mock.patch.object(tools_video.subprocess, "run", return_value=subprocess.CompletedProcess([], 1, stdout=b"", stderr=b"")):
            self.assertIn("could not make", tools_video.vertical_video(self.clip))
        self.assertFalse(os.path.exists(os.path.join(tools_files.HOME, "Movies", "a-vertical.mp4")))


class Audio(Base):
    """trim_audio: a sound file, two times, a new file in the same format."""

    def setUp(self):
        """Add a sound file to the temp home."""
        super().setUp()
        self.song = os.path.join(tools_files.HOME, "Movies", "song.mp3")
        open(self.song, "wb").close()

    def test_route_and_refusals(self):
        """The route hands over path, start and end; a video, a hidden file, a bad time and a missing time are plain replies."""
        route = next(r for r in tools_video.ROUTES if r[1] == "trim_audio")
        m = route[0].match("cut ~/Music/a.mp3 from 0:10 to 0:25")
        self.assertEqual(route[2](m), "~/Music/a.mp3\t0:10\t0:25")
        self.assertIsNone(route[0].match("trim ~/Movies/a.mp4 from 0:10 to 0:25"))
        with mock.patch.object(tools_video.subprocess, "run") as run:
            self.assertIn("allowed", tools_video.trim_audio(self.clip + "\t1\t2"))  # a video
            self.assertIn("allowed", tools_video.trim_audio(os.path.join(tools_files.HOME, ".hidden", "x.mp3") + "\t1\t2"))
            self.assertIn("Give the times", tools_video.trim_audio(self.song + "\tsoon\t2"))
            self.assertIn("Say which", tools_video.trim_audio(self.song))
        run.assert_not_called()

    def test_headless_and_never_overwrites(self):
        """Headless names the new file and runs nothing; an existing clip is left alone."""
        with mock.patch.object(tools_video.subprocess, "run") as run:
            self.assertEqual(tools_video.trim_audio(self.song + "\t0:10\t0:25"), "Cut 0:10 to 0:25 into ~/Movies/song-clip.mp3.")
            open(os.path.join(tools_files.HOME, "Movies", "song-clip.mp3"), "wb").close()
            self.assertEqual(tools_video.trim_audio(self.song + "\t0:10\t0:25"), "~/Movies/song-clip.mp3 already exists.")
        run.assert_not_called()

    def test_real_run_command(self):
        """Not headless: ffmpeg gets the times and no picture, writes a .part file, and it moves into place."""
        def fake(cmd, **kw):
            """A stand-in that writes the output the way ffmpeg would."""
            open(cmd[-1], "wb").write(b"x")
            return subprocess.CompletedProcess(cmd, 0, stdout=b"", stderr=b"")
        with mock.patch.object(tools_files, "HEADLESS", False), mock.patch.object(tools_video, "_exe", return_value="ffmpeg"), \
                mock.patch.object(tools_video.subprocess, "run", side_effect=fake) as run:
            got = tools_video.trim_audio(self.song + "\t2\t5")
        cmd = run.call_args[0][0]
        self.assertEqual(got, "Cut 2 to 5 into ~/Movies/song-clip.mp3.")
        self.assertEqual((cmd[cmd.index("-ss") + 1], cmd[cmd.index("-to") + 1], "-vn" in cmd), ("2", "5", True))
        self.assertTrue(os.path.exists(os.path.join(tools_files.HOME, "Movies", "song-clip.mp3")))
        self.assertFalse(os.path.exists(os.path.join(tools_files.HOME, "Movies", "song-clip.part.mp3")))

    def test_failures(self):
        """No ffmpeg, a hang and a bad exit are plain replies and leave no partial file."""
        with mock.patch.object(tools_files, "HEADLESS", False), mock.patch.object(tools_video, "_exe", return_value=None):
            self.assertEqual(tools_video.trim_audio(self.song + "\t1\t2"), tools_video._NO_FFMPEG)
        with mock.patch.object(tools_files, "HEADLESS", False), mock.patch.object(tools_video, "_exe", return_value="ffmpeg"), \
                mock.patch.object(tools_video.subprocess, "run", side_effect=subprocess.TimeoutExpired("ffmpeg", 300)):
            self.assertEqual(tools_video.trim_audio(self.song + "\t1\t2"), "ffmpeg did not finish.")
        with mock.patch.object(tools_files, "HEADLESS", False), mock.patch.object(tools_video, "_exe", return_value="ffmpeg"), \
                mock.patch.object(tools_video.subprocess, "run", return_value=subprocess.CompletedProcess([], 1, stdout=b"", stderr=b"")):
            self.assertIn("could not cut", tools_video.trim_audio(self.song + "\t1\t2"))
        self.assertFalse(os.path.exists(os.path.join(tools_files.HOME, "Movies", "song-clip.mp3")))


class Extract(Base):
    """extract_audio: the sound out of a video, into a new mp3, m4a or wav beside it."""

    def test_route_and_refusals(self):
        """The route defaults to mp3; a non-video, a hidden file and a wrong format are plain replies and run nothing."""
        route = next(r for r in tools_video.ROUTES if r[1] == "extract_audio")
        self.assertEqual(route[2](route[0].match("extract the audio from ~/Movies/a.mp4")), "~/Movies/a.mp4\tmp3")
        self.assertEqual(route[2](route[0].match("pull the sound out of my ~/a.mov as a wav")), "~/a.mov\twav")
        with mock.patch.object(tools_video.subprocess, "run") as run:
            self.assertIn("allowed", tools_video.extract_audio(os.path.join(tools_files.HOME, ".hidden", "secret.mp4") + "\tmp3"))
            self.assertIn("not ogg", tools_video.extract_audio(self.clip + "\togg"))
            self.assertIn("not nothing", tools_video.extract_audio(self.clip))
            open(os.path.join(tools_files.HOME, "Movies", "a.mp3"), "wb").close()
            self.assertEqual(tools_video.extract_audio(self.clip + "\tmp3"), "~/Movies/a.mp3 already exists.")
        run.assert_not_called()

    def test_headless_and_run(self):
        """Headless names the file and runs nothing; a live run uses -vn, writes a .part file, and moves it into place."""
        with mock.patch.object(tools_video.subprocess, "run") as run:
            self.assertEqual(tools_video.extract_audio(self.clip + "\twav"), "Pulled the sound into ~/Movies/a.wav.")
        run.assert_not_called()

        def fake(cmd, **kw):
            """A stand-in that writes the output the way ffmpeg would."""
            open(cmd[-1], "wb").write(b"x")
            return subprocess.CompletedProcess(cmd, 0, stdout=b"", stderr=b"")
        with mock.patch.object(tools_files, "HEADLESS", False), mock.patch.object(tools_video, "_exe", return_value="ffmpeg"), \
                mock.patch.object(tools_video.subprocess, "run", side_effect=fake) as run:
            self.assertEqual(tools_video.extract_audio(self.clip + "\tm4a"), "Pulled the sound into ~/Movies/a.m4a.")
        self.assertIn("-vn", run.call_args[0][0])
        self.assertTrue(os.path.exists(os.path.join(tools_files.HOME, "Movies", "a.m4a")))
        self.assertFalse(os.path.exists(os.path.join(tools_files.HOME, "Movies", "a.part.m4a")))

    def test_failures(self):
        """No ffmpeg, a hang and a bad exit are plain replies and leave no file."""
        with mock.patch.object(tools_files, "HEADLESS", False), mock.patch.object(tools_video, "_exe", return_value=None):
            self.assertEqual(tools_video.extract_audio(self.clip + "\tmp3"), tools_video._NO_FFMPEG)
        with mock.patch.object(tools_files, "HEADLESS", False), mock.patch.object(tools_video, "_exe", return_value="ffmpeg"), \
                mock.patch.object(tools_video.subprocess, "run", side_effect=subprocess.TimeoutExpired("ffmpeg", 900)):
            self.assertEqual(tools_video.extract_audio(self.clip + "\tmp3"), "ffmpeg did not finish.")
        with mock.patch.object(tools_files, "HEADLESS", False), mock.patch.object(tools_video, "_exe", return_value="ffmpeg"), \
                mock.patch.object(tools_video.subprocess, "run", return_value=subprocess.CompletedProcess([], 1, stdout=b"", stderr=b"")):
            self.assertIn("could not pull", tools_video.extract_audio(self.clip + "\tmp3"))
        self.assertFalse(os.path.exists(os.path.join(tools_files.HOME, "Movies", "a.mp3")))


class Registry(unittest.TestCase):
    """The three tools are registered, documented, and the two writes ask first."""

    def test_names(self):
        """Names match TOOLS and each has a docstring."""
        self.assertEqual({f.__name__ for f in tools_video.TOOLS}, {"video_info", "trim_video", "vertical_video", "trim_audio", "extract_audio"})
        self.assertTrue(all(f.__doc__ for f in tools_video.TOOLS))
        import tools
        self.assertTrue({"video_info", "trim_video", "vertical_video", "trim_audio", "extract_audio"} <= set(tools.TOOLS))
        self.assertTrue({"trim_video", "vertical_video", "trim_audio", "extract_audio"} <= tools.WRITES and "video_info" not in tools.WRITES)


if __name__ == "__main__":
    unittest.main()
