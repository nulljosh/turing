"""Painting styles for `pxm.py paint --engine magick --style NAME`: the same photo, drawn a different way.

Every style starts from one plan: the photo cut into flat cells by a quadtree that always splits the cell whose
colors disagree most (busy places get small cells, calm sky gets big ones). `cells()` returns that plan as a
partition, leaves only, each cell once. A style turns the cells into primitives, plain dicts a renderer draws:

    {"kind": "rect" | "roundrect" | "circle" | "line", "box": (x0, y0, x1, y1), "fill": "#RRGGBB" or None,
     "stroke": "#RRGGBB" or None, "width": px, "radius": px}          (a line runs from (x0, y0) to (x1, y1))

`to_mvg()` writes them for ImageMagick. Stdlib only, like pxm.py.
"""
import colorsys
import heapq
import random

STYLES = {
    "squares": "flat squares edge to edge, the classic",
    "mosaic": "tiles with dark grout between them",
    "dots": "round dabs of paint on cream paper, like pointillism",
    "poster": "squares in eight bold colors, like a screen print",
    "sketch": "ink outlines only, dense where the photo is busy",
    "glass": "stained glass: rich color, thick black lead",
}
# How many cells each style reads best at: mosaic and glass want tiles you can see, squares and poster want detail.
BUDGET = {"squares": 40000, "poster": 20000, "dots": 9000, "sketch": 30000, "mosaic": 3500, "glass": 1800}
PAPER, INK, GROUT, LEAD = "#F4EFE4", "#2B2723", "#1E1C1A", "#101010"


def _hex(rgb):
    """(r, g, b) floats -> "#RRGGBB", clamped."""
    return "#%02X%02X%02X" % tuple(max(0, min(255, round(c))) for c in rgb)


def _rgb(fill):
    """"#RRGGBB" -> (r, g, b) ints."""
    return tuple(int(fill[i:i + 2], 16) for i in (1, 3, 5))


def cells(w, h, rows, budget):
    """The photo (rows of (r, g, b), w x h) as at most `budget` flat cells: [(x0, y0, x1, y1, "#RRGGBB")], a
    partition of the whole frame. The cell with the most color error splits first, into four."""
    S = [[(0, 0, 0, 0)] * (w + 1)]
    for y in range(h):
        acc, line, up = (0, 0, 0, 0), [(0, 0, 0, 0)], S[y]
        for x in range(w):
            r, g, b = rows[y][x]
            acc = (acc[0] + r, acc[1] + g, acc[2] + b, acc[3] + r * r + g * g + b * b)
            line.append(tuple(acc[k] + up[x + 1][k] for k in range(4)))
        S.append(line)

    def stat(x0, y0, x1, y1):
        """Error and mean color of one cell, from the summed-area tables."""
        n = (x1 - x0) * (y1 - y0)
        r, g, b, sq = (S[y1][x1][k] - S[y0][x1][k] - S[y1][x0][k] + S[y0][x0][k] for k in range(4))
        return sq - (r * r + g * g + b * b) / n, _hex((r / n, g / n, b / n))

    done, heap = [], []

    def add(x0, y0, x1, y1):
        """Queue a cell to split later, or keep it as it is when it is one pixel wide or tall."""
        err, fill = stat(x0, y0, x1, y1)
        if x1 - x0 > 1 and y1 - y0 > 1:
            heapq.heappush(heap, (-err, x0, y0, x1, y1, fill))
        else:
            done.append((x0, y0, x1, y1, fill))

    add(0, 0, w, h)
    while heap and len(heap) + len(done) + 3 <= budget:
        _, x0, y0, x1, y1, _ = heapq.heappop(heap)
        mx, my = (x0 + x1) // 2, (y0 + y1) // 2
        for a, b, c, d in ((x0, y0, mx, my), (mx, y0, x1, my), (x0, my, mx, y1), (mx, my, x1, y1)):
            if c > a and d > b:
                add(a, b, c, d)
    return done + [(x0, y0, x1, y1, fill) for _, x0, y0, x1, y1, fill in heap]


def _palette(cs, k=8, rounds=12):
    """k colors that stand for all the cells, weighted by area (a small k-means, seeded the same every time)."""
    pts = [(_rgb(f), (x1 - x0) * (y1 - y0)) for x0, y0, x1, y1, f in cs]
    rng = random.Random(0)
    centers = [p for p, _ in rng.sample(pts, min(k, len(pts)))]
    for _ in range(rounds):
        sums = [[0.0, 0.0, 0.0, 0.0] for _ in centers]
        for p, wgt in pts:
            i = min(range(len(centers)), key=lambda j: sum((p[t] - centers[j][t]) ** 2 for t in range(3)))
            for t in range(3):
                sums[i][t] += p[t] * wgt
            sums[i][3] += wgt
        centers = [(s[0] / s[3], s[1] / s[3], s[2] / s[3]) if s[3] else c for s, c in zip(sums, centers)]
    return centers


def _nearest(fill, centers):
    """The palette color closest to fill."""
    p = _rgb(fill)
    return _hex(min(centers, key=lambda c: sum((p[t] - c[t]) ** 2 for t in range(3))))


def _rich(fill, sat=1.5, val=1.1):
    """The same hue, more saturated and a little brighter: light through colored glass."""
    h, s, v = colorsys.rgb_to_hsv(*(c / 255 for c in _rgb(fill)))
    return _hex(c * 255 for c in colorsys.hsv_to_rgb(h, min(1, s * sat), min(1, v * val)))


def _darker(fill, f=0.55):
    """The same color in shadow: ink for the sketch."""
    return _hex(c * f for c in _rgb(fill))


