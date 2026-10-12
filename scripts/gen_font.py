"""Samantha Sans, built from one table of constraints (scripts/font_glyphs.py draws the skeletons, this strokes them).

    python3 scripts/gen_font.py            # writes web/fonts/SamanthaSans-{Regular,Medium,Semibold}.{ttf,woff2}
    python3 scripts/gen_font.py --check    # builds in memory twice: same bytes, tabular digits, I l 1 O 0 all different

Proportional by rule, not by hand: a glyph's side bearings come from the shape class of each edge (a straight stem needs
the most air, a round the least, a diagonal or an open edge almost none), then a short kerning table fixes the classic
pairs. Figures are the one exception on purpose: they share an advance so a column of numbers never jitters. Needs
fonttools, brotli and skia-pathops (pip install fonttools brotli skia-pathops), none of which the apps themselves need.
"""
import io
import os
import sys

import pathops
from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import font_caps  # noqa: E402
import font_glyphs as fg  # noqa: E402
import font_marks  # noqa: E402

GLYPHS = {**fg.LOWER, **font_caps.CAPS, **font_marks.MARKS}

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "web", "fonts")
WEIGHTS = {"Regular": (84, 400), "Medium": (100, 500), "Semibold": (118, 600)}   # name: (stem, usWeightClass)
SIDE = {"s": 0.9, "r": 0.42, "d": 0.1}      # side bearing as a share of the stem, by the shape class of the edge
CAPS = 1.2                                   # capitals and figures get a little more air than the lowercase
FIGURE = 580                                 # the one advance every figure shares
SPACE = 260
CLIPS = {"": None, "x": (0, 520), "c": (0, 700), "a": (0, 740), "xd": (-200, 520), "p": (-420, 1040)}
KERN = [("A", "V", -70), ("A", "T", -80), ("A", "Y", -80), ("A", "W", -45), ("V", "A", -70), ("T", "A", -80), ("Y", "A", -80),
        ("W", "A", -45), ("L", "T", -90), ("L", "V", -80), ("L", "Y", -90), ("L", "W", -50), ("T", "o", -60), ("T", "a", -60),
        ("T", "e", -60), ("T", "u", -35), ("T", "r", -35), ("V", "o", -45), ("V", "a", -45), ("V", "e", -45), ("Y", "o", -60),
        ("Y", "e", -60), ("P", "A", -70), ("F", "A", -60), ("r", ".", -50), ("r", ",", -50), ("y", ".", -60), ("y", ",", -60),
        ("T", ".", -80), ("T", ",", -80), ("F", ".", -70), ("P", ".", -80), ("v", ".", -55), ("w", ".", -45)]


class Params:
    """The numbers every glyph is drawn from; only the stem changes between weights."""

    def __init__(self, stem):
        """Set the stem and its half, and the fixed vertical metrics."""
        self.W, self.h = stem, stem / 2
        self.X, self.C, self.A, self.D, self.O = 520, 700, 740, -200, 12


def rect(x0, y0, x1, y1):
    """A rectangle as a pathops Path."""
    r = pathops.Path()
    r.moveTo(x0, y0); r.lineTo(x1, y0); r.lineTo(x1, y1); r.lineTo(x0, y1); r.close()
    return r


def outline(strokes, p, clip):
    """The union of every stroke, flat-ended and mitered, cut to the clip box: one clean pathops Path."""
    whole = pathops.Path()
    for s in strokes:
        box = None
        if isinstance(s, tuple) and s[0] == "-":   # ("-", box): cut a rectangle out of what is drawn so far, a level terminal
            whole = pathops.op(whole, rect(*s[1]), pathops.PathOp.DIFFERENCE, fix_winding=True)
            continue
        if isinstance(s, tuple):   # (points, (x0, y0, x1, y1)): this one stroke is cut to its own box before the union
            s, box = s
        sp = pathops.Path()
        sp.moveTo(*s[0])
        for pt in s[1:]:
            sp.lineTo(*pt)
        if len(s) > 8 and abs(s[0][0] - s[-1][0]) < 1e-6 and abs(s[0][1] - s[-1][1]) < 1e-6:
            sp.close()
        sp.stroke(p.W, pathops.LineCap.BUTT_CAP, pathops.LineJoin.MITER_JOIN, 4)
        if box:
            sp = pathops.op(sp, rect(*box), pathops.PathOp.INTERSECTION, fix_winding=True)
        whole = pathops.op(whole, sp, pathops.PathOp.UNION, fix_winding=True)
    if clip:
        whole = pathops.op(whole, rect(-2000, clip[0], 4000, clip[1]), pathops.PathOp.INTERSECTION, fix_winding=True)
    return whole


