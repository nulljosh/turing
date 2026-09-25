"""tools_badge.py: the badge modernizer. step_for's pure math, plus a real build at step 0 and step 1 when
magick and potrace are on this machine; skips clean, like tests/test_tools_image.py does for CI's ubuntu box,
when they are not.

Run: python3 tests/test_badge.py
"""
import os
import shutil
import sys
import tempfile
import unittest

os.environ["SAMANTHA_HEADLESS"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tools_badge

HAS_TOOLS = bool(shutil.which("magick") and shutil.which("potrace"))


class StepFor(unittest.TestCase):
    """step_for's pure arithmetic, no magick or potrace needed."""

    def test_cases(self):
        """4.7.x is step 0, each minor after it is one step, a major bump is one more step past the last minor."""
        self.assertEqual(tools_badge.step_for("4.7.0"), 0)
        self.assertEqual(tools_badge.step_for("4.7.3"), 0)
        self.assertEqual(tools_badge.step_for("4.8.0"), 1)
        self.assertEqual(tools_badge.step_for("5.0.0"), 3)

    def test_cap(self):
        """A version far past MAX_STEP still returns MAX_STEP, never more."""
        self.assertEqual(tools_badge.step_for("9.9.0"), tools_badge.MAX_STEP)
        self.assertLessEqual(tools_badge.step_for("40.0.0"), tools_badge.MAX_STEP)

    def test_garbage_version(self):
        """A version string that does not parse is step 0, never a crash."""
        self.assertEqual(tools_badge.step_for("not a version"), 0)


class Edit1(unittest.TestCase):
    """The one-edit tolerance words_read uses against Vision's known T/P confusion on this font."""

    def test_exact_and_one_off(self):
        """Equal strings, and strings one substitution/insertion/deletion apart, both count."""
        self.assertTrue(tools_badge._edit1("TURING", "TURING"))
        self.assertTrue(tools_badge._edit1("PURING", "TURING"))
        self.assertTrue(tools_badge._edit1("TURIN", "TURING"))
        self.assertFalse(tools_badge._edit1("PURPLE", "TURING"))


@unittest.skipUnless(HAS_TOOLS, "magick and potrace not both on PATH")
class Modernize(unittest.TestCase):
    """A real build, against a scratch copy of the repo's own source badge so nothing here touches web/badge.svg."""

    def setUp(self):
        """Point tools_badge at temp copies of the source, output svg and preview, restored in tearDown."""
        self.tmp = tempfile.mkdtemp()
        real_source = tools_badge.SOURCE_SVG if os.path.exists(tools_badge.SOURCE_SVG) else tools_badge.OUTPUT_SVG
        self._orig = (tools_badge.SOURCE_SVG, tools_badge.OUTPUT_SVG, tools_badge.OUTPUT_PNG)
        tools_badge.SOURCE_SVG = os.path.join(self.tmp, "badge-source.svg")
        tools_badge.OUTPUT_SVG = os.path.join(self.tmp, "badge.svg")
        tools_badge.OUTPUT_PNG = os.path.join(self.tmp, "badge-preview.png")
        shutil.copyfile(real_source, tools_badge.SOURCE_SVG)

    def tearDown(self):
        """Point tools_badge back at the real files and drop the scratch copies."""
        tools_badge.SOURCE_SVG, tools_badge.OUTPUT_SVG, tools_badge.OUTPUT_PNG = self._orig
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_modernize_zero_and_one(self):
        """Step 0 and step 1 each produce an svg with the aria-label kept, and a preview PNG next to it."""
        for step in (0, 1):
            ok, msg = tools_badge.modernize(step)
            self.assertTrue(ok, msg)
            self.assertTrue(os.path.exists(tools_badge.OUTPUT_SVG))
            self.assertTrue(os.path.exists(tools_badge.OUTPUT_PNG))
            with open(tools_badge.OUTPUT_SVG, encoding="utf-8") as f:
                svg = f.read()
            self.assertIn('role="img"', svg)
            self.assertIn(tools_badge.ARIA_LABEL, svg)

    def test_failing_gate_restores_previous_files(self):
        """build_and_gate keeps the old badge when the gate fails, never a half-written one."""
        tools_badge.modernize(0)
        with open(tools_badge.OUTPUT_SVG, "rb") as f:
            before_svg = f.read()
        with open(tools_badge.OUTPUT_PNG, "rb") as f:
            before_png = f.read()

        real_gate = tools_badge.gate
        tools_badge.gate = lambda *a, **k: (False, ["forced failure for this test"])
        try:
            rc = tools_badge.build_and_gate("5.0.0")
        finally:
            tools_badge.gate = real_gate
        self.assertEqual(rc, 0)  # a release must never fail over the badge
        with open(tools_badge.OUTPUT_SVG, "rb") as f:
            self.assertEqual(f.read(), before_svg)
        with open(tools_badge.OUTPUT_PNG, "rb") as f:
            self.assertEqual(f.read(), before_png)


if __name__ == "__main__":
    unittest.main()
