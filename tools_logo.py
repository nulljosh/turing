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
    "palette": {"enum": list(PALETTES)}, "cells": {"type": "integer", "minimum": 55, "maximum": 233},
    "shape": {"enum": ["circle", "square"]}, "lit": {"type": "integer", "minimum": 1, "maximum": 5}}}


def _bloom_layers(palette, cells, shape, lit):
    """A wordless logo: cells on a golden-angle spiral, growing outward, with a few lit in the accent color."""
    tile, ink, accent = PALETTES[palette]
    C, golden = 512, math.radians(137.507764)
    fib = [n for n in (1, 3, 8, 21, 55, 144, 233) if n <= cells]
    bright = set(fib[-lit:]) | {1}
    L = [{"type": "rounded_rectangle", "name": "Tile", "width": 880, "height": 880, "corner_radius": 200, "fill": tile}]
    for i in range(1, cells + 1):
        f = math.sqrt((i - 1) / (cells - 1))  # cell 1 sits exactly on the centre: the one cell under the head
        r, theta = 335 * f, i * golden
        size = round(14 + 30 * f + ((44 if i == 1 else 16) if i in bright else 0))
        cell = {"name": f"Cell {i}", "cx": round(C + r * math.cos(theta)), "cy": round(C + r * math.sin(theta)), "width": size, "height": size,
                "fill": accent if i in bright else ink, "opacity": 100 if i in bright else round(52 + 40 * f)}
        if shape == "square":
            cell.update(type="rounded_rectangle", corner_radius=max(2, size // 6), rotation=round(math.degrees(theta) % 360, 2))
        else:
            cell["type"] = "ellipse"
        L.append(cell)
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
                  "number reads best. shape: circle or square. lit: how many cells glow in the accent color. Logo for: " + description)
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
