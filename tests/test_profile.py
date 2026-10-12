"""app/tools_profile.py against a throwaway home folder: no real iCloud, no real memory file is touched.

Run: python3 tests/test_profile.py
"""
import json
import os
import sys
import tempfile
import unittest

os.environ["SAMANTHA_HEADLESS"] = "1"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app"))
import tools  # noqa: E402
import tools_profile as tp  # noqa: E402
import util_words  # noqa: E402


class Profile(unittest.TestCase):
    """Where her memory lives, and that moving it never loses a fact."""

    def setUp(self):
        """A fresh home with one fact, and no SAMANTHA_MEMORY override."""
        self.old = {k: os.environ.pop(k, None) for k in ("SAMANTHA_MEMORY", "HOME")}
        self.home = tempfile.mkdtemp()
        os.environ["HOME"] = self.home
        self.local = os.path.join(self.home, ".samantha", "memory.json")
        tp._write(self.local, ["my dog is called Biscuit"])
        self.cloud = os.path.join(self.home, "Library", "Mobile Documents", "com~apple~CloudDocs")

    def tearDown(self):
        """Put the environment back."""
        for k, v in self.old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_no_icloud_changes_nothing(self):
        """Without iCloud Drive she says so and the memory stays where it was."""
        self.assertIn("not turned on", tp.keep_memory("icloud"))
        self.assertFalse(os.path.exists(os.path.expanduser(tp.POINTER)))
        self.assertEqual(util_words._memory_path(), self.local)

    def test_icloud_merges_and_points(self):
        """An existing iCloud copy and the local file merge, each fact once, and she reads from iCloud afterwards."""
        os.makedirs(self.cloud)
        tp._write(os.path.join(self.cloud, "Samantha", "memory.json"), ["MY DOG IS CALLED BISCUIT", "the code is 42"])
        self.assertIn("2 things", tp.keep_memory("icloud"))
        dest = os.path.join(self.cloud, "Samantha", "memory.json")
        self.assertEqual(util_words._memory_path(), dest)
        self.assertEqual(json.load(open(dest)), ["MY DOG IS CALLED BISCUIT", "the code is 42"])

    def test_back_on_this_mac(self):
        """Coming back keeps the facts, drops the pointer, and leaves the iCloud copy alone."""
        os.makedirs(self.cloud)
        tp.keep_memory("icloud")
        util_words_path = util_words._memory_path()
        tp._write(util_words_path, ["my dog is called Biscuit", "new fact from the phone"])
        self.assertIn("on this Mac again", tp.keep_memory("mac"))
        self.assertEqual(util_words._memory_path(), self.local)
        self.assertEqual(json.load(open(self.local)), ["my dog is called Biscuit", "new fact from the phone"])
        self.assertTrue(os.path.exists(util_words_path))

    def test_routes_and_asking_first(self):
        """The words route to keep_memory, it is a write, and no model can pick it."""
        self.assertEqual(tools.plan("keep my memory in icloud"), [("keep_memory", ("icloud",))])
        self.assertEqual(tools.plan("keep my memory on this mac"), [("keep_memory", ("mac",))])
        self.assertIn("keep_memory", tools.WRITES)
        self.assertIn("keep_memory", tools.NOT_FOR_MODELS)


if __name__ == "__main__":
    unittest.main()
