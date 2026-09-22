"""Samantha's logo designer and painter: make_logo (golden spiral by default, complex or simple on request, always an
icon, never text) and paint_image (a photo rebuilt from squares). Her model picks the dials; this code lays out the layers.
Split out of tools.py, which re-exports every name here.
"""
import json
import math
import os
import re
import shutil
import sys
import urllib.request

HEADLESS = os.environ.get("SAMANTHA_HEADLESS") == "1"


def _tools():
    """The tools module, fetched when a function runs, never at import: tools imports this file."""
    import tools
    return tools


def _run(argv, timeout=10):
    """tools._run, looked up when called, so a test that patches tools._run also stubs the logo and paint calls."""
    return _tools()._run(argv, timeout=timeout)


def _inside_home(path):
    """tools._inside_home: a path inside the home folder, or None."""
    return _tools()._inside_home(path)


PXM = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pixelmator", "pxm.py")
# A 1.7B picks well and composes badly: left to write layers itself it put a
# pink rectangle over everything and set "TURING" at 360pt, and pxm rejected
# the spec. So she chooses, the harness lays out. Three choices, all enums.
PALETTES = {"ember": ("#15110D", "#F4C893", "#E8A96A"), "ink": ("#101418", "#FFFFFF", "#F2B33D"),
            "forest": ("#0F1A14", "#E9F2EA", "#6FBF73"), "signal": ("#16161A", "#FFFFFF", "#E5484D"),
            "paper": ("#F3EDE2", "#1A1410", "#C2562D")}
_LOGO_SCHEMA = {"type": "object", "required": ["palette", "motif"], "properties": {
    "palette": {"enum": list(PALETTES)}, "motif": {"enum": ["ring", "spark", "bars", "dot"]}}}
_WANTS_SIMPLE = re.compile(r"\b(?:simple|minimal|minimalist|clean|plain)\b", re.I)


def _logo_layers(palette, motif):
    """Build layer list for a simple icon logo, no text."""
    tile, ink, accent = PALETTES[palette]
    L = [{"type": "rounded_rectangle", "name": "Tile", "width": 880, "height": 880, "corner_radius": 200, "fill": tile}]
    if motif == "ring":
        L.append({"type": "ellipse", "name": "Ring", "cx": 512, "cy": 512, "width": 640, "height": 640, "stroke": accent, "stroke_width": 28})
        L.append({"type": "ellipse", "name": "Dot", "cx": 512, "cy": 512, "width": 300, "height": 300, "fill": accent})
    elif motif == "spark":
        L.append({"type": "star", "name": "Spark", "cx": 512, "cy": 512, "width": 520, "height": 520, "points": 4, "radius": 72, "fill": accent})
        L.append({"type": "ellipse", "name": "Dot", "cx": 512, "cy": 512, "width": 120, "height": 120, "fill": ink})
    elif motif == "bars":
        for i, (cx, h, fill) in enumerate(((392, 240, accent), (512, 420, ink), (632, 320, accent))):
            L.append({"type": "rounded_rectangle", "name": f"Bar {i + 1}", "cx": cx, "cy": 512, "width": 90, "height": h, "corner_radius": 45, "fill": fill})
    else:
        L.append({"type": "ellipse", "name": "Disc", "cx": 512, "cy": 512, "width": 360, "height": 360, "fill": accent})
        L.append({"type": "ellipse", "name": "Dot", "cx": 690, "cy": 340, "width": 110, "height": 110, "fill": ink})
    return L


# "Complex" mode: same rule, bigger control panel. She turns seven dials, the
# harness does the trigonometry, so whatever she picks comes out symmetric.
_COMPLEX_SCHEMA = {"type": "object", "required": ["palette", "rings", "rays", "ray_style", "orbit_dots", "star_points"],
                   "properties": {
    "palette": {"enum": list(PALETTES)},
    "rings": {"type": "integer", "minimum": 2, "maximum": 5}, "rays": {"type": "integer", "minimum": 12, "maximum": 36},
    "ray_style": {"enum": ["bars", "dots", "stars"]}, "orbit_dots": {"type": "integer", "minimum": 0, "maximum": 16},
    "star_points": {"type": "integer", "minimum": 4, "maximum": 12}}}