def spacing(path, cls, stem, caps):
    """(shift, advance) that gives the outline its side bearings, from the shape class of each edge."""
    x0, _, x1, _ = path.bounds
    k = stem * (CAPS if caps else 1.0)
    lsb, rsb = SIDE[cls[0]] * k, SIDE[cls[1]] * k
    return lsb - x0, (x1 - x0) + lsb + rsb


def glyph_set(stem):
    """{char: (TrueType glyph, advance)} for one weight."""
    p, glyphs = Params(stem), {}
    for ch, (fn, left, right, clip) in GLYPHS.items():
        path = outline(fn(p), p, CLIPS[clip])
        caps = ch.isupper() or ch.isdigit()
        shift, adv = spacing(path, left + right, stem, caps)
        if ch.isdigit():
            x0, _, x1, _ = path.bounds
            shift, adv = (FIGURE - (x1 - x0)) / 2 - x0, FIGURE
        pen = TTGlyphPen(None)
        path.draw(TransformPen(Cu2QuPen(pen, 1.0, reverse_direction=False), (1, 0, 0, 1, shift, 0)))
        glyphs[ch] = (pen.glyph(), round(adv))
    return glyphs


def name_of(ch):
    """The glyph name for a character."""
    return "space" if ch == " " else f"uni{ord(ch):04X}"


def build(stem, weight, style):
    """One weight as an in-memory FontBuilder."""
    glyphs = glyph_set(stem)
    order = [".notdef", "space"] + [name_of(c) for c in glyphs]
    fb = FontBuilder(1000, isTTF=True)
    fb.setupGlyphOrder(order)
    fb.setupCharacterMap({ord(c): name_of(c) for c in glyphs} | {32: "space", 0xA0: "space"})
    empty = TTGlyphPen(None).glyph()
    table = {".notdef": empty, "space": empty} | {name_of(c): g for c, (g, _) in glyphs.items()}
    fb.setupGlyf(table)
    fb.setupHorizontalMetrics({".notdef": (500, 0), "space": (SPACE, 0)} | {name_of(c): (a, round(g.xMin)) for c, (g, a) in glyphs.items()})
    fb.setupHorizontalHeader(ascent=960, descent=-240, lineGap=0)
    fb.setupNameTable({"familyName": "Samantha Sans", "styleName": style, "uniqueFontIdentifier": f"SamanthaSans-{style}",
                       "fullName": f"Samantha Sans {style}", "psName": f"SamanthaSans-{style}", "version": "Version 1.000"})
    fb.setupOS2(sTypoAscender=960, sTypoDescender=-240, sTypoLineGap=0, usWinAscent=1000, usWinDescent=300, usWeightClass=weight,
                sxHeight=520, sCapHeight=700, achVendID="SMTH", fsType=0)
    fb.setupPost()
    fb.font["head"].created = fb.font["head"].modified = 3_700_000_000   # fixed, so every build is the same bytes
    pairs = "\n".join(f"    pos {name_of(a)} {name_of(b)} {round(v * stem / 84)};" for a, b, v in KERN)
    addOpenTypeFeaturesFromString(fb.font, f"feature kern {{\n{pairs}\n}} kern;")
    return fb


def to_bytes(fb, woff2=False):
    """The font as TTF or WOFF2 bytes."""
    if woff2:
        fb.font.flavor = "woff2"
    buf = io.BytesIO()
    fb.save(buf)
    fb.font.flavor = None
    return buf.getvalue()


def check():
    """Self-check: identical bytes twice, one advance for every figure, and the look-alikes drawn differently."""
    a, b = to_bytes(build(84, 400, "Regular")), to_bytes(build(84, 400, "Regular"))
    assert a == b, "the build is not deterministic"
    glyphs = glyph_set(84)
    assert len({glyphs[d][1] for d in "0123456789"}) == 1, "figures are not tabular"
    shapes = {c: glyphs[c][0].coordinates.array.tobytes() for c in "Il1O0"}
    assert len(set(shapes.values())) == 5, "two of I l 1 O 0 are drawn the same"
    assert glyphs["O"][1] > glyphs["0"][1] and glyphs["i"][1] < glyphs["m"][1]
    print(f"font ok: {len(glyphs)} glyphs, {len(a)} bytes regular")


def main():
    """Write every weight to web/fonts, or run the check."""
    if "--check" in sys.argv:
        return check()
    os.makedirs(OUT, exist_ok=True)
    for style, (stem, weight) in WEIGHTS.items():
        fb = build(stem, weight, style)
        for ext, w2 in (("ttf", False), ("woff2", True)):
            with open(os.path.join(OUT, f"SamanthaSans-{style}.{ext}"), "wb") as f:
                f.write(to_bytes(fb, w2))
        print(f"SamanthaSans-{style}: stem {stem}")


if __name__ == "__main__":
    main()
