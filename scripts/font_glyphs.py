"""Samantha Sans: the skeletons. Every glyph is a handful of centre lines, drawn at one stroke width W and nothing else
(gen_font.py strokes them with flat ends, joins and clips them). The whole face obeys these constraints:

  one stem W (84 regular, 118 semibold), horizontals the same, so the weights are one number
  x-height 500, cap height 700, ascender 740, descender -200; round letters overshoot 12 units top and bottom
  every bowl is the same superellipse (exponent N), the one shape her squircle icon and mascot are drawn with
  a flat, square cut at every end, never a ball, never a hook; diagonals are cut level by the clip box
  I has slabs, l has a tail, 1 has a flag and no foot, 0 is narrower than O: the passwords she prints read unambiguously

This file holds the shared pieces and the lowercase; font_caps.py has the capitals and figures, font_marks.py the punctuation.
A glyph is a function of the parameter object p returning a list of strokes (each a list of (x, y) points, drawn from
x = 0 as the glyph's outer left edge) and its table row says the shape class of its left and right sides, which is all
the spacing ever needs (gen_font.spacing). A stroke may be (points, box) to be cut to its own box, or ("-", box) to cut a
rectangle out of what is drawn, which is how every terminal gets its level cut.
"""
import math

N = 2.3  # the superellipse exponent: 2 is a circle, higher is a squircle; 2.3 is a Helvetica oval, not a squircle


def ell(cx, cy, rx, ry, a0=0.0, a1=360.0, step=4.0):
    """Points along a superellipse from angle a0 to a1 (degrees, either direction)."""
    k = max(2, int(abs(a1 - a0) / step))
    out = []
    for i in range(k + 1):
        t = math.radians(a0 + (a1 - a0) * i / k)
        c, s = math.cos(t), math.sin(t)
        out.append((cx + rx * math.copysign(abs(c) ** (2 / N), c), cy + ry * math.copysign(abs(s) ** (2 / N), s)))
    return out


def dline(p, x0, y0, x1, y1, e=220):
    """A diagonal centre line pushed e units past both ends; the glyph's clip box cuts the ends level."""
    d = math.hypot(x1 - x0, y1 - y0)
    ux, uy = (x1 - x0) / d, (y1 - y0) / d
    return [(x0 - ux * e, y0 - uy * e), (x1 + ux * e, y1 + uy * e)]


def hw(p, dx, dy):
    """Half the horizontal width of a diagonal stroke: how far its centre sits inside the outer edge."""
    return p.h * math.hypot(dx, dy) / abs(dy)


def bowl(p, x0, ow, top, bot):
    """A closed bowl whose outer box is x0..x0+ow by bot..top."""
    return ell(x0 + ow / 2, (top + bot) / 2, ow / 2 - p.h, (top - bot) / 2 - p.h)


def arch(p, ow, top_h):
    """The shoulder of n, h, m: an arc from the left stem round to the right stem, top_h below the x-height."""
    h, top = p.h, p.X - p.h + p.O
    ry = top_h
    return ell(ow / 2, top - ry, ow / 2 - h, ry, 180, 0)


def rot(strokes, cx, cy):
    """A glyph turned half a turn about (cx, cy): u from n, 9 from 6."""
    return [[(2 * cx - x, 2 * cy - y) for x, y in s] for s in strokes]


def bar(y, x0, x1):
    """A horizontal stroke."""
    return [(x0, y), (x1, y)]


def stem(x, y0, y1):
    """A vertical stroke."""
    return [(x, y0), (x, y1)]


def n_(p, ow=450):
    """n: stem and arch."""
    h = p.h
    a = arch(p, ow, 175)
    return [stem(h, 0, p.X), a + [(ow - h, 0)]]


def h_(p):
    """h: n with an ascender."""
    s = n_(p)
    s[0] = stem(p.h, 0, p.A)
    return s


def m_(p):
    """m: two arches on three stems."""
    h, ow = p.h, 720
    rx, cy = (ow / 2 - h) / 2, p.X - h + p.O - 175
    a1 = ell(h + rx, cy, rx, 175, 180, 0)
    a2 = ell(ow / 2 + rx, cy, rx, 175, 180, 0)
    return [stem(h, 0, p.X), a1 + [(ow / 2, 0)], a2 + [(ow - h, 0)]]


