"""styles.py: the cell plan is a real partition, every style draws, and the MVG it writes is what ImageMagick reads.
No ImageMagick needed. Run: cd pixelmator && python3 -m unittest test_styles"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import styles


def photo(w=40, h=30):
    """A small synthetic photo: a sky gradient over a dark noisy ground, like a landscape."""
    rows = []
    for y in range(h):
        line = []
        for x in range(w):
            line.append((90 + y * 4, 140 + y * 3, 230) if y < h // 2 else ((x * 37 + y * 11) % 60, 40 + (x * 7) % 30, 20))
        rows.append(line)
    return w, h, rows


class Cells(unittest.TestCase):
    """The plan every style starts from."""

    def test_cells_cover_the_frame_exactly_once(self):
        """Leaves only: the cells' areas add up to the frame and no pixel is in two cells."""
        w, h, rows = photo()
        cs = styles.cells(w, h, rows, 300)
        self.assertLessEqual(len(cs), 300)
        self.assertEqual(sum((x1 - x0) * (y1 - y0) for x0, y0, x1, y1, _ in cs), w * h)
        seen = set()
        for x0, y0, x1, y1, _ in cs:
            for y in range(y0, y1):
                for x in range(x0, x1):
                    self.assertNotIn((x, y), seen)
                    seen.add((x, y))

    def test_busy_ground_gets_smaller_cells_than_calm_sky(self):
        """Detail lands where the picture needs it."""
        w, h, rows = photo()
        cs = styles.cells(w, h, rows, 200)
        sky = [(x1 - x0) * (y1 - y0) for x0, y0, x1, y1, _ in cs if y1 <= h // 2]
        ground = [(x1 - x0) * (y1 - y0) for x0, y0, x1, y1, _ in cs if y0 >= h // 2]
        self.assertGreater(sum(sky) / len(sky), sum(ground) / len(ground))


class Draw(unittest.TestCase):
    """Every style, drawn and written out."""

    def test_every_style_draws_inside_the_canvas(self):
        """Each style returns a background and shapes that stay on the canvas, with real colors."""
        w, h, rows = photo()
        cs = styles.cells(w, h, rows, 300)
        for style in styles.STYLES:
            bg, prims = styles.draw(cs, 4, style)
            self.assertRegex(bg, r"^#[0-9A-F]{6}$", style)
            self.assertTrue(prims, style)
            for p in prims:
                x0, y0, x1, y1 = p["box"]
                if p["kind"] != "circle":  # a dab may spill a little past the edge, like paint does
                    self.assertTrue(-1 <= min(x0, x1) and max(x0, x1) <= w * 4 and -1 <= min(y0, y1) and max(y0, y1) <= h * 4, (style, p))
                self.assertTrue(p.get("fill") or p.get("stroke"), (style, p))

    def test_poster_uses_at_most_eight_colors(self):
        """A screen print has a small fixed palette."""
        w, h, rows = photo()
        _, prims = styles.draw(styles.cells(w, h, rows, 300), 4, "poster")
        self.assertLessEqual(len({p["fill"] for p in prims}), 8)

    def test_sketch_is_ink_on_paper_and_darker_ground_gets_more_strokes(self):
        """Pencil: only ink lines on paper, and the dark ground is hatched harder than the light sky."""
        w, h, rows = photo()
        bg, prims = styles.draw(styles.cells(w, h, rows, 300), 4, "sketch")
        self.assertEqual(bg, styles.PAPER)
        self.assertEqual({p["kind"] for p in prims}, {"line"})
        sky = sum(1 for p in prims if max(p["box"][1], p["box"][3]) <= h * 2)
        ground = sum(1 for p in prims if min(p["box"][1], p["box"][3]) >= h * 2)
        self.assertGreater(ground, sky)

    def test_unknown_style_is_a_plain_error(self):
        """A style that does not exist names the ones that do."""
        with self.assertRaisesRegex(ValueError, "mosaic"):
            styles.draw([(0, 0, 1, 1, "#000000")], 1, "banana")

    def test_mvg_has_one_primitive_per_shape(self):
        """to_mvg writes every kind ImageMagick draws: rectangle, roundrectangle, ellipse, line."""
        prims = [{"kind": "rect", "box": (0, 0, 9, 9), "fill": "#112233"},
                 {"kind": "roundrect", "box": (1, 1, 8, 8), "fill": "#445566", "radius": 2},
                 {"kind": "circle", "box": (0, 0, 10, 10), "fill": "#778899"},
                 {"kind": "line", "box": (0, 0, 5, 5), "stroke": "#000000", "width": 1}]
        mvg = styles.to_mvg("#FFFFFF", prims)
        for word in ("rectangle 0,0 9,9", "roundrectangle 1,1 8,8 2,2", "ellipse 5.0,5.0 5.0,5.0 0,360", "line 0,0 5,5"):
            self.assertIn(word, mvg)
        self.assertIn("stroke-width 1", mvg)


if __name__ == "__main__":
    unittest.main()
