"""Her marks beyond the icon tile. make_symbol: the glyph alone, in its accent color on a clear background (a PNG and
an SVG). make_wordmark: that symbol beside the name, set in Samantha Sans. make_avatar: a friendly flat face from a name,
the same face every time. All draw with ImageMagick through tools_logo's MVG path, in the house style (one accent, flat,
no gradients), and write new files to the Desktop, never over one. Names are plain words only, so nothing odd reaches magick.
"""
import hashlib
import os
import re

import tools_glyphs
import tools_image
import tools_logo

FONT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "fonts", "SamanthaSans-Semibold.ttf")
_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9 .&'-]{0,23}")
_INK = "#111111"


def _fresh(name):
    """A new output path on the Desktop; a file of that name is never overwritten, it gets -2, -3 and so on."""
    base, ext = os.path.splitext(tools_image.output(name))
    path, n = base + ext, 2
    while os.path.exists(path):
        path, n = f"{base}-{n}{ext}", n + 1
    return path


def _symbol_layers(description):
    """The glyph for a subject with no tile: its white strokes turned into the palette's accent."""
    chose, layers = tools_logo._glyph_design(description)
    if "glyph" not in chose:  # no glyph and no model: her flower, which is already in color
        return chose, layers[1:], tools_glyphs.GLYPH_PALETTES["terracotta"][1]
    accent = tools_glyphs.GLYPH_PALETTES[chose["palette"]][1]
    return chose, [{k: (accent if v == "#FFFFFF" else v) for k, v in l.items()} for l in layers[1:]], accent


def _draw(layers, out):
    """Layers to a transparent 1024 PNG; the magick output, empty on success."""
    return tools_logo._run(["magick", "-size", "1024x1024", "xc:none", "-draw", tools_logo._mvg(layers), out], timeout=60)


def make_symbol(description):
    """Make a symbol: the bold glyph that means a subject, alone on a clear background in its accent color, as a PNG and an SVG on the Desktop. Never text."""
    chose, layers, _ = _symbol_layers(description)
    png = _fresh("samantha-symbol.png")
    result = _draw(layers, png)
    if not os.path.exists(png):
        return f"ImageMagick refused my design: {result[-300:]}"
    with open(png[:-4] + ".svg", "w") as f:
        f.write(tools_logo.layers_to_svg(layers, "Samantha's symbol"))
    return f"I went with {', '.join(f'{k} {v}' for k, v in chose.items())}. Symbol saved to {png} and {png[:-4]}.svg."


def make_wordmark(description):
    """Make a wordmark: a symbol for the subject beside its name set in Samantha Sans, as a PNG on the Desktop. The name is up to 24 letters, numbers and spaces; give it as 'for Name' or 'for Name, a bakery'."""
    name, _, about = description.partition(",")
    name = " ".join(name.split())
    if not _NAME.fullmatch(name):
        return "I can set a name of up to 24 letters, numbers and spaces."
    chose, layers, accent = _symbol_layers((about or name).strip())
    out = _fresh("samantha-wordmark.png")
    tmp = out[:-4] + ".parts"
    os.makedirs(tmp)
    try:
        sym, txt = os.path.join(tmp, "s.png"), os.path.join(tmp, "t.png")
        _draw(layers, sym)
        tools_logo._run(["magick", "-background", "none", "-fill", _INK, "-font", FONT, "-pointsize", "220", f"label:{name}", txt], timeout=60)
        if os.path.exists(sym) and os.path.exists(txt):
            sym2, txt2 = os.path.join(tmp, "s2.png"), os.path.join(tmp, "t2.png")
            tools_logo._run(["magick", sym, "-trim", "+repage", "-resize", "x300", sym2], timeout=60)
            tools_logo._run(["magick", txt, "-trim", "+repage", "-resize", "x200", txt2], timeout=60)
            tools_logo._run(["magick", sym2, "-size", "80x300", "xc:none", txt2, "-background", "none", "-gravity", "center", "+append",
                             "-bordercolor", "none", "-border", "60", out], timeout=60)
    finally:
        for f in os.listdir(tmp):
            os.remove(os.path.join(tmp, f))
        os.rmdir(tmp)
    if not os.path.exists(out):
        return "ImageMagick could not set that wordmark."
    return f"I paired {', '.join(f'{k} {v}' for k, v in chose.items())} with {name}. Wordmark saved to {out}."


