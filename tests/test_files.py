"""tools_files.py: the files family, read and write halves, inside a throwaway home folder.

HOME is patched to a temp dir so every move, copy, rename, zip and unzip runs for real on scratch files and never
touches the Mac. Trash goes through Finder, so it is only checked headless (message, nothing moved) and with
osascript stood in. The pure parts (split_pair, _home, ROUTES) get their own checks.

Run: python3 tests/test_files.py
"""
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

os.environ["SAMANTHA_HEADLESS"] = "1"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app"))
import tools_files  # noqa: E402


class Pure(unittest.TestCase):
    """split_pair and _home: no files touched."""

    def test_split_pair_shapes(self):
        """A tab, a from/to sentence, a bare to, and a lone piece all split the same way."""
        self.assertEqual(tools_files.split_pair("a.txt\tb"), ("a.txt", "b"))
        self.assertEqual(tools_files.split_pair("invoices\tfolder\tto\tbackup"), ("invoices", "backup"))
        self.assertEqual(tools_files.split_pair("draft.md from downloads to documents"), ("draft.md", "documents"))
        self.assertEqual(tools_files.split_pair("draft.md to the documents folder"), ("draft.md", "the documents folder"))
        self.assertEqual(tools_files.split_pair("draft.md"), ("draft.md", ""))

    def test_home_fence(self):
        """Outside the home folder and hidden paths are None; inside is a real path."""
        self.assertIsNone(tools_files._home("/etc/passwd"))
        self.assertIsNone(tools_files._home("~/.ssh/id_rsa"))
        self.assertIsNone(tools_files._home("~/../../etc"))
        self.assertTrue(tools_files._home("~/Documents").startswith(tools_files.HOME))

    def test_routes(self):
        """The exact phrases hand each write tool its tab-joined argument."""
        def route(text):
            """(tool, argument) for the first ROUTES pattern that matches, or (None, None)."""
            for pat, name, arg in tools_files.ROUTES:
                m = pat.match(text)
                if m:
                    return name, arg(m)
            return None, None
        self.assertEqual(route("move ~/a.txt to ~/Desktop"), ("move_file", "~/a.txt\t~/Desktop"))
        self.assertEqual(route("copy the file a.txt into the folder b"), ("copy_file", "a.txt\tb"))
        self.assertEqual(route("rename a.txt as b.txt"), ("rename_file", "a.txt\tb.txt"))
        self.assertEqual(route("zip ~/Documents/x"), ("zip_file", "~/Documents/x"))
        self.assertEqual(route("unzip ~/x.zip"), ("unzip_file", "~/x.zip"))
        self.assertEqual(route("throw away old.txt"), ("trash_file", "old.txt"))
        self.assertEqual(route("move my notes to the cloud")[0], None)  # spaces: never a file op


