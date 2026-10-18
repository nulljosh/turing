"""tools_blender.py: blender_info and render_blend, with subprocess mocked throughout so Blender is never run.

Covers the routes, the home-only and no-hidden-files fence, the headless answer (nothing runs), the no-overwrite
rule, and a missing Blender getting a plain reply. A throwaway home folder stands in for ~.

Run: python3 tests/test_blender.py
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

os.environ["SAMANTHA_HEADLESS"] = "1"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app"))
import tools_blender  # noqa: E402
import tools_files  # noqa: E402


def fake_info(*args, **kwargs):
    """A stand-in for subprocess.run that answers like the info script: two objects, a cube and a camera."""
    out = 'Blender 4.5\nBLENDINFO {"objects": 2, "vertices": 8, "names": ["Cube", "Camera"]}\n'
    return subprocess.CompletedProcess(args[0], 0, stdout=out, stderr="")


class Base(unittest.TestCase):
    """Each test gets a throwaway home folder with one .blend and one hidden .blend."""

    def setUp(self):
        """Point tools_files at a temp home and make the scene files."""
        self.home = tempfile.mkdtemp()
        self.real_home = tools_files.HOME
        tools_files.HOME = os.path.realpath(self.home)
        os.makedirs(os.path.join(tools_files.HOME, "Documents"))
        self.scene = os.path.join(tools_files.HOME, "Documents", "scene.blend")
        open(self.scene, "wb").close()
        os.makedirs(os.path.join(tools_files.HOME, ".hidden"))
        open(os.path.join(tools_files.HOME, ".hidden", "secret.blend"), "wb").close()

    def tearDown(self):
        """Restore the real home and delete the temp one."""
        tools_files.HOME = self.real_home
        shutil.rmtree(self.home, ignore_errors=True)


class Routes(unittest.TestCase):
    """The exact phrases hand each tool its path."""

    def route(self, text):
        """(tool, argument) for the first ROUTES pattern that matches, or (None, None)."""
        for pat, name, arg in tools_blender.ROUTES:
            m = pat.match(text)
            if m:
                return name, arg(m)
        return None, None

    def test_info_routes(self):
        """what is in and inspect each hand blender_info the path."""
        self.assertEqual(self.route("what is in ~/Documents/scene.blend"), ("blender_info", "~/Documents/scene.blend"))
        self.assertEqual(self.route("inspect ~/model.glb"), ("blender_info", "~/model.glb"))
        self.assertEqual(self.route("what's in the ~/a.obj"), ("blender_info", "~/a.obj"))

    def test_render_route(self):
        """render hands render_blend the .blend; anything else is left to the other routers."""
        self.assertEqual(self.route("render ~/Documents/scene.blend"), ("render_blend", "~/Documents/scene.blend"))
        self.assertEqual(self.route("render my notes"), (None, None))
        self.assertEqual(self.route("render ~/a.png"), (None, None))


class Fence(Base):
    """Home only, nothing hidden, and only the file types each tool takes."""

    def test_outside_home_refused(self):
        """A path outside home, a hidden path and a wrong extension are all refused, and nothing runs."""
        with mock.patch.object(tools_blender.subprocess, "run") as run:
            self.assertIn("allowed", tools_blender.blender_info("/etc/passwd.blend"))
            self.assertIn("allowed", tools_blender.blender_info("~/.hidden/secret.blend"))
            self.assertIn("allowed", tools_blender.blender_info("~/Documents/notes.txt"))
            self.assertIn("allowed", tools_blender.render_blend("~/../../etc/x.blend"))
            self.assertIn("allowed", tools_blender.render_blend("~/.hidden/secret.blend"))
            self.assertIn("allowed", tools_blender.render_blend("~/Documents/model.glb"))
            run.assert_not_called()

    def test_missing_file_refused(self):
        """A 3D file that is not there gets a plain refusal, never a raise."""
        self.assertIn("No 3D file", tools_blender.blender_info("~/Documents/nope.fbx"))


class Info(Base):
    """blender_info reads Blender's JSON line and says one plain sentence."""

    def test_sentence(self):
        """Object count, vertex total and names come back in one sentence."""
        with mock.patch.object(tools_blender, "_blender", return_value="/opt/homebrew/bin/blender"), \
                mock.patch.object(tools_blender.subprocess, "run", side_effect=fake_info) as run:
            got = tools_blender.blender_info(self.scene)
        self.assertEqual(got, "~/Documents/scene.blend has 2 objects and 8 vertices: Cube, Camera.")
        cmd = run.call_args[0][0]
        self.assertEqual(cmd[:3], ["/opt/homebrew/bin/blender", "-b", "-P"])
        self.assertEqual(cmd[-1], os.path.join(tools_files.HOME, "Documents", "scene.blend"))

    def test_more_than_names_shown(self):
        """Objects past the names listed are counted as more, never dropped silently."""
        out = 'BLENDINFO {"objects": 25, "vertices": 900, "names": ["A", "B"]}'
        with mock.patch.object(tools_blender, "_blender", return_value="blender"), \
                mock.patch.object(tools_blender.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, stdout=out, stderr="")):
            self.assertIn("and 23 more", tools_blender.blender_info(self.scene))

    def test_missing_blender_plain_reply(self):
        """No blender on the Mac is a plain sentence, and nothing is run."""
        with mock.patch.object(tools_blender, "_blender", return_value=None), mock.patch.object(tools_blender.subprocess, "run") as run:
            self.assertEqual(tools_blender.blender_info(self.scene), tools_blender._NO_BLENDER)
            run.assert_not_called()

    def test_blender_crash_plain_reply(self):
        """A Blender that will not start, or prints no info line, is a plain reply."""
        with mock.patch.object(tools_blender, "_blender", return_value="blender"), \
                mock.patch.object(tools_blender.subprocess, "run", side_effect=subprocess.TimeoutExpired("blender", 120)):
            self.assertEqual(tools_blender.blender_info(self.scene), "Blender did not answer.")
        with mock.patch.object(tools_blender, "_blender", return_value="blender"), \
                mock.patch.object(tools_blender.subprocess, "run", return_value=subprocess.CompletedProcess([], 1, stdout="", stderr="")):
            self.assertIn("could not open", tools_blender.blender_info(self.scene))