def r_(p):
    """r: stem and a short shoulder."""
    h, ow = p.h, 330
    return [stem(h, 0, p.X), ell(ow / 2 + h / 2, p.X - h + p.O - 175, ow / 2 - h / 2 - h, 175, 180, 62)]


def u_(p):
    """u: n turned half a turn."""
    return rot(n_(p), 225, p.X / 2)


def o_(p, ow=505):
    """o."""
    return [bowl(p, 0, ow, p.X + p.O, -p.O)]


def c_(p):
    """c: the o with a level cut at each end, the way a grotesque closes its terminals."""
    ow = 480
    cy = p.X / 2
    return [bowl(p, 0, ow, p.X + p.O, -p.O), ("-", (ow / 2 + 20, cy - 98, 4000, cy + 128))]


def e_(p):
    """e: the o, a bar, and a level cut under the bar."""
    ow, h = 490, p.h
    cy = p.X / 2
    return [bowl(p, 0, ow, p.X + p.O, -p.O), ("-", (ow / 2 + 20, cy - 108, 4000, cy + 8)), bar(cy + 8 + h - h, h, ow - h)][:2] + [bar(cy + 8, h, ow - h)]


def a_(p):
    """a: two storeys, a bowl that joins the stem and a hood over it, as in every grotesque."""
    ow, h, X = 465, p.h, p.X
    top = X - h + p.O
    ry = 150
    hood = ell(ow / 2 - 8, top - ry, ow / 2 - 8 - h, ry, 158, 0)
    return [hood + [(ow - h, 0)], bowl(p, 6, ow - 6, 292, -p.O)]


def d_(p):
    """d."""
    ow = 490
    return [bowl(p, 0, ow, p.X + p.O, -p.O), stem(ow - p.h, 0, p.A)]


def b_(p):
    """b."""
    ow = 490
    return [bowl(p, 0, ow, p.X + p.O, -p.O), stem(p.h, 0, p.A)]


def p_(p):
    """p."""
    ow = 490
    return [bowl(p, 0, ow, p.X + p.O, -p.O), stem(p.h, p.D, p.X)]


def q_(p):
    """q."""
    ow = 490
    return [bowl(p, 0, ow, p.X + p.O, -p.O), stem(ow - p.h, p.D, p.X)]


def g_(p):
    """g: a bowl, a stem and a hook that opens left."""
    ow, h, r = 490, p.h, 150
    yb = p.D + h
    return [bowl(p, 0, ow, p.X + p.O, -p.O), stem(ow - h, yb + r, p.X), ell(ow - h - r, yb + r, r, r, 0, -135)]


def i_(p):
    """i: a stem and a square dot."""
    return [stem(p.h, 0, p.X), stem(p.h, 612, 712)]


def j_(p):
    """j: i with a hook below."""
    h, r = p.h, 140
    yb = p.D + h
    return [stem(h + r, yb + r, p.X), ell(h + r - r, yb + r, r, r, 0, -90) + [(-30, yb)], stem(h + r, 612, 712)]


def l_(p):
    """l: a plain stem; the capital I has slabs, so the two never read alike."""
    return [stem(p.h, 0, p.A)]


def f_(p):
    """f: a stem with a hook and a crossbar."""
    h, r = p.h, 130
    return [stem(h + 40, 0, p.A - h - r) + [], ell(h + 40 + r, p.A - h - r, r, r, 180, 90) + [(h + 40 + r + 70, p.A - h)],
            bar(p.X - h, 0, 280)]


def t_(p):
    """t: a stem curving into the baseline, and a crossbar."""
    h, r = p.h, 120
    return [stem(h + 70, 650, h + r) + [], ell(h + 70 + r, h + r, r, r, 180, 270) + [(h + 70 + r + 50, h)], bar(p.X - h, 0, 300)]