# A face from a name: the same name is always the same face. Every feature is picked by bits of the name's hash.
_BACKS = ("#B5502C", "#0071E3", "#2F8F5B", "#D93A3F", "#111111", "#E0825A", "#2997FF")
_SKIN = ("#FFFFFF", "#F4D9C6", "#E6B994", "#C98B65", "#8D5A3C", "#F1E4D3")
_MOUTH = ("M 392 640 C 452 712 572 712 632 640", "M 392 660 L 632 660", "M 372 620 C 432 760 592 760 652 620")


def make_avatar(description):
    """Make an avatar: a friendly flat face drawn from a name, the same face every time, as a round PNG and an SVG on the Desktop. The name is up to 24 letters, numbers and spaces."""
    name = " ".join(description.split())
    if not _NAME.fullmatch(name):
        return "I can draw an avatar for a name of up to 24 letters, numbers and spaces."
    h = hashlib.sha256(name.lower().encode()).digest()
    back, skin, mouth = _BACKS[h[0] % len(_BACKS)], _SKIN[h[1] % len(_SKIN)], _MOUTH[h[2] % len(_MOUTH)]
    gap, eye = 104 + h[3] % 40, 44 + h[4] % 24
    face = {"type": "ellipse", "cx": 512, "cy": 540, "width": 600, "height": 640, "fill": skin}
    L = [{"type": "ellipse", "name": "Back", "cx": 512, "cy": 512, "width": 1000, "height": 1000, "fill": back}, face]
    for side in (-1, 1):
        L.append({"type": "ellipse", "cx": 512 + side * gap, "cy": 500, "width": eye, "height": eye * 1.15, "fill": _INK})
    L.append({"type": "path", "d": mouth, "stroke": _INK, "stroke_width": 36})
    extra = h[5] % 4
    if extra == 1:  # round glasses
        for side in (-1, 1):
            L.append({"type": "ellipse", "cx": 512 + side * gap, "cy": 500, "width": 150, "height": 150, "stroke": _INK, "stroke_width": 20})
        L.append({"type": "path", "d": f"M {512 - gap + 75} 500 L {512 + gap - 75} 500", "stroke": _INK, "stroke_width": 20})
    elif extra == 2:  # a cap
        L.append({"type": "path", "d": "M 232 440 C 232 250 792 250 792 440", "stroke": _INK, "stroke_width": 72})
    elif extra == 3:  # a tuft of hair
        L.append({"type": "path", "d": "M 432 250 C 452 170 552 170 592 250", "stroke": _INK, "stroke_width": 60})
    png = _fresh("samantha-avatar.png")
    result = tools_logo._run(["magick", "-size", "1024x1024", "xc:none", "-draw", tools_logo._mvg(L), png], timeout=60)
    if not os.path.exists(png):
        return f"ImageMagick refused my design: {result[-300:]}"
    with open(png[:-4] + ".svg", "w") as f:
        f.write(tools_logo.layers_to_svg(L, "Samantha's avatar"))
    return f"Drew an avatar for {name}. Saved to {png} and {png[:-4]}.svg."


TOOLS = (make_symbol, make_wordmark, make_avatar)

_I = re.I
# (pattern, tool name, what to hand it), same shape as tools_files.ROUTES. Their own words, so "make me a logo for" stays make_logo's.
ROUTES = (
    (re.compile(r"^(?:make|design|draw|create|build)(?: me)? (?:a |an )?(?:symbol|glyph) (?:for|of) (.+)$", _I), "make_symbol", lambda m: m.group(1).strip()),
    (re.compile(r"^(?:make|design|draw|create|build)(?: me)? (?:a |an )?(?:wordmark|logotype|logo with (?:text|a name|the name)) (?:for|of) (.+)$", _I), "make_wordmark",
     lambda m: m.group(1).strip()),
    (re.compile(r"^(?:make|design|draw|create|build)(?: me)? (?:a |an )?(?:avatar|profile picture|profile pic|pfp) (?:for|of) (.+)$", _I), "make_avatar",
     lambda m: m.group(1).strip()),
)
