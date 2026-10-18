"""Her glyph logos: the keyword table, the house style, both renderers, and the fallbacks when her model is down."""
import os
import re
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app"))

import tools_glyphs  # noqa: E402
import tools_logo  # noqa: E402


class Keywords(unittest.TestCase):
    """The subject names the glyph plainly, whole words only."""

    def test_plain_subjects(self):
        """A surf school is a wave, a bakery is bread, a gym a dumbbell, Turing a network."""
        for text, want in (("a surf school", "wave"), ("my bakery", "bread"), ("a gym", "dumbbell"), ("turing", "network"),
                           ("a coffee shop", "cup"), ("hiking trails", "mountain"), ("dog grooming", "paw")):
            self.assertEqual(tools_glyphs.keyword_glyph(text), want, text)

    def test_no_partial_words(self):
        """Inside another word is no match: 'said' is not ai, 'apple' is not app."""
        self.assertIsNone(tools_glyphs.keyword_glyph("a quantum widget co"))
        self.assertIsNone(tools_glyphs.keyword_glyph("she said apple"))


class Style(unittest.TestCase):
    """Every glyph keeps the house style and draws in both renderers."""

    def test_inside_the_grid_and_no_banned_color(self):
        """Paths stay inside 192..832, strokes are 72 and white, and no palette is yellow."""
        for name, (_, layers) in tools_glyphs.GLYPHS.items():
            for l in layers:
                if l["type"] == "path":
                    self.assertEqual((l["stroke"], l["stroke_width"]), ("#FFFFFF", 72), name)
                    for n in re.findall(r"\d+", l["d"]):
                        self.assertTrue(192 <= int(n) <= 832, (name, n))
        for color in (c for pair in tools_glyphs.GLYPH_PALETTES.values() for c in pair):
            r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
            self.assertFalse(r > 180 and g > 150 and b < 100, color)  # yellow
        self.assertNotIn("#F2B33D", str(tools_logo.PALETTES))

    def test_both_renderers(self):
        """Each glyph becomes MVG with round ends and an SVG path, so the PNG and the SVG agree."""
        for name in tools_glyphs.GLYPHS:
            layers = tools_glyphs.glyph_layers(name, "terracotta")
            self.assertIn("fill #B5502C", tools_logo._mvg(layers))
            svg = tools_logo.layers_to_svg(layers)
            self.assertIn('fill="#b5502c"', svg)
            if any(l["type"] == "path" for l in layers):
                self.assertIn("stroke-linecap round", tools_logo._mvg(layers))
                self.assertIn('<path d="M', svg)


class Bundle(unittest.TestCase):
    """The Icon Composer bundle: icon.json in the brand kit's shape, the glyph as its one layer."""

    def test_bundle(self):
        """A gradient fill light to deep, a dark appearance, and glyph.png drawn without the tile."""
        import json
        import tempfile
        drawn = []
        with tempfile.TemporaryDirectory() as tmp:
            path = tools_glyphs.icon_bundle("wave", "blue", os.path.join(tmp, "x.icon"), lambda ls, png: drawn.append((ls, png)))
            with open(os.path.join(path, "icon.json")) as f:
                icon = json.load(f)
        self.assertEqual(icon["fill-specializations"][0]["value"]["linear-gradient"][1], "extended-srgb:0.000,0.443,0.890,1.0")
        self.assertEqual(icon["fill-specializations"][1]["appearance"], "dark")
        self.assertEqual(icon["groups"][0]["layers"][0]["image-name"], "glyph.png")
        self.assertTrue(drawn[0][1].endswith("Assets/glyph.png"))
        self.assertFalse(any(l.get("name") == "Tile" for l in drawn[0][0]))


class Design(unittest.TestCase):
    """The default design: keywords beat a wrong pick, and nothing at all still draws something."""

    def test_keyword_beats_the_model(self):
        """The model says leaf for a surf school: the wave still wins, the model's palette is kept."""
        with mock.patch.object(tools_logo, "_pick", return_value={"glyph": "leaf", "palette": "blue"}):
            chose, layers = tools_logo._glyph_design("a surf school")
        self.assertEqual(chose, {"glyph": "wave", "palette": "blue"})
        self.assertEqual(layers[0]["fill"], "#0071E3")

    def test_model_down(self):
        """No model: a keyword still draws its glyph; no keyword falls back to her flower."""
        with mock.patch.object(tools_logo, "_pick", side_effect=OSError("down")):
            self.assertEqual(tools_logo._glyph_design("a bakery")[0]["glyph"], "bread")
            chose, layers = tools_logo._glyph_design("a quantum widget co")
        self.assertEqual(chose["style"], "flower")
        self.assertEqual(layers[-1]["name"], "Core")

    def test_model_fills_the_gap(self):
        """No keyword: the model's glyph is used."""
        with mock.patch.object(tools_logo, "_pick", return_value={"glyph": "bolt", "palette": "red"}):
            self.assertEqual(tools_logo._glyph_design("a quantum widget co")[0], {"glyph": "bolt", "palette": "red"})


if __name__ == "__main__":
    unittest.main(verbosity=1)