def s_(p, w=440, top=None, bot=None):
    """s: one arc and its half turn about the middle, joined by a straight spine that falls a little to the right."""
    h = p.h
    top = p.X + p.O if top is None else top
    bot = -p.O if bot is None else bot
    ry = (top - bot - 2 * h) / 4
    rx = w / 2 - h
    cx, cy = w / 2, (top + bot) / 2
    up = ell(cx, top - h - ry, rx, ry, 30, 238)
    low = [(2 * cx - x, 2 * cy - y) for x, y in reversed(up)]
    return [up + low]


def kk(p, ow, hi, ya):
    """The arm and leg shared by k and K: both leave the stem at one point, height ya, so there is no seam to see."""
    h = p.h
    jx = h + 20
    xa = ow - hw(p, ow - jx, hi - ya)
    xl = ow - hw(p, ow - jx, ya) + 10
    return [(dline(p, xa, hi, jx, ya), (h, 0, 4000, hi)), (dline(p, jx, ya, xl, 0), (h, 0, 4000, hi))]


def k_(p):
    """k."""
    return [stem(p.h, 0, p.A)] + kk(p, 470, p.X, 200)


def vx(p, ow, y1, hi, lo=0):
    """The two strokes of a V between y=lo and y=hi, its outer top width ow."""
    c = ow / 2
    xt = hw(p, c, hi - lo) + 4
    return [dline(p, xt, hi, c, lo), dline(p, ow - xt, hi, c, lo)]


def v_(p):
    """v."""
    return vx(p, 500, 0, p.X)


def w_(p):
    """w: two vs sharing a stroke."""
    ow, X = 760, p.X
    xt = hw(p, 190, X) + 4
    return [dline(p, xt, X, ow / 4, 0), dline(p, ow / 2 - xt / 2 + 0, X, ow / 4, 0), dline(p, ow / 2 + xt / 2, X, 3 * ow / 4, 0),
            dline(p, ow - xt, X, 3 * ow / 4, 0)]


def x_(p):
    """x."""
    ow, X = 490, p.X
    xt = hw(p, ow - 2 * p.h, X) + 4
    return [dline(p, xt, X, ow - xt, 0), dline(p, ow - xt, X, xt, 0)]


def y_(p):
    """y: v with a long right leg."""
    ow, X = 500, p.X
    xt = hw(p, 250, X) + 4
    mx = ow - xt + (90 - (ow - xt)) * (X - 120) / (X - p.D - 20)
    return [(dline(p, xt, X, mx, 120), (-2000, 120, 4000, X)), (dline(p, ow - xt, X, 90, p.D + 20), (-2000, p.D, 4000, X))]


def z_(p):
    """z."""
    ow, h = 450, p.h
    return [bar(p.X - h, 0, ow), (dline(p, ow - 65, p.X - h, 65, h), (0, 0, ow, p.X)), bar(h, 0, ow)]


# name -> (function, left class, right class, clip box key). Classes: s straight stem, r round, d open or diagonal.
# Clip boxes: x = 0..x-height, c = 0..cap, a = 0..ascender, xd = descender..x-height, p = whole em.
LOWER = {
    "n": (n_, "s", "s", ""), "h": (h_, "s", "s", ""), "m": (m_, "s", "s", ""), "r": (r_, "s", "r", ""),
    "u": (u_, "s", "s", ""), "o": (o_, "r", "r", ""), "c": (c_, "r", "d", ""), "e": (e_, "r", "r", ""),
    "a": (a_, "r", "s", ""), "d": (d_, "r", "s", ""), "b": (b_, "s", "r", ""), "p": (p_, "s", "r", ""),
    "q": (q_, "r", "s", ""), "g": (g_, "r", "s", ""), "i": (i_, "s", "s", ""), "j": (j_, "d", "s", ""),
    "l": (l_, "s", "d", ""), "f": (f_, "d", "r", ""), "t": (t_, "d", "r", ""), "s": (s_, "r", "r", ""),
    "k": (k_, "s", "d", "a"), "v": (v_, "d", "d", "x"), "w": (w_, "d", "d", "x"), "x": (x_, "d", "d", "x"),
    "y": (y_, "d", "d", "xd"), "z": (z_, "d", "d", "x")}