class Writes(unittest.TestCase):
    """Every write tool against real scratch files, HOME patched to a temp dir, headless off."""

    def setUp(self):
        """A temp home with a file and a folder in it."""
        self.tmp = os.path.realpath(tempfile.mkdtemp())
        self.patches = [mock.patch.object(tools_files, "HOME", self.tmp), mock.patch.object(tools_files, "HEADLESS", False)]
        for p in self.patches:
            p.start()
        self.file = os.path.join(self.tmp, "a.txt")
        self.folder = os.path.join(self.tmp, "box")
        os.mkdir(self.folder)
        with open(self.file, "w") as f:
            f.write("hello")
        with open(os.path.join(self.folder, "inner.txt"), "w") as f:
            f.write("inside")

    def tearDown(self):
        """Undo the patches and remove the temp home."""
        for p in self.patches:
            p.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_move_into_folder_keeps_name(self):
        """A folder destination keeps the file's name; the source is gone after."""
        reply = tools_files.move_file(f"{self.file}\t{self.folder}")
        self.assertIn("Moved", reply)
        self.assertTrue(os.path.isfile(os.path.join(self.folder, "a.txt")))
        self.assertFalse(os.path.exists(self.file))

    def test_move_refuses_outside_and_existing(self):
        """Outside home is refused with a sentence; an occupied destination is refused and nothing moves."""
        self.assertIn("only put things inside your home", tools_files.move_file(f"{self.file}\t/tmp/elsewhere.txt"))
        self.assertIn("No file or folder", tools_files.move_file(f"{self.tmp}/missing.txt\t{self.folder}"))
        with open(os.path.join(self.folder, "a.txt"), "w") as f:
            f.write("taken")
        self.assertIn("already there", tools_files.move_file(f"{self.file}\t{self.folder}"))
        self.assertTrue(os.path.isfile(self.file))

    def test_copy_file_and_folder(self):
        """A file copy keeps the original; a folder copy brings its contents."""
        self.assertIn("Copied", tools_files.copy_file(f"{self.file}\t{self.tmp}/b.txt"))
        self.assertTrue(os.path.isfile(self.file) and os.path.isfile(os.path.join(self.tmp, "b.txt")))
        self.assertIn("Copied", tools_files.copy_file(f"{self.folder}\t{self.tmp}/box2"))
        self.assertTrue(os.path.isfile(os.path.join(self.tmp, "box2", "inner.txt")))
        self.assertIn("already there", tools_files.copy_file(f"{self.file}\t{self.tmp}/b.txt"))

    def test_rename(self):
        """A plain name renames in place; a slash, a hidden name, or a taken name is refused."""
        self.assertIn("Renamed", tools_files.rename_file(f"{self.file}\tfinal.txt"))
        self.assertTrue(os.path.isfile(os.path.join(self.tmp, "final.txt")))
        self.assertIn("not a name I can use", tools_files.rename_file(f"{self.folder}\tx/y"))
        self.assertIn("not a name I can use", tools_files.rename_file(f"{self.folder}\t.hidden"))
        self.assertIn("already a", tools_files.rename_file(f"{self.folder}\tfinal.txt"))

    def test_zip_and_unzip_roundtrip(self):
        """A folder zips next to itself and unzips back with its contents; a file zips too; repeats are refused."""
        self.assertIn("Zipped", tools_files.zip_file(self.folder))
        self.assertTrue(os.path.isfile(self.folder + ".zip"))
        self.assertIn("already exists", tools_files.zip_file(self.folder))
        shutil.rmtree(self.folder)
        self.assertIn("Unzipped", tools_files.unzip_file(self.folder + ".zip"))
        self.assertEqual(open(os.path.join(self.folder, "inner.txt")).read(), "inside")
        self.assertIn("already exists", tools_files.unzip_file(self.folder + ".zip"))
        self.assertIn("Zipped", tools_files.zip_file(self.file))
        self.assertTrue(os.path.isfile(self.file + ".zip"))
        self.assertIn("No zip file", tools_files.unzip_file(self.file))

    def test_trash_goes_through_finder_never_home(self):
        """Trash hands the real path to osascript once; the whole home folder is refused before that."""
        with mock.patch.object(tools_files.subprocess, "run") as run:
            self.assertIn("to the Trash", tools_files.trash_file(self.file))
        self.assertEqual(run.call_count, 1)
        self.assertEqual(run.call_args[0][0][-1], self.file)
        self.assertEqual(tools_files.trash_file(self.tmp), "Not your whole home folder.")
        self.assertIn("No file or folder", tools_files.trash_file(f"{self.tmp}/missing"))

    def test_headless_describes_without_touching(self):
        """Headless, every write answers as if done and nothing on disk changes."""
        with mock.patch.object(tools_files, "HEADLESS", True), mock.patch.object(tools_files.subprocess, "run", side_effect=AssertionError("ran")):
            self.assertIn("Moved", tools_files.move_file(f"{self.file}\t{self.folder}"))
            self.assertIn("Zipped", tools_files.zip_file(self.folder))
            self.assertIn("to the Trash", tools_files.trash_file(self.file))
        self.assertTrue(os.path.isfile(self.file))
        self.assertFalse(os.path.exists(self.folder + ".zip"))


if __name__ == "__main__":
    unittest.main()
