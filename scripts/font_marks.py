"""Samantha Sans: punctuation and symbols, drawn the same way as the letters (see font_glyphs.py)."""
import math  # noqa: F401

from font_glyphs import bar, bowl, dline, ell, hw, kk, rot, s_, stem, vx  # noqa: F401


# ---- punctuation ---------------------------------------------------------------------------------------------------

def dot(p):
    """The full stop: a square the stroke wide."""
    return [stem(p.h, 0, p.W)]


def comma(p):
    """The comma: a dot with a tail."""
    return [stem(p.h, 0, p.W), dline(p, p.h, 0, p.h - 40, -110, 0)[0:2]]


def colon(p):
    """The colon."""
    return [stem(p.h, 0, p.W), stem(p.h, p.X - p.W, p.X)]


def semi(p):
    """The semicolon."""
    return comma(p) + [stem(p.h, p.X - p.W, p.X)]


def excl(p):
    """The exclamation mark."""
    return [stem(p.h, 200, p.C), stem(p.h, 0, p.W)]


def quest(p):
    """The question mark: a hook that comes down to a stem, and a dot."""
    ow, h = 430, p.h
    top, ry = p.C - h + p.O, 170
    return [ell(ow / 2, top - ry, ow / 2 - h, ry, 165, -90) + [(ow / 2, 250)], stem(ow / 2, 0, p.W)]


def apos(p):
    """The straight apostrophe."""
    return [stem(p.h, 440, p.C)]


def dquote(p):
    """The straight double quote."""
    return [stem(p.h, 440, p.C), stem(p.h + 130, 440, p.C)]


def hyphen(p):
    """The hyphen."""
    return [bar(p.X * 0.47, 0, 260)]


def endash(p):
    """The en dash."""
    return [bar(p.X * 0.47, 0, 480)]


def emdash(p):
    """The em dash."""
    return [bar(p.X * 0.47, 0, 900)]


def lparen(p):
    """The left parenthesis."""
    return [ell(260, 270, 200 - p.h, 480, 120, 240, 3)]


def rparen(p):
    """The right parenthesis."""
    return rot(lparen(p), 130, 270)


def lbrack(p):
    """The left square bracket."""
    return [[(220, p.C + 60 - p.h), (p.h, p.C + 60 - p.h), (p.h, p.D + 20 + p.h), (220, p.D + 20 + p.h)]]


def rbrack(p):
    """The right square bracket."""
    return rot(lbrack(p), 110, 270)


def slash(p):
    """The slash."""
    return [dline(p, 340, p.C + 40, 30, p.D + 80, 0)[:2]]


def plus(p):
    """The plus."""
    return [bar(p.X * 0.55, 0, 460), stem(230, p.X * 0.55 - 230, p.X * 0.55 + 230)]


def equals(p):
    """The equals sign."""
    return [bar(p.X * 0.55 - 90, 0, 460), bar(p.X * 0.55 + 90, 0, 460)]


def underscore(p):
    """The underscore."""
    return [bar(-120, 0, 560)]


def times(p):
    """The multiplication sign."""
    return [dline(p, 20, p.X * 0.55 - 190, 440, p.X * 0.55 + 190, 0)[:2], dline(p, 20, p.X * 0.55 + 190, 440, p.X * 0.55 - 190, 0)[:2]]


def degree(p):
    """The degree sign."""
    return [ell(110, p.C - 110, 110 - p.h, 110 - p.h)]


def ellipsis(p):
    """The ellipsis: three full stops."""
    return [stem(p.h + i * 210, 0, p.W) for i in range(3)]


def lsq(p):
    """The left single curly quote."""
    return [stem(p.h + 0, 440, p.C), dline(p, p.h, 440, p.h + 40, 400, 0)[:2]]


def percent(p):
    """The percent sign: two rings and a slash."""
    return [bowl(p, 0, 270, p.C + p.O, 380), bowl(p, 560, 270, 320, -p.O), dline(p, 640, p.C, 190, 0, 0)[:2]]


def at(p):
    """The at sign: a nearly closed ring round a small a."""
    h = p.h
    return [ell(420, 280, 420 - h, 400 - h, -16, 316), bowl(p, 250, 270, 420, 130), stem(520 - h, 130, 420)]


def hash_(p):
    """The number sign."""
    return [stem(190, 20, 620), stem(390, 20, 620), bar(220, 40, 560), bar(420, 40, 560)]


def amp(p):
    """The ampersand: two bowls and a leg."""
    return [bowl(p, 60, 300, p.C + p.O, 380), bowl(p, 0, 440, 400, -p.O), (dline(p, 130, 450, 640, 0, 0)[:2], (0, 0, 4000, 4000))]


def pipe(p):
    """The vertical bar."""
    return [stem(p.h, p.D, p.C + 60)]


def lt(p):
    """The less-than sign."""
    return [[(440, p.X * 0.55 + 190), (20, p.X * 0.55), (440, p.X * 0.55 - 190)]]


def gt(p):
    """The greater-than sign."""
    return rot(lt(p), 230, p.X * 0.55)


def tilde(p):
    """The tilde."""
    return [ell(110, 360, 110, 60, 180, 0)[::-1] + [(330, 360)] + ell(330 + 110, 360, 110, 60, 180, 360)]


def dollar(p):
    """The dollar sign."""
    return s_(p, 480, p.C - 40, 40) + [stem(240, p.D + 100, p.C + 80)]


def caret(p):
    """The circumflex."""
    return [[(20, 420), (210, p.C + 40), (400, 420)]]


def backtick(p):
    """The grave accent."""
    return [dline(p, 20, p.C + 60, 160, p.C - 70, 0)[:2]]


MARKS = {
    ".": (dot, "s", "s", ""), ",": (comma, "s", "s", "p"), ":": (colon, "s", "s", ""), ";": (semi, "s", "s", "p"),
    "!": (excl, "s", "s", ""), "?": (quest, "r", "d", ""), "'": (apos, "s", "s", ""), '"': (dquote, "s", "s", ""),
    "-": (hyphen, "d", "d", ""), "–": (endash, "d", "d", ""), "—": (emdash, "d", "d", ""),
    "(": (lparen, "d", "d", ""), ")": (rparen, "d", "d", ""), "[": (lbrack, "s", "d", ""),
    "]": (rbrack, "d", "s", ""), "/": (slash, "d", "d", "p"), "+": (plus, "d", "d", ""), "=": (equals, "d", "d", ""),
    "_": (underscore, "d", "d", ""), "×": (times, "d", "d", "p"), "°": (degree, "r", "r", ""),
    "…": (ellipsis, "s", "s", ""), "‘": (lsq, "s", "s", "p"), "’": (lsq, "s", "s", "p"),
    "%": (percent, "r", "r", "p"), "@": (at, "r", "r", ""), "#": (hash_, "d", "d", ""), "&": (amp, "r", "d", "p"),
    "|": (pipe, "s", "s", ""), "<": (lt, "d", "d", ""), ">": (gt, "d", "d", ""), "~": (tilde, "d", "d", ""),
    "$": (dollar, "r", "r", ""), "^": (caret, "d", "d", ""), "`": (backtick, "d", "d", "p")}
