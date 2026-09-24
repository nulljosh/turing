"""gui/launcher.sh: the packaged app's first-run setup, a plain sh script so it works with no Xcode
and no Swift toolchain. Runs the real script against a mocked HOME, no network involved (--check
skips the pip install), so this passes on Linux CI the same as on the Mac.

Run: python3 tests/test_launcher.py
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAUNCHER = os.path.join(REPO, "gui", "launcher.sh")


def run_launcher(home):
    """One `sh gui/launcher.sh --check` with HOME pointed at a scratch directory, real stdout/stderr."""
    env = dict(os.environ, HOME=home)
    return subprocess.run(["sh", LAUNCHER, "--check"], env=env, capture_output=True, text=True)


class FirstRun(unittest.TestCase):
    """No venv yet: she says she is setting up, and a real (offline) venv appears once."""

    def setUp(self):
        """A throwaway HOME, cleaned up after, so no test ever touches your real Application Support."""
        self.home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.home, ignore_errors=True)
        self.venv = os.path.join(self.home, "Library", "Application Support", "Samantha", "venv")

    def test_missing_venv_shows_setup_and_creates_one(self):
        """A fresh HOME has no venv: the setup line comes first, then a real venv, then launcher ok."""
        self.assertFalse(os.path.exists(self.venv))
        result = run_launcher(self.home)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('{"working": "Setting up Samantha, about two minutes..."}', result.stdout)
        self.assertIn("launcher ok", result.stdout)
        self.assertTrue(os.path.exists(os.path.join(self.venv, "bin", "python3")))

    def test_existing_venv_skips_setup(self):
        """Run it twice: the second run finds the venv already there and says nothing about setting up."""
        run_launcher(self.home)
        result = run_launcher(self.home)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("Setting up Samantha", result.stdout)
        self.assertIn("launcher ok", result.stdout)

    def test_never_installs_requirements_under_check(self):
        """--check proves the env exists without touching pip or the network, even with no requirements.txt around."""
        result = run_launcher(self.home)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("pip", result.stderr.lower())


if __name__ == "__main__":
    unittest.main()
