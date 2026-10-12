"""Samantha Sans: the capitals and the figures, drawn the same way as the lowercase (see font_glyphs.py)."""
import math  # noqa: F401

from font_glyphs import bar, bowl, dline, ell, hw, kk, rot, s_, stem, vx  # noqa: F401


# ---- capitals -----------------------------------------------------------------------------------------------------

def tops(p):
    """The capital's skeleton top and bottom."""
    return p.C - p.h, p.h


def A_(p):
    """A."""
    ow, C = 640, p.C
    xt = hw(p, ow / 2, C) + 4
    y = 230
    xl = xt + (ow / 2 - xt) * y / C
    return [dline(p, xt, 0, ow / 2, C), dline(p, ow - xt, 0, ow / 2, C), bar(y, xl, ow - xl)]


def dbowl(p, xs, yt, yb, xr):
    """A D-shaped bowl hanging off a stem at x=xs between skeleton heights yt and yb, reaching skeleton x=xr."""
    ry = (yt - yb) / 2
    rx = min(ry * 0.92, xr - xs - 30)
    return [(xs, yt), (xr - rx, yt)] + ell(xr - rx, (yt + yb) / 2, rx, ry, 90, -90) + [(xs, yb)]


def B_(p):
    """B."""
    h, C = p.h, p.C
    ym = C / 2 - 4
    return [stem(h, 0, C), dbowl(p, h, C - h, ym + h / 2 + 2, 520), dbowl(p, h, ym - h / 2 + 2, h, 560)]


def C_(p):
    """C: the O with level terminals."""
    ow = 610
    cy = p.C / 2
    return [bowl(p, 0, ow, p.C + p.O, -p.O), ("-", (ow / 2 + 20, cy - 150, 4000, cy + 170))]


def D_(p):
    """D."""
    return [stem(p.h, 0, p.C), dbowl(p, p.h, p.C - p.h, p.h, 600)]


def E_(p):
    """E."""
    h, C = p.h, p.C
    return [stem(h, 0, C), bar(C - h, h, 500), bar(C / 2, h, 450), bar(h, h, 510)]


def F_(p):
    """F."""
    h, C = p.h, p.C
    return [stem(h, 0, C), bar(C - h, h, 500), bar(C / 2 + 10, h, 450)]


def G_(p):
    """G: a C with a shelf."""
    ow = 620
    cy = p.C / 2
    return [bowl(p, 0, ow, p.C + p.O, -p.O), ("-", (ow / 2 + 20, cy - 12, 4000, cy + 170)), bar(cy - 10 + 10, ow / 2 + 20, ow - p.h)][:2] + [bar(cy, ow / 2 + 10, ow - p.h), stem(ow - p.h, p.h, cy)]


def H_(p):
    """H."""
    h, ow = p.h, 630
    return [stem(h, 0, p.C), stem(ow - h, 0, p.C), bar(p.C / 2, h, ow - h)]


def I_(p):
    """I: a stem with slabs, so it is never a lowercase l or a one."""
    h, x = p.h, 100
    return [stem(x, 0, p.C), bar(h, 0, 2 * x), bar(p.C - h, 0, 2 * x)]


def J_(p):
    """J."""
    ow, h = 440, p.h
    r = 150
    return [stem(ow - h, p.C, r), ell(ow - h - r, r, r, r, 0, -150)]


def K_(p):
    """K."""
    return [stem(p.h, 0, p.C)] + kk(p, 600, p.C, 260)


def L_(p):
    """L."""
    return [stem(p.h, 0, p.C), bar(p.h, p.h, 470)]


def M_(p):
    """M."""
    h, ow, C = p.h, 800, p.C
    box = (h, 0, ow - h, C)
    return [stem(h, 0, C), stem(ow - h, 0, C), (dline(p, h, C, ow / 2, 0), box), (dline(p, ow - h, C, ow / 2, 0), box)]


def N_(p):
    """N."""
    h, ow = p.h, 650
    return [stem(h, 0, p.C), stem(ow - h, 0, p.C), (dline(p, h, p.C, ow - h, 0), (h, 0, ow - h, p.C))]


def O_(p):
    """O: wider than the zero."""
    return [bowl(p, 0, 650, p.C + p.O, -p.O)]


def P_(p):
    """P."""
    h, C = p.h, p.C
    return [stem(h, 0, C), dbowl(p, h, C - h, 270, 540)]


def Q_(p):
    """Q."""
    return O_(p) + [dline(p, 420, 190, 640, -40, 20)]


def R_(p):
    """R."""
    h, C = p.h, p.C
    return [stem(h, 0, C), dbowl(p, h, C - h, 290, 530), dline(p, 300, 290, 560 - hw(p, 260, 290), 0, 20)]


def S_(p):
    """S."""
    return s_(p, 520, p.C + p.O, -p.O)


def T_(p):
    """T."""
    ow = 590
    return [bar(p.C - p.h, 0, ow), stem(ow / 2, 0, p.C - p.h)]


def U_(p):
    """U."""
    h, ow = p.h, 600
    ry = 250
    cy = h - p.O + ry
    return [stem(h, p.C, cy), ell(ow / 2, cy, ow / 2 - h, ry, 180, 360), stem(ow - h, cy, p.C)]


def V_(p):
    """V."""
    return vx(p, 640, 0, p.C)


