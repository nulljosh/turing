"""Tests for pxm.py, part two: running osascript, verifying exports, the command line, the skill file, the build
lock, the live app and the ImageMagick painter. Split out of test_pxm.py (law 8, file size); the helpers live there.

    python3 -m unittest -v              unit tests. No Mac, no app needed. This is what CI runs.
    PXM_LIVE=1 python3 -m unittest -v   also drives the real Pixelmator Pro on this Mac.
"""
import contextlib
import fcntl
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest import mock

import pxm
from test_pxm import APP_PATH, HERE, LIVE, fake_proc, run_main, spec, setUpModule  # noqa: F401  (setUpModule: same private build lock)


class Running(unittest.TestCase):
    """Tests for running."""
    def test_success_returns_stdout(self):
        """Success returns stdout."""
        with mock.patch("subprocess.run", return_value=fake_proc(stdout="3.8\n")):
            self.assertEqual(pxm.run_applescript("x"), "3.8")

    def test_no_osascript_means_not_a_mac(self):
        """No osascript means not a mac."""
        with mock.patch("subprocess.run", side_effect=FileNotFoundError):
            with self.assertRaises(pxm.PxmError) as cm:
                pxm.run_applescript("x")
        self.assertEqual(cm.exception.code, pxm.EXIT_ENV)

    def test_hang_becomes_a_clear_error(self):
        """Hang becomes a clear error."""
        with mock.patch("subprocess.run", side_effect=subprocess.TimeoutExpired("osascript", 5)):
            with self.assertRaises(pxm.PxmError) as cm:
                pxm.run_applescript("x", timeout=5)
        self.assertIn("dialog", cm.exception.hint)

    def test_permission_denied_is_an_environment_problem(self):
        """Permission denied is an environment problem."""
        err = "0:10: execution error: Not authorized to send Apple events to Pixelmator Pro. (-1743)"
        with mock.patch("subprocess.run", return_value=fake_proc(1, stderr=err)):
            with self.assertRaises(pxm.PxmError) as cm:
                pxm.run_applescript("x")
        self.assertEqual(cm.exception.code, pxm.EXIT_ENV)
        self.assertIn("Automation", cm.exception.hint)

    def test_dropped_connection_retries_once_then_succeeds(self):
        """Dropped connection retries once then succeeds."""
        err = "execution error: Connection is invalid. (-609)"
        with mock.patch("subprocess.run",
                        side_effect=[fake_proc(1, stderr=err), fake_proc(stdout="ok")]) as run:
            self.assertEqual(pxm.run_applescript("x"), "ok")
        self.assertEqual(run.call_count, 2)

    def test_dropped_connection_gives_up_after_one_retry(self):
        """Dropped connection gives up after one retry."""
        err = "execution error: Connection is invalid. (-609)"
        with mock.patch("subprocess.run", return_value=fake_proc(1, stderr=err)) as run:
            with self.assertRaises(pxm.PxmError):
                pxm.run_applescript("x")
        self.assertEqual(run.call_count, 2)

    def test_other_errors_do_not_retry(self):
        """Other errors do not retry."""
        err = "1:2: execution error: nope (-1728)"
        with mock.patch("subprocess.run", return_value=fake_proc(1, stderr=err)) as run:
            with self.assertRaises(pxm.PxmError) as cm:
                pxm.run_applescript("x")
        self.assertEqual(run.call_count, 1)
        self.assertEqual(cm.exception.code, pxm.EXIT_SCRIPT)


