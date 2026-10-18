"""Her symbols, wordmarks and avatars: the routes, the name fence, the same face every time, never over a file."""
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app"))

import tools_mark  # noqa: E402


class Routes(unittest.TestCase):
    """Their own words reach them, and make_logo keeps its own."""

    def route(self, text):
        """(tool, argument) for the first ROUTES pattern that matches, or (None, None)."""
        for pat, name, arg in tools_mark.ROUTES:
            m = pat.match(text)
            if m:
                return name, arg(m)
        return None, None

    def test_routes(self):
        """symbol, wordmark and avatar each get the rest of the sentence; a plain logo request is left to make_logo."""
        self.assertEqual(self.route("make a symbol for a surf school"), ("make_symbol", "a surf school"))
        self.assertEqual(self.route("design me a wordmark for Wavecrest, a surf school"), ("make_wordmark", "Wavecrest, a surf school"))
        self.assertEqual(self.route("make an avatar for Alex"), ("make_avatar", "Alex"))
        self.assertEqual(self.route("make a profile picture of Mom"), ("make_avatar", "Mom"))
        self.assertEqual(self.route("make me a logo for turing"), (None, None))


class Fence(unittest.TestCase):
    """Odd names never reach ImageMagick."""

    def test_bad_names_refused(self):
        """Shell characters, empty, too long and a leading dash are plain replies and run nothing."""
        with mock.patch.object(tools_mark.tools_logo, "_run") as run:
            for bad in ("bad;name$(rm)", "", "x" * 30, "-evil", "a/b", "%0"):
                self.assertIn("up to 24", tools_mark.make_avatar(bad))
                self.assertIn("up to 24", tools_mark.make_wordmark(bad))
        run.assert_not_called()


class Outputs(unittest.TestCase):
    """Real drawing through ImageMagick into a temp folder."""

    def setUp(self):
        """Point the Desktop at a temp folder for this test."""
        self.tmp = tempfile.mkdtemp()
        self.patch = mock.patch.object(tools_mark.tools_image, "output", lambda name: os.path.join(self.tmp, name))
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def test_avatar_same_face_and_never_over_a_file(self):
        """The same name draws the same pixels, and a second run is a new file, not a replacement."""
        import filecmp
        a = tools_mark.make_avatar("Alex")
        self.assertIn("samantha-avatar.png", a)
        tools_mark.make_avatar("alex")  # case does not matter
        self.assertTrue(filecmp.cmp(os.path.join(self.tmp, "samantha-avatar.png"), os.path.join(self.tmp, "samantha-avatar-2.png"), shallow=False))
        self.assertTrue(os.path.exists(os.path.join(self.tmp, "samantha-avatar.svg")))
        tools_mark.make_avatar("Joshua")
        self.assertFalse(filecmp.cmp(os.path.join(self.tmp, "samantha-avatar.png"), os.path.join(self.tmp, "samantha-avatar-3.png"), shallow=False))

    def test_symbol_and_wordmark(self):
        """A keyword subject needs no model: the symbol is a PNG and an SVG, the wordmark one wider PNG."""
        with mock.patch.object(tools_mark.tools_logo, "_pick", side_effect=OSError("down")):
            self.assertIn("glyph wave", tools_mark.make_symbol("a surf school"))
            self.assertIn("glyph bread", tools_mark.make_wordmark("Crumb & Co, my bakery"))
        for name in ("samantha-symbol.png", "samantha-symbol.svg", "samantha-wordmark.png"):
            self.assertTrue(os.path.exists(os.path.join(self.tmp, name)), name)
        self.assertEqual(os.listdir(self.tmp).count("samantha-wordmark.parts"), 0)  # scratch folder cleaned up
        out = subprocess.run(["magick", "identify", "-format", "%w %h", os.path.join(self.tmp, "samantha-wordmark.png")], capture_output=True, text=True).stdout
        w, h = (int(v) for v in out.split())
        self.assertGreater(w, 2 * h)


class Shape(unittest.TestCase):
    """Every tool is documented."""

    def test_documented(self):
        """Each tool has a docstring, and the TOOLS tuple names all three."""
        self.assertTrue(all(f.__doc__ for f in tools_mark.TOOLS))
        self.assertEqual({f.__name__ for f in tools_mark.TOOLS}, {"make_symbol", "make_wordmark", "make_avatar"})


if __name__ == "__main__":
    unittest.main(verbosity=1)