def W_(p):
    """W."""
    ow, C = 940, p.C
    xt = hw(p, 235, C) + 4
    return [dline(p, xt, C, ow / 4, 0), dline(p, ow / 2 - xt / 2, C, ow / 4, 0), dline(p, ow / 2 + xt / 2, C, 3 * ow / 4, 0),
            dline(p, ow - xt, C, 3 * ow / 4, 0)]


def X_(p):
    """X."""
    ow, C = 620, p.C
    xt = hw(p, ow - 2 * p.h, C) + 4
    return [dline(p, xt, C, ow - xt, 0), dline(p, ow - xt, C, xt, 0)]


def Y_(p):
    """Y."""
    ow, C = 620, p.C
    xt = hw(p, 310, 300) + 4
    return [(dline(p, xt, C, ow / 2, 280), (-2000, -2000, ow / 2, C)), (dline(p, ow - xt, C, ow / 2, 280), (ow / 2, -2000, 4000, C)), stem(ow / 2, 0, 290)]


def Z_(p):
    """Z."""
    ow, h = 560, p.h
    return [bar(p.C - h, 0, ow), (dline(p, ow - 75, p.C - h, 75, h), (0, 0, ow, p.C)), bar(h, 0, ow)]


# ---- figures: every digit has the same advance (tabular), so a column of numbers never jitters -------------------

def zero(p):
    """0: narrower than O, an upright oval."""
    return [bowl(p, 0, 470, p.C + p.O, -p.O)]


def one(p):
    """1: a stem and a flag, no foot."""
    x = 190
    return [stem(x, 0, p.C), (dline(p, x, p.C, x - 170, p.C - 150, 10), (0, 0, x + 1, p.C))]


def two(p):
    """2."""
    ow, h = 470, p.h
    rx, ry = ow / 2 - h, 140
    return [ell(ow / 2, p.C - ry - 6 + p.O, rx, ry + 6, 160, -30) + [(h + 20, h + 40), (h, h)], bar(h, h, ow)]


def three(p):
    """3: two arcs that meet on one point at the middle."""
    ow, h = 470, p.h
    top, J = p.C - h + p.O, 372
    return [ell(ow / 2, (J + top) / 2, ow / 2 - h - 30, (top - J) / 2, 150, -90), ell(ow / 2, (J + h - p.O) / 2, ow / 2 - h, (J - h + p.O) / 2, 90, -150)]


def four(p):
    """4."""
    ow, h = 500, p.h
    return [stem(ow - 150, 0, p.C), (dline(p, ow - 150, p.C, 20, 200, 10), (0, 0, ow, p.C)), bar(200, 0, ow)]


def five(p):
    """5."""
    ow, h = 470, p.h
    return [bar(p.C - h, 70, ow - 20), stem(h + 70, p.C - h, 370), ell(ow / 2 + 4, 235 - 0, ow / 2 - h - 4, 235 + p.O - h, 150, -150)]


def six(p):
    """6: a lower bowl and a stroke rising from it."""
    ow, h = 470, p.h
    top, cy = p.C - h + p.O, 190
    return [bowl(p, 0, ow, 380, -p.O), stem(h, cy, 372), ell(ow / 2 + 70, 372, ow / 2 + 70 - h, top - 372, 180, 52)]


def seven(p):
    """7."""
    ow, h = 470, p.h
    return [bar(p.C - h, 0, ow), (dline(p, ow - 20, p.C - h, 140, 0, 10), (0, 0, ow, p.C))]


def eight(p):
    """8: two bowls stacked."""
    ow, h = 450, p.h
    return [bowl(p, 20, ow - 40, p.C + p.O, 380 - h), bowl(p, 0, ow, 380 + h, -p.O)]


def nine(p):
    """9: a six turned half a turn."""
    return rot(six(p), 235, p.C / 2)


CAPS = {
    "A": (A_, "d", "d", "c"), "B": (B_, "s", "r", ""), "C": (C_, "r", "d", ""), "D": (D_, "s", "r", ""),
    "E": (E_, "s", "d", ""), "F": (F_, "s", "d", ""), "G": (G_, "r", "s", ""), "H": (H_, "s", "s", ""),
    "I": (I_, "s", "s", ""), "J": (J_, "d", "r", ""), "K": (K_, "s", "d", "c"), "L": (L_, "s", "d", ""),
    "M": (M_, "s", "s", "c"), "N": (N_, "s", "s", "c"), "O": (O_, "r", "r", ""), "P": (P_, "s", "r", ""),
    "Q": (Q_, "r", "r", "p"), "R": (R_, "s", "d", "c"), "S": (S_, "r", "r", ""), "T": (T_, "d", "d", ""),
    "U": (U_, "s", "s", ""), "V": (V_, "d", "d", "c"), "W": (W_, "d", "d", "c"), "X": (X_, "d", "d", "c"),
    "Y": (Y_, "d", "d", "c"), "Z": (Z_, "d", "d", "c"), "0": (zero, "r", "r", ""), "1": (one, "d", "d", "c"),
    "2": (two, "r", "s", ""), "3": (three, "r", "r", ""), "4": (four, "d", "d", "c"), "5": (five, "s", "r", ""),
    "6": (six, "r", "r", ""), "7": (seven, "d", "d", "c"), "8": (eight, "r", "r", ""), "9": (nine, "r", "r", "")}