class Verifying(unittest.TestCase):
    """Tests for verifying."""
    def setUp(self):
        """Set up the fixtures for each test."""
        self.spec = pxm.validate_spec(spec(background="#000"))

    def test_layer_count_matches(self):
        """Layer count matches."""
        pxm.check_result(self.spec, "layers\t2\n")

    def test_layer_count_mismatch(self):
        """Layer count mismatch."""
        for output in ("layers\t3\n", "", "layers\tmany\n"):
            with self.subTest(output=output), self.assertRaises(pxm.PxmError) as cm:
                pxm.check_result(self.spec, output)
            self.assertEqual(cm.exception.code, pxm.EXIT_VERIFY)

    def test_silent_font_fallback_is_caught(self):
        """Silent font fallback is caught."""
        with self.assertRaises(pxm.PxmError) as cm:
            pxm.check_result(self.spec, "font\tNoSuchFont\tHelvetica\tHelvetica\nlayers\t2\n")
        self.assertIn("NoSuchFont", cm.exception.message)

    def test_font_names_compare_loosely(self):
        """Font names compare loosely."""
        pxm.check_result(self.spec, "font\tHelvetica Neue Bold\tHelvetica\tHelveticaNeue-Bold\nlayers\t2\n")
        pxm.check_result(self.spec, "font\thelvetica\tHelvetica\tHelvetica\nlayers\t2\n")

    def test_missing_and_empty_exports(self):
        """Missing and empty exports."""
        with tempfile.TemporaryDirectory() as tmp:
            empty = os.path.join(tmp, "empty.svg")
            open(empty, "w").close()
            for path in (os.path.join(tmp, "gone.svg"), empty):
                s = dict(self.spec, export=[path])
                with self.subTest(path=path), self.assertRaises(pxm.PxmError) as cm:
                    pxm.check_exports(s)
                self.assertEqual(cm.exception.code, pxm.EXIT_VERIFY)

    def test_wrong_dimensions(self):
        """Wrong dimensions."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "a.png")
            with open(path, "w") as f:
                f.write("x")
            s = dict(self.spec, export=[path])
            sips = fake_proc(stdout="  pixelWidth: 64\n  pixelHeight: 64\n")
            with mock.patch("subprocess.run", return_value=sips), self.assertRaises(pxm.PxmError) as cm:
                pxm.check_exports(s)
            self.assertIn("64x64", cm.exception.message)
            good = fake_proc(stdout="  pixelWidth: 100\n  pixelHeight: 100\n")
            with mock.patch("subprocess.run", return_value=good):
                pxm.check_exports(s)


class CommandLine(unittest.TestCase):
    """Tests for command line."""
    def write(self, tmp, content):
        """Write a spec file into tmp and return its path."""
        path = os.path.join(tmp, "spec.json")
        with open(path, "w") as f:
            f.write(content)
        return path

    def test_dry_run_prints_script_and_touches_nothing(self):
        """Dry run prints script and touches nothing."""
        with tempfile.TemporaryDirectory() as tmp, mock.patch("subprocess.run") as run:
            code, out, _ = run_main("logo", self.write(tmp, json.dumps(spec())), "--dry-run")
        self.assertEqual(code, 0)
        self.assertIn('tell application "Pixelmator Pro"', out)
        run.assert_not_called()

    def test_exit_codes(self):
        """Exit codes."""
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(run_main("logo", os.path.join(tmp, "missing.json"))[0], pxm.EXIT_USAGE)
            self.assertEqual(run_main("logo", self.write(tmp, "{not json"))[0], pxm.EXIT_USAGE)
            code, _, err = run_main("logo", self.write(tmp, json.dumps(spec(width=-1))))
            self.assertEqual(code, pxm.EXIT_USAGE)
            self.assertIn("hint:", err)

    def test_full_run_with_a_fake_app(self):
        """Full run with a fake app."""
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write(tmp, json.dumps(spec(export=os.path.join(tmp, "deep/dir/a.svg"))))

            def fake(cmd, **kw):
                """A stand-in osascript run that writes the export files the build expects."""
                with open(os.path.join(tmp, "deep/dir/a.svg"), "w") as f:  # folder must exist by now
                    f.write("<svg/>")
                return fake_proc(stdout="layers\t1\n")

            with mock.patch("subprocess.run", side_effect=fake):
                code, out, err = run_main("logo", path)
        self.assertEqual((code, err), (0, ""))
        self.assertIn("exported:", out)

    def test_app_error_reaches_the_user_with_number_and_hint(self):
        """App error reaches the user with number and hint."""
        err = "5:9: execution error: Pixelmator Pro got an error: layer 0 (ellipse): no (-10006)"
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch("subprocess.run", return_value=fake_proc(1, stderr=err)):
            code, _, stderr = run_main("logo", self.write(tmp, json.dumps(spec())))
        self.assertEqual(code, pxm.EXIT_SCRIPT)
        self.assertIn("AppleScript -10006", stderr)
        self.assertIn("layer 0 (ellipse)", stderr)
        self.assertIn("read-only", stderr)

    def test_gif_needs_ffmpeg_and_a_gif_path(self):
        """Gif needs ffmpeg and a gif path."""
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write(tmp, json.dumps(spec()))
            self.assertEqual(run_main("logo", path, "--gif", "out.mov")[0], pxm.EXIT_USAGE)
            with mock.patch("subprocess.run", return_value=fake_proc(stdout="layers\t1\n")), \
                    mock.patch("shutil.which", return_value=None):
                code, _, err = run_main("logo", path, "--gif", os.path.join(tmp, "out.gif"))
        self.assertEqual(code, pxm.EXIT_ENV)
        self.assertIn("brew install ffmpeg", err)

    def test_check_off_the_mac(self):
        """Check off the mac."""
        with mock.patch.object(sys, "platform", "linux"):
            self.assertEqual(run_main("check")[0], pxm.EXIT_ENV)


class SkillFile(unittest.TestCase):
    """Tests for skill file."""
    def test_frontmatter(self):
        """Frontmatter."""
        with open(os.path.join(HERE, "SKILL.md")) as f:
            text = f.read()
        m = re.match(r"---\n(.*?)\n---\n", text, re.S)
        self.assertTrue(m, "SKILL.md needs YAML frontmatter")
        self.assertRegex(m.group(1), r"(?m)^name: pixelmator$")
        self.assertRegex(m.group(1), r"(?m)^description: .{40,}")
        self.assertNotIn(chr(0x2014), text)  # house rule: no em dashes


@unittest.skipUnless(sys.platform == "darwin" and not os.path.isdir(APP_PATH),
                     "needs a Mac without Pixelmator Pro (the CI runner)")
class MacWithoutTheApp(unittest.TestCase):
    """Tests for mac without the app."""
    def test_check_says_not_installed(self):
        """Check says not installed."""
        code, _, err = run_main("check")
        self.assertEqual(code, pxm.EXIT_ENV)
        self.assertIn("not installed", err)


class BuildLock(unittest.TestCase):
    """Tests for the file-based build lock (no app needed)."""

    def setUp(self):
        # Use a temp lock file for each test, not the real one.
        """Set up the fixtures for each test."""
        self.lock_dir = tempfile.TemporaryDirectory()
        self.lock_path = os.path.join(self.lock_dir.name, "test.lock")

    def tearDown(self):
        """Clean up after each test."""
        self.lock_dir.cleanup()

    def test_lock_blocked_by_default(self):
        """If lock is held, build_lock raises PxmError with code EXIT_ENV."""
        # Acquire the lock from the same process using two file descriptors.
        f1 = open(self.lock_path, 'a+')
        fcntl.flock(f1, fcntl.LOCK_EX)
        f1.write("other pid 9999\n")
        f1.flush()
        try:
            with mock.patch.object(pxm, 'BUILD_LOCK_PATH', self.lock_path):
                with self.assertRaises(pxm.PxmError) as cm:
                    with pxm.build_lock("test", wait=False):
                        pass
            self.assertEqual(cm.exception.code, pxm.EXIT_ENV)
            self.assertIn("Pixelmator Pro is busy", cm.exception.message)
            self.assertIn("other pid 9999", cm.exception.message)
            self.assertIn("--wait", cm.exception.hint)
        finally:
            fcntl.flock(f1, fcntl.LOCK_UN)
            f1.close()

    def test_lock_waits_when_flag_set(self):
        """With wait=True, build_lock waits for the lock to be released."""
        f1 = open(self.lock_path, 'a+')
        fcntl.flock(f1, fcntl.LOCK_EX)
        f1.write("other pid 9999\n")
        f1.flush()
        try:
            # Spawn a thread that will release the lock after a short delay.
            def release_lock():
                """Let go of the build lock after a short wait."""
                import time
                time.sleep(0.1)
                fcntl.flock(f1, fcntl.LOCK_UN)
            thread = threading.Thread(target=release_lock)
            thread.daemon = True
            thread.start()
            # build_lock with wait=True should succeed.
            with mock.patch.object(pxm, 'BUILD_LOCK_PATH', self.lock_path):
                with pxm.build_lock("test", wait=True):
                    pass
                thread.join(timeout=1)
        finally:
            fcntl.flock(f1, fcntl.LOCK_UN)
            f1.close()

    def test_dry_run_skips_lock(self):
        """--dry-run does not acquire the lock."""
        with tempfile.TemporaryDirectory() as tmp:
            spec_path = os.path.join(tmp, "spec.json")
            with open(spec_path, "w") as f:
                json.dump(spec(export=[]), f)
            # Hold the lock so any real build would fail.
            f1 = open(self.lock_path, 'a+')
            fcntl.flock(f1, fcntl.LOCK_EX)
            try:
                with mock.patch.object(pxm, 'BUILD_LOCK_PATH', self.lock_path):
                    code, out, err = run_main("logo", spec_path, "--dry-run")
                    # Dry-run should not be blocked by the lock.
                    self.assertEqual(code, 0)
                    self.assertIn("make new document", out)  # Script output, not an error.
            finally:
                fcntl.flock(f1, fcntl.LOCK_UN)
                f1.close()

    def test_wait_flag_accepted_by_logo(self):
        """--wait flag is accepted by logo command and doesn't block on dry-run."""
        with tempfile.TemporaryDirectory() as tmp:
            spec_path = os.path.join(tmp, "spec.json")
            with open(spec_path, "w") as f:
                json.dump(spec(export=[]), f)
            # With --dry-run, --wait should parse without error and not block.
            with mock.patch.object(pxm, 'BUILD_LOCK_PATH', self.lock_path):
                code, out, err = run_main("logo", spec_path, "--wait", "--dry-run")
                self.assertEqual(code, 0)

    def test_wait_flag_accepted_by_paint(self):
        """--wait parses on paint. read_pixels is faked: sips only exists on macOS, CI runs on Linux."""
        rows = [[(200, 10, 10)] * 4 for _ in range(4)]
        with mock.patch.object(pxm, "read_pixels", return_value=(4, 4, rows)):
            code, out, err = run_main("paint", "any.png", "--out", "/tmp/pxm-wait.png", "--wait", "--dry-run")
        self.assertEqual(code, 0, err)
        self.assertIn("make new document", out)