_WANTS_COMPLEX = re.compile(r"\b(?:complex|intricate|detailed|elaborate|ornate|fancy|crazy|insane)\b", re.I)


def _complex_layers(palette, rings, rays, ray_style, orbit_dots, star_points):
    """Build layer list for an intricate logo design with concentric geometry."""
    tile, ink, accent = PALETTES[palette]
    C = 512

    def polar(r, deg):  # clock angle, 0 at the top, screen y grows downward
        """A point on a circle around the center, by radius and clock angle."""
        t = math.radians(deg)
        return round(C + r * math.sin(t)), round(C - r * math.cos(t))

    L = [{"type": "rounded_rectangle", "name": "Tile", "width": 880, "height": 880, "corner_radius": 200, "fill": tile}]
    for i in range(rays):
        deg = 360 * i / rays
        long = i % 2 == 0
        cx, cy = polar(372 if long else 384, deg)
        ray = {"name": f"Ray {i + 1}", "cx": cx, "cy": cy, "fill": accent, "opacity": 100 if long else 55}
        if ray_style == "bars":
            # pxm rotation is counterclockwise, a clock angle is clockwise
            ray.update(type="rounded_rectangle", width=10, height=64 if long else 36, corner_radius=5, rotation=round((360 - deg) % 360, 2))
        elif ray_style == "stars":
            ray.update(type="star", width=34 if long else 22, height=34 if long else 22, points=4, radius=35)
        else:
            ray.update(type="ellipse", width=22 if long else 12, height=22 if long else 12)
        L.append(ray)
    for k in range(rings):
        d = 620 - k * (300 // rings)
        L.append({"type": "ellipse", "name": f"Ring {k + 1}", "width": d, "height": d, "stroke": accent if k % 2 == 0 else ink,
                  "stroke_width": max(4, 16 - 3 * k), "opacity": 100 - 15 * k})
    for j in range(orbit_dots):
        cx, cy = polar(310 - (300 // rings) // 2, 360 * j / orbit_dots + 180 / orbit_dots)
        L.append({"type": "ellipse", "name": f"Orbit {j + 1}", "cx": cx, "cy": cy, "width": 18, "height": 18, "fill": ink})
    L.append({"type": "ellipse", "name": "Core", "width": 300, "height": 300, "fill": tile})
    L.append({"type": "star", "name": "Burst", "width": 290, "height": 290, "points": star_points, "radius": 72, "fill": accent, "opacity": 28})
    L.append({"type": "ellipse", "name": "Center", "width": 96, "height": 96, "fill": ink})
    return L


# Default mode: no letters at all. She turns four dials, the harness lays the cells on a golden-angle spiral (the way a
# sunflower packs its seeds), so it is never symmetric in the same way twice and never has text.
_BLOOM_SCHEMA = {"type": "object", "required": ["palette", "cells", "shape", "lit"], "properties": {
    "style": {"enum": ["spiral", "flower"]},
    "palette": {"enum": list(PALETTES)}, "cells": {"type": "integer", "minimum": 13, "maximum": 233},
    "shape": {"enum": ["circle", "square"]}, "lit": {"type": "integer", "minimum": 1, "maximum": 5}}}


def _bloom_layers(palette, cells, shape, lit, style="spiral"):
    """A wordless logo: cells on a golden-angle spiral, growing outward, with a few lit in the accent color.
    style "flower" packs the cells into accent petals around a clear dark ring and one bright core, so the
    mark still reads as a sunflower with a lit centre at 16 pixels, the way a browser tab shows it."""
    if style == "flower":
        return _flower_layers(palette, cells, shape)
    tile, ink, accent = PALETTES[palette]
    C, golden = 512, math.radians(137.507764)
    fib = [n for n in (1, 3, 8, 21, 55, 144, 233) if n <= cells]
    bright = set(fib[-lit:]) | {1}
    # fewer cells are drawn bigger, so the spiral fills the same disc: 144 is the reference size, and 21 cells
    # read as a bold sunflower even as a 16 pixel browser tab icon
    k = math.sqrt(144 / cells)
    L = [{"type": "rounded_rectangle", "name": "Tile", "width": 880, "height": 880, "corner_radius": 200, "fill": tile}]
    for i in range(1, cells + 1):
        f = math.sqrt((i - 1) / (cells - 1))  # cell 1 sits exactly on the centre: the one cell under the head
        r, theta = 335 * f, i * golden
        size = round(k * (14 + 30 * f + ((44 if i == 1 else 16) if i in bright else 0)))
        cell = {"name": f"Cell {i}", "cx": round(C + r * math.cos(theta)), "cy": round(C + r * math.sin(theta)), "width": size, "height": size,
                "fill": accent if i in bright else ink, "opacity": 100 if i in bright else round(52 + 40 * f)}
        if shape == "square":
            cell.update(type="rounded_rectangle", corner_radius=max(2, size // 6), rotation=round(math.degrees(theta) % 360, 2))
        else:
            cell["type"] = "ellipse"
        L.append(cell)
    return L


FLOWER_SPAN, FLOWER_GAP, FLOWER_CORE = 305, 0.55, 160  # spiral radius, cleared inner fraction, core diameter


def _flower_layers(palette, cells, shape):
    """The flower bloom: the same golden-angle spiral, cells packed until they nearly touch, the inner ones cleared
    to a dark ring, and one core in the palette's ink. Graded at 180, 64, 32 and 16 pixels on light and dark pages."""
    tile, ink, accent = PALETTES[palette]
    # measured, not guessed (docs/icon-blueprint.svg): the mark spans 78% of the tile, the dark ring is 63 units, a
    # full pixel at 16 pixels, so the core never merges into the petals; cream on ember alone is only 1.3:1
    span, gap, core = FLOWER_SPAN, FLOWER_GAP, FLOWER_CORE
    C, golden, k = 512, math.radians(137.507764), 1.45 * math.sqrt(144 / cells) * span / 335
    L = [{"type": "rounded_rectangle", "name": "Tile", "width": 880, "height": 880, "corner_radius": 200, "fill": tile}]
    for i in range(2, cells + 1):
        f = math.sqrt((i - 1) / (cells - 1))
        if f < gap:  # the dark ring that makes the core read as the one cell under the head
            continue
        r, theta = span * f, i * golden
        size = round(k * (14 + 30 * f))
        cell = {"name": f"Petal {i}", "cx": round(C + r * math.cos(theta)), "cy": round(C + r * math.sin(theta)),
                "width": size, "height": size, "fill": accent, "opacity": round(85 + 15 * f)}
        if shape == "square":
            cell.update(type="rounded_rectangle", corner_radius=max(2, size // 6), rotation=round(math.degrees(theta) % 360, 2))
        else:
            cell["type"] = "ellipse"
        L.append(cell)
    L.append({"type": "ellipse", "name": "Core", "cx": C, "cy": C, "width": core, "height": core, "fill": ink})
    return L


def make_logo(description):
    """Design a logo icon and build it live in Pixelmator Pro. It always makes an icon with no text. Default is a golden spiral; say 'complex' for an intricate one or 'simple' for a plain shape."""
    fancy = bool(_WANTS_COMPLEX.search(description))
    simple = not fancy and bool(_WANTS_SIMPLE.search(description))
    pal = ("palette: ember (warm amber on dark), ink (white and gold on near-black), forest (green on dark), signal (red on dark), "
           "paper (dark on cream). ")
    if fancy:
        prompt = ("Pick an icon logo with no letters or text at all. " + pal + "This one should be intricate, so be bold with the numbers. "
                  "rings: concentric rings. rays: marks around the rim. ray_style: bars, dots or stars. orbit_dots: dots circling inside. "
                  "star_points: points on the centre burst. Logo for: " + description)
    elif simple:
        prompt = "Pick a simple icon logo with no letters or text at all. " + pal + "motif: ring, spark, bars or dot. Logo for: " + description
    else:
        prompt = ("Pick an icon logo, no letters or text at all. " + pal + "cells: how many cells spiral out from the centre, a Fibonacci "
                  "number reads best. shape: circle or square. lit: how many cells glow in the accent color. "
                  "style: spiral (open cells, best big) or flower (packed petals round one bright core, reads even as a tiny tab icon). "
                  "Logo for: " + description)
    body = json.dumps({"model": _tools().AGENT_MODEL, "stream": False, "think": False, "format": _COMPLEX_SCHEMA if fancy else _LOGO_SCHEMA if simple else _BLOOM_SCHEMA,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    try:
        with urllib.request.urlopen(urllib.request.Request(_tools().OLLAMA_CHAT, body, {"Content-Type": "application/json"}), timeout=180) as r:
            pick = json.loads(json.load(r)["message"]["content"])
        spec = {"layers": _complex_layers(**pick) if fancy else _logo_layers(**pick) if simple else _bloom_layers(**pick)}
    except Exception as e:
        return f"I couldn't draft the design: {e}"
    out = os.path.expanduser("~/Desktop/samantha-logo.png")
    spec.update(width=1024, height=1024, export=[out], keep_open=not HEADLESS)
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".samantha-logo.json")
    json.dump(spec, open(path, "w"), indent=1)
    if os.path.exists(out):
        os.remove(out)  # a stale file must not read as a fresh success
    result = _run([sys.executable, PXM, "logo", path, "--timeout", "600"] + (["--headless"] if HEADLESS else []), timeout=620)
    chose = ", ".join(f"{k} {v}" for k, v in pick.items())
    return (f"I went with {chose}. {len(spec['layers'])} layers, built in Pixelmator, saved to {out}."
            if os.path.exists(out) else f"Pixelmator refused my design: {result[-300:]}")

def paint_image(path):
    """Repaint a photo out of tens of thousands of colored squares. Takes the path of an image file."""
    full = _inside_home(path.strip().strip("'\""))
    if not full or not os.path.isfile(full):
        return f"I can't find an image at {path}."
    out = os.path.expanduser("~/Desktop/samantha-painting.png")
    if os.path.exists(out):
        os.remove(out)  # a stale file must not read as a fresh success
    # ImageMagick draws the same plan in seconds, so she paints 40000 squares and the result is clear.
    # Pixelmator (800 layers, about a minute) is the fallback when ImageMagick is not installed.
    if shutil.which("magick"):
        result = _run([sys.executable, PXM, "paint", full, "--out", out, "--engine", "magick", "--shapes", "40000",
                       "--detail", "1024", "--size", "2048"], timeout=120)
        if os.path.exists(out):
            return f"Painted it from 40,000 squares, saved to {out}."
    result = _run([sys.executable, PXM, "paint", full, "--out", out, "--shapes", "800", "--size", "1024"]
                  + (["--headless"] if HEADLESS else []), timeout=600)
    return (f"Painted it from 800 layers in Pixelmator, saved to {out}." if os.path.exists(out)
            else f"Pixelmator refused the painting: {result[-300:]}")


def layers_to_svg(layers, note=""):
    """Her layer spec as an SVG, no Pixelmator needed: the same rounded tile, ellipses and stars pxm builds, on the
    1024 canvas cropped to the 880 tile. note rides along as a comment saying who picked what."""
    def num(v):
        """A coordinate without trailing zeros."""
        return f"{v:.2f}".rstrip("0").rstrip(".")

    def paint(l):
        """Fill, stroke and opacity attributes of a layer."""
        a = f' fill="{l["fill"].lower()}"' if l.get("fill") else ' fill="none"'
        if l.get("stroke"):
            a += f' stroke="{l["stroke"].lower()}" stroke-width="{num(l.get("stroke_width", 1))}"'
        if l.get("opacity", 100) != 100:
            a += f' opacity="{num(l["opacity"] / 100)}"'
        return a

    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="72 72 880 880">']
    if note:
        out.append(f"  <!-- {note.replace('--', '-')} -->")
    for l in layers:
        cx, cy, w, h = l.get("cx", 512), l.get("cy", 512), l.get("width", 0), l.get("height", 0)
        turn = f' transform="rotate({num(l["rotation"])} {num(cx)} {num(cy)})"' if l.get("rotation") else ""
        if l["type"] == "rounded_rectangle":
            out.append(f'  <rect x="{num(cx - w / 2)}" y="{num(cy - h / 2)}" width="{num(w)}" height="{num(h)}" rx="{num(l.get("corner_radius", 0))}"{paint(l)}{turn}/>')
        elif l["type"] == "ellipse":
            out.append(f'  <ellipse cx="{num(cx)}" cy="{num(cy)}" rx="{num(w / 2)}" ry="{num(h / 2)}"{paint(l)}{turn}/>')
        elif l["type"] == "star":
            n, R = int(l.get("points", 5)), w / 2
            r = R * l.get("radius", 50) / 100  # pxm's radius is the inner radius, as a percent of the outer one
            pts = " ".join(f"{num(cx + (R if k % 2 == 0 else r) * math.cos(math.pi * k / n - math.pi / 2))},"
                           f"{num(cy + (R if k % 2 == 0 else r) * h / w * math.sin(math.pi * k / n - math.pi / 2))}" for k in range(2 * n))
            out.append(f'  <polygon points="{pts}"{paint(l)}{turn}/>')
        else:
            raise ValueError(f"no SVG for a {l['type']} layer")
    return "\n".join(out + ["</svg>"]) + "\n"


ICON = ("ember", 89, "circle", 1, "flower")  # the dials behind web/icon.svg and icon.svg
ICON_NOTE = ("Made with Samantha: her logo designer laid 89 ember petals on a golden-angle spiral (style flower), cleared a dark ring, "
             "and lit one core, the cell under the tape head. Rebuild with tools_logo.icon_svg(); spec in pixelmator/examples/turing-flower.json.")


def icon_svg():
    """Turing's own icon, rebuilt from her designer: the exact bytes of web/icon.svg and icon.svg."""
    return layers_to_svg(_bloom_layers(*ICON), ICON_NOTE)


def _contrast(a, b):
    """WCAG contrast ratio of two hex colours."""
    def lum(h):
        """Relative luminance."""
        c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def icon_measures():
    """The icon's construction, measured from its own layers: every number the blueprint prints."""
    layers = _bloom_layers(*ICON)
    petals, core = layers[1:-1], layers[-1]
    dist = [math.hypot(p["cx"] - 512, p["cy"] - 512) for p in petals]
    inner = min(d - p["width"] / 2 for d, p in zip(dist, petals))
    outer = max(d + p["width"] / 2 for d, p in zip(dist, petals))
    tile, ink, accent = PALETTES[ICON[0]]
    return {"canvas": 1024, "tile": 880, "radius": 200, "core": core["width"], "inner": round(inner, 1), "outer": round(outer, 1),
            "gap": round(inner - core["width"] / 2, 1), "petals": len(petals), "cells": ICON[1], "span": FLOWER_SPAN,
            "petal_min": min(p["width"] for p in petals), "petal_max": max(p["width"] for p in petals),
            "margin": round(440 - outer, 1), "fill": round(2 * outer / 880, 3), "colors": (tile, accent, ink),
            "contrast": {"accent on tile": round(_contrast(accent, tile), 1), "core on tile": round(_contrast(ink, tile), 1),
                         "core on petals": round(_contrast(ink, accent), 2), "tile on white": round(_contrast(tile, "#FFFFFF"), 1)}}


def icon_blueprint_svg():
    """A construction sheet for the icon, drawn from the same layers: grid, keylines, the golden angle, every
    measurement and ratio, the palette with its contrast, and the icon at the sizes it has to survive."""
    m, blue, line, ink_t = icon_measures(), "#0d2a4a", "#8fc1ec", "#eaf4ff"
    tile, accent, cream = m["colors"]
    s, ox, oy = 0.72, 60, 90  # the 1024 canvas drawn at 737 px
    X = lambda v: round(ox + v * s, 1)
    Y = lambda v: round(oy + v * s, 1)
    R = lambda v: round(v * s, 1)
    o = ['<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="960" viewBox="0 0 1400 960" font-family="Helvetica, Arial, sans-serif">',
         "  <!-- Generated by tools_logo.icon_blueprint_svg() from the icon's own layers. Do not edit by hand. -->",
         f'  <rect width="1400" height="960" fill="{blue}"/>',
         f'  <text x="60" y="52" fill="{ink_t}" font-size="26" font-weight="700" letter-spacing="3">TURING / SAMANTHA  ICON BLUEPRINT</text>',
         f'  <text x="60" y="74" fill="{line}" font-size="14">Units are the 1024 unit canvas. Made with her designer: tools_logo._bloom_layers{ICON}</text>']
    o += [f'  <line x1="{X(v)}" y1="{Y(0)}" x2="{X(v)}" y2="{Y(1024)}" stroke="{line}" stroke-opacity="0.18"/>' for v in range(0, 1025, 64)]
    o += [f'  <line x1="{X(0)}" y1="{Y(v)}" x2="{X(1024)}" y2="{Y(v)}" stroke="{line}" stroke-opacity="0.18"/>' for v in range(0, 1025, 64)]
    body = icon_svg().split("\n")
    shapes = [l for l in body if l.strip().startswith(("<rect", "<ellipse", "<polygon"))]
    o.append(f'  <g transform="translate({ox} {oy}) scale({s}) translate(0 0)">')
    o += ["  " + l for l in shapes]
    o.append("  </g>")
    dash = f'fill="none" stroke="{line}" stroke-width="1.5" stroke-dasharray="6 5"'
    o += [f'  <rect x="{X(0)}" y="{Y(0)}" width="{R(1024)}" height="{R(1024)}" {dash}/>',
          f'  <rect x="{X(72)}" y="{Y(72)}" width="{R(880)}" height="{R(880)}" rx="{R(200)}" fill="none" stroke="{ink_t}" stroke-width="1.5"/>']
    for r, label in ((m["core"] / 2, f'core Ø{m["core"]}'), (m["inner"], f'ring inner Ø{round(2 * m["inner"])}'), (m["outer"], f'mark Ø{round(2 * m["outer"])}')):
        o.append(f'  <circle cx="{X(512)}" cy="{Y(512)}" r="{R(r)}" {dash}/>')
    o += [f'  <line x1="{X(512)}" y1="{Y(40)}" x2="{X(512)}" y2="{Y(984)}" stroke="{line}" stroke-width="1"/>',
          f'  <line x1="{X(40)}" y1="{Y(512)}" x2="{X(984)}" y2="{Y(512)}" stroke="{line}" stroke-width="1"/>']
    a = math.radians(137.507764)
    ex, ey = 512 + 250 * math.cos(-a), 512 + 250 * math.sin(-a)
    o += [f'  <line x1="{X(512)}" y1="{Y(512)}" x2="{X(762)}" y2="{Y(512)}" stroke="{accent}" stroke-width="2.5"/>',
          f'  <line x1="{X(512)}" y1="{Y(512)}" x2="{X(ex)}" y2="{Y(ey)}" stroke="{accent}" stroke-width="2.5"/>',
          f'  <path d="M {X(512 + 120)} {Y(512)} A {R(120)} {R(120)} 0 0 0 {X(512 + 120 * math.cos(-a))} {Y(512 + 120 * math.sin(-a))}" fill="none" stroke="{accent}" stroke-width="2.5"/>',
]
    lab = lambda x, y, t: f'  <text x="{x}" y="{y}" fill="{ink_t}" font-size="14">{t}</text>'
    o += [lab(X(72) + 4, Y(72) - 8, f'tile 880 x 880, corner r {m["radius"]} ({m["radius"] / 880:.1%})'),
          lab(X(0) + 4, Y(1024) + 20, "canvas 1024 x 1024, grid 64"),
          lab(X(512) + 8, Y(512 - m["outer"]) - 6, f'mark Ø{round(2 * m["outer"])} ({m["fill"]:.1%} of tile)'),
          lab(X(512) + 8, Y(512 + m["outer"]) + 20, f'core Ø{m["core"]}, dark ring {m["gap"]} wide, ring inner Ø{round(2 * m["inner"])}')]
    # the spec column
    x0, y = 870, 130
    rows = [("CONSTRUCTION", None),
            (f'{m["cells"]} cells on a golden-angle spiral (Fibonacci)', None),
            ("cell i at r = %d·√((i−1)/(n−1)), θ = i · 137.508°" % m["span"], None),
            (f'{m["cells"] - m["petals"]} inner cells cleared, {m["petals"]} petals drawn', None),
            (f'petals Ø{m["petal_min"]} to Ø{m["petal_max"]}, growing outward', None),
            ("golden angle 137.5° between cells (drawn in ember)", None),
            ("", None), ("PROPORTIONS", None),
            (f'mark / tile  {m["fill"]:.1%}   margin {m["margin"]}', None),
            (f'core / mark  {m["core"] / (2 * m["outer"]):.1%}', None),
            (f'ring / core  {m["gap"] / m["core"]:.1%}   ({m["gap"] / 1024 * 16:.2f} px at 16 px)', None),
            (f'corner / tile  {m["radius"] / 880:.1%}', None),
            ("", None), ("COLOUR, WCAG CONTRAST", None)]
    for t, _ in rows:
        bold = t.isupper() and t != ""
        weight = ' font-weight="700" letter-spacing="2"' if bold else ""
        o.append(f'  <text x="{x0}" y="{y}" fill="{line if bold else ink_t}" font-size="{14 if bold else 16}"{weight}>{t}</text>')
        y += 26
    for name, hexv in (("tile", tile), ("ember petals", accent), ("core", cream)):
        o += [f'  <rect x="{x0}" y="{y - 16}" width="22" height="22" rx="4" fill="{hexv}" stroke="{line}"/>',
              f'  <text x="{x0 + 32}" y="{y}" fill="{ink_t}" font-size="16">{name}  {hexv.upper()}</text>']
        y += 30
    for k, v in m["contrast"].items():
        o.append(f'  <text x="{x0}" y="{y}" fill="{ink_t}" font-size="15">{k}  {v}:1</text>')
        y += 24
    y += 20
    o.append(f'  <text x="{x0}" y="{y}" fill="{line}" font-size="14" font-weight="700" letter-spacing="2">SIZES IT MUST SURVIVE</text>')
    y += 16
    xx = x0
    for px in (180, 64, 32, 16):
        o.append(f'  <g transform="translate({xx} {y}) scale({px / 880}) translate(-72 -72)">')
        o += ["  " + l for l in shapes]
        o.append("  </g>")
        o.append(f'  <text x="{xx}" y="{y + px + 18}" fill="{ink_t}" font-size="13">{px}</text>')
        xx += px + 24
    return "\n".join(o + ["</svg>"]) + "\n"