def draw(cs, scale, style="squares"):
    """Cells -> (background, primitives) for one style, on a canvas `scale` times the plan's size."""
    if style not in STYLES:
        raise ValueError("unknown style %r, pick one of: %s" % (style, ", ".join(STYLES)))
    out = []
    if style == "squares":
        return "#000000", [{"kind": "rect", "box": (x0 * scale, y0 * scale, x1 * scale - 1, y1 * scale - 1), "fill": f}
                           for x0, y0, x1, y1, f in cs]
    if style == "poster":
        centers = _palette(cs)
        return "#000000", [{"kind": "rect", "box": (x0 * scale, y0 * scale, x1 * scale - 1, y1 * scale - 1),
                            "fill": _nearest(f, centers)} for x0, y0, x1, y1, f in cs]
    if style in ("mosaic", "glass"):
        # The gap grows with the tile, so small tiles stay tiles and not specks.
        for x0, y0, x1, y1, f in cs:
            side = min(x1 - x0, y1 - y0) * scale
            gap = max(1, min(6, round(side * (0.06 if style == "mosaic" else 0.1))))
            box = (x0 * scale + gap, y0 * scale + gap, x1 * scale - 1 - gap, y1 * scale - 1 - gap)
            if box[2] < box[0] or box[3] < box[1]:
                continue
            out.append({"kind": "roundrect" if style == "mosaic" else "rect", "box": box,
                        "fill": f if style == "mosaic" else _rich(f), "radius": max(1, gap)})
        return (GROUT if style == "mosaic" else LEAD), out
    if style == "dots":
        # Big cells become a few dabs, small ones one each; biggest first so fine detail sits on top, and every dab
        # a little off center and a little off size so it reads as a hand, not a grid. Dabs overlap: little bare paper.
        rng = random.Random(1)
        for x0, y0, x1, y1, f in sorted(cs, key=lambda c: -(c[2] - c[0]) * (c[3] - c[1])):
            cw, ch = (x1 - x0) * scale, (y1 - y0) * scale
            n = max(1, min(6, round(max(cw, ch) / min(cw, ch)) + (2 if min(cw, ch) > 40 else 0)))
            for _ in range(n):
                r = max(1.5, (cw * ch / n) ** 0.5 * rng.uniform(0.55, 0.75))
                cx, cy = x0 * scale + rng.uniform(0.2, 0.8) * cw, y0 * scale + rng.uniform(0.2, 0.8) * ch
                out.append({"kind": "circle", "box": (cx - r, cy - r, cx + r, cy + r), "fill": _rich(f, 1.25, 1.03)})
        return PAPER, out
    # sketch: pencil on paper. Hatching on one lattice for the whole canvas, so strokes run on unbroken from cell
    # to cell: each darker tone adds a layer (/, then \\, then both again offset), and a cell takes a layer only when
    # it is that dark. Clouds stay bare paper, the forest goes nearly black, edges draw themselves where tones change.
    gap = 7

    def lum(f):
        """How light a fill looks, 0 to 1."""
        r, g, b = _rgb(f)
        return (0.299 * r + 0.587 * g + 0.114 * b) / 255

    # Equalized tones: a cell's darkness is the share of the picture (by area) lighter than it, so a dark photo
    # still spreads over every hatch layer instead of going one flat crosshatch, and the drawing keeps its detail.
    by_tone = sorted((lum(f), (x1 - x0) * (y1 - y0)) for x0, y0, x1, y1, f in cs)
    total, run, rank = sum(a for _, a in by_tone), 0, {}
    for v, area in by_tone:
        run += area
        rank.setdefault(v, run / total)
    for k, (tone, way, shift) in enumerate(((0.2, 1, 0), (0.42, -1, 0), (0.62, 1, 0.5), (0.8, -1, 0.5))):
        for x0, y0, x1, y1, f in cs:
            if 1 - rank[lum(f)] < tone:
                continue
            X0, Y0, X1, Y1 = x0 * scale, y0 * scale, x1 * scale, y1 * scale
            lo, hi = (X0 + Y0, X1 + Y1) if way == 1 else (X0 - Y1, X1 - Y0)
            c = (int(lo // gap) + shift) * gap
            while c <= hi:
                if way == 1:  # x + y = c
                    a, e = max(X0, c - Y1), min(X1, c - Y0)
                    seg = (a, c - a, e, c - e)
                else:  # x - y = c
                    a, e = max(X0, c + Y0), min(X1, c + Y1)
                    seg = (a, a - c, e, e - c)
                if e > a:
                    out.append({"kind": "line", "box": seg, "stroke": INK, "width": 1})
                c += gap
    return PAPER, out


def to_mvg(background, prims):
    """Primitives as an ImageMagick MVG draw file (the body of `-draw @file`)."""
    lines = []
    for p in prims:
        x0, y0, x1, y1 = (round(v, 1) for v in p["box"])
        lines.append("fill %s" % (p.get("fill") or "none"))
        lines.append("stroke %s" % (p.get("stroke") or "none"))
        if p.get("stroke"):
            lines.append("stroke-width %s" % p.get("width", 1))
        if p["kind"] == "rect":
            lines.append("rectangle %s,%s %s,%s" % (x0, y0, x1, y1))
        elif p["kind"] == "line":
            lines.append("line %s,%s %s,%s" % (x0, y0, x1, y1))
        elif p["kind"] == "roundrect":
            lines.append("roundrectangle %s,%s %s,%s %s,%s" % (x0, y0, x1, y1, p["radius"], p["radius"]))
        else:
            lines.append("ellipse %s,%s %s,%s 0,360" % ((x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2, (y1 - y0) / 2))
    return "\n".join(lines) + "\n"