class Render(Base):
    """render_blend: headless answers and runs nothing, never overwrites, names the PNG like the file."""

    def test_headless_answers_and_runs_nothing(self):
        """Under SAMANTHA_HEADLESS the answer comes back and Blender is never called."""
        with mock.patch.object(tools_files, "HEADLESS", True), mock.patch.object(tools_blender.subprocess, "run") as run:
            got = tools_blender.render_blend(self.scene)
        self.assertEqual(got, "Rendered frame 1 to ~/Documents/scene.png.")
        run.assert_not_called()
        self.assertFalse(os.path.exists(os.path.join(tools_files.HOME, "Documents", "scene.png")))

    def test_renders_beside_the_file(self):
        """A live render calls blender with -F PNG and frame 1, and moves the frame it made to scene.png."""
        def fake_render(cmd, **kwargs):
            """Write the frame the way blender -o <dir>/frame_ -F PNG -f 1 would."""
            prefix = cmd[cmd.index("-o") + 1]
            with open(prefix + "0001.png", "wb") as f:
                f.write(b"png")
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        with mock.patch.object(tools_files, "HEADLESS", False), \
                mock.patch.object(tools_blender, "_blender", return_value="blender"), \
                mock.patch.object(tools_blender.subprocess, "run", side_effect=fake_render) as run:
            got = tools_blender.render_blend(self.scene)
        self.assertEqual(got, "Rendered frame 1 to ~/Documents/scene.png.")
        cmd = run.call_args[0][0]
        self.assertEqual(cmd[1:2], ["-b"])
        self.assertEqual(cmd[cmd.index("-F") + 1], "PNG")
        self.assertEqual(cmd[cmd.index("-f") + 1], "1")
        self.assertEqual(run.call_args[1]["timeout"], 180)
        with open(os.path.join(tools_files.HOME, "Documents", "scene.png"), "rb") as f:
            self.assertEqual(f.read(), b"png")

    def test_never_overwrites(self):
        """A PNG already there is named and left alone, and Blender is not run."""
        open(os.path.join(tools_files.HOME, "Documents", "scene.png"), "wb").close()
        with mock.patch.object(tools_files, "HEADLESS", False), mock.patch.object(tools_blender.subprocess, "run") as run:
            self.assertEqual(tools_blender.render_blend(self.scene), "~/Documents/scene.png already exists.")
        run.assert_not_called()

    def test_missing_blender_plain_reply(self):
        """No blender on the Mac is a plain reply, and no PNG appears."""
        with mock.patch.object(tools_files, "HEADLESS", False), mock.patch.object(tools_blender, "_blender", return_value=None):
            self.assertEqual(tools_blender.render_blend(self.scene), tools_blender._NO_BLENDER)
        self.assertFalse(os.path.exists(os.path.join(tools_files.HOME, "Documents", "scene.png")))

    def test_timeout_plain_reply(self):
        """A render that runs past 180 seconds is a plain reply, and no PNG appears."""
        with mock.patch.object(tools_files, "HEADLESS", False), \
                mock.patch.object(tools_blender, "_blender", return_value="blender"), \
                mock.patch.object(tools_blender.subprocess, "run", side_effect=subprocess.TimeoutExpired("blender", 180)):
            self.assertEqual(tools_blender.render_blend(self.scene), "Blender did not finish the render.")
        self.assertFalse(os.path.exists(os.path.join(tools_files.HOME, "Documents", "scene.png")))


class Shape(unittest.TestCase):
    """Every tool is documented and listed."""

    def test_tools_documented(self):
        """Each tool has a docstring, and the TOOLS tuple names both."""
        self.assertTrue(all(f.__doc__ for f in tools_blender.TOOLS))
        self.assertEqual({f.__name__ for f in tools_blender.TOOLS}, {"blender_info", "render_blend"})


if __name__ == "__main__":
    unittest.main(verbosity=1)