@unittest.skipUnless(LIVE, "set PXM_LIVE=1 on a Mac with Pixelmator Pro")
class Live(unittest.TestCase):
    """Drives the real app. Opens and closes documents on screen."""

    def logo(self, tmp, **over):
        """The example badge spec with any fields overridden."""
        with open(os.path.join(HERE, "examples", "badge.json")) as f:
            data = json.load(f)
        data.update(keep_open=False, **over)
        path = os.path.join(tmp, "spec.json")
        with open(path, "w") as f:
            json.dump(data, f)
        return run_main("logo", path)

    def test_check(self):
        """Check."""
        self.assertEqual(run_main("check")[0], 0)

    def test_example_builds_exports_and_verifies(self):
        """Example builds exports and verifies."""
        with tempfile.TemporaryDirectory() as tmp:
            png, svg = os.path.join(tmp, "new dir/a.png"), os.path.join(tmp, "a.svg")
            code, _, err = self.logo(tmp, export=[png, svg])
            self.assertEqual((code, err), (0, ""))
            alpha = subprocess.run(["sips", "-g", "hasAlpha", png], text=True, capture_output=True)
            self.assertIn("hasAlpha: yes", alpha.stdout)
            self.assertIn("<svg", open(svg).read())

    def test_gif_of_the_build(self):
        """Gif of the build."""
        with tempfile.TemporaryDirectory() as tmp:
            gif = os.path.join(tmp, "build.gif")
            path = os.path.join(tmp, "s.json")
            with open(os.path.join(HERE, "examples", "badge.json")) as f:
                data = dict(json.load(f), export=[], keep_open=False)
            with open(path, "w") as f:
                json.dump(data, f)
            code, _, err = run_main("logo", path, "--headless", "--gif", gif)
            self.assertEqual((code, err), (0, ""))
            with open(gif, "rb") as f:
                self.assertEqual(f.read(6), b"GIF89a")

    def test_unknown_font_fails_loudly(self):
        """Unknown font fails loudly."""
        with tempfile.TemporaryDirectory() as tmp:
            code, _, err = self.logo(tmp, export=[], layers=[
                {"type": "text", "text": "x", "font": "NoSuchFont-XYZ"}])
        self.assertEqual(code, pxm.EXIT_VERIFY)
        self.assertIn("NoSuchFont-XYZ", err)

    def test_raw_script_errors_are_decoded(self):
        """Raw script errors are decoded."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "bad.applescript")
            with open(path, "w") as f:
                f.write('tell application "Pixelmator Pro" to get width of document 99')
            code, _, err = run_main("run", path)
        self.assertEqual(code, pxm.EXIT_SCRIPT)
        self.assertIn("-1719", err)


class PaintMagickTests(unittest.TestCase):
    """The ImageMagick engine draws the same quadtree plan with no app."""

    @unittest.skipUnless(shutil.which("magick"), "ImageMagick not installed")
    def test_draws_a_png_of_the_right_size(self):
        """Draws a png of the right size."""
        layers = [{"x": 0, "y": 0, "width": 8, "height": 6, "fill": "#FF0000"},
                  {"x": 4, "y": 0, "width": 4, "height": 6, "fill": "#0000FF"}]
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "p.png")
            with contextlib.redirect_stdout(io.StringIO()):
                pxm.paint_magick(8, 6, layers, [out])
            data = open(out, "rb").read()
        self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual((int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")), (8, 6))

    def test_gif_needs_the_pixelmator_engine(self):
        """Gif needs the pixelmator engine."""
        args = pxm.argparse.Namespace(engine="magick", shapes=100, gif="x.gif", frames=None)
        with self.assertRaises(pxm.PxmError):
            pxm.cmd_paint(args)


if __name__ == "__main__":
    unittest.main()
