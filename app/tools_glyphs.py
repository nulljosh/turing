"""Her glyph logos: one bold flat white glyph that means the subject, on a flat accent tile. The house icon style
(the /brand skill): stroke 72 with round ends, inside the central 640 px of the 1024 grid, no text, no emblem.
The model only picks a glyph and a palette from fixed lists; a keyword table picks first when the subject says
it plainly (a bakery is bread, a surf school is a wave), so a weak pick never draws the wrong thing.
"""
import json
import os
import re
import shutil
import unicodedata

# One accent per tile, white glyph on top: (light, deep), the Icon Composer gradient runs light to deep and the flat
# PNG uses deep. No yellow, teal, purple, brown or beige (the design system).
GLYPH_PALETTES = {"terracotta": ("#E0825A", "#B5502C"), "blue": ("#2997FF", "#0071E3"), "green": ("#4CBF7F", "#2F8F5B"),
                  "red": ("#FF6B6B", "#D93A3F"), "black": ("#3A3A3C", "#111111")}

_C = {"type": "path", "stroke": "#FFFFFF", "stroke_width": 72}  # every stroke in the house style


def _dot(cx, cy, d):
    """A filled white dot, for pupils, notes and wheels."""
    return {"type": "ellipse", "cx": cx, "cy": cy, "width": d, "height": d, "fill": "#FFFFFF"}


def _ring(cx, cy, d):
    """A white stroked circle."""
    return {"type": "ellipse", "cx": cx, "cy": cy, "width": d, "height": d, "stroke": "#FFFFFF", "stroke_width": 72}


def _p(*paths):
    """Stroked paths in the house style."""
    return [dict(_C, d=d) for d in paths]


# name: (keywords, layers). Paths are SVG path data on the 1024 grid, kept inside 192..832.
GLYPHS = {
    "wave": (r"surf|wave|ocean|sea|beach|swim|water|sail|boat|marine", _p(
        "M 232 440 C 312 360 392 360 472 440 C 552 520 632 520 712 440 L 792 400",
        "M 232 640 C 312 560 392 560 472 640 C 552 720 632 720 712 640 L 792 600")),
    "leaf": (r"leaf|plant|garden|green|eco|nature|organic|farm|vegan|tree|herb", _p(
        "M 300 724 C 300 440 480 300 724 300 C 724 560 580 724 300 724 Z", "M 300 724 L 560 464")),
    "mountain": (r"mountain|hike|hiking|climb|peak|outdoor|ski|trail|alpine|camp", _p(
        "M 212 724 L 420 380 L 540 560 L 640 440 L 812 724 Z")),
    "bolt": (r"bolt|energy|electric|power|fast|speed|charge|battery|volt|flash", _p(
        "M 560 212 L 352 540 L 520 540 L 464 812 L 672 484 L 504 484 Z")),
    "book": (r"book|read|library|school|learn|study|course|teach|tutor|class|education|story", _p(
        "M 512 360 C 440 310 330 300 232 320 L 232 712 C 330 692 440 702 512 752 C 584 702 694 692 792 712 L 792 320 C 694 300 584 310 512 360 Z",
        "M 512 360 L 512 752")),
    "cup": (r"coffee|cafe|tea|espresso|latte|cup|mug|brew", _p(
        "M 292 452 L 292 640 C 292 712 344 752 412 752 L 492 752 C 560 752 612 712 612 640 L 612 452 Z",
        "M 612 492 C 732 492 732 640 612 640", "M 392 232 C 352 292 432 316 392 372", "M 512 232 C 472 292 552 316 512 372")),
    "dumbbell": (r"gym|fitness|workout|lift|strength|train|muscle|crossfit|weights|sport", _p(
        "M 332 512 L 692 512", "M 332 380 L 332 644", "M 232 440 L 232 584", "M 692 380 L 692 644", "M 792 440 L 792 584")),
    "heart": (r"love|heart|dating|care|health|kind|charity|wedding|valentine|clinic", _p(
        "M 512 772 C 312 640 232 540 252 440 C 272 330 412 300 512 412 C 612 300 752 330 772 440 C 792 540 712 640 512 772 Z")),
    "garage": (r"garage|overhead door|sectional door|door opener", _p(
        "M 212 816 L 212 472 L 512 232 L 812 472 L 812 816", "M 352 556 L 672 556", "M 352 666 L 672 666", "M 352 776 L 672 776")),
    "house": (r"house|home|real estate|rent|apartment|property|realtor|stay|hotel|room", _p(
        "M 232 512 L 512 272 L 792 512", "M 312 452 L 312 772 L 712 772 L 712 452", "M 452 772 L 452 612 L 572 612 L 572 772")),
    "eye": (r"eye|vision|see|watch|optic|view|look|camera|photo|lens|security", _p(
        "M 212 512 C 332 332 692 332 812 512 C 692 692 332 692 212 512 Z") + [_dot(512, 512, 150)]),
    "note": (r"music|song|band|audio|sound|podcast|radio|beat|dj|sing|piano", _p(
        "M 432 712 L 432 312 L 712 262 L 712 652") + [_dot(372, 712, 150), _dot(652, 652, 150)]),
    "pin": (r"map|location|travel|place|trip|local|city|tour|guide|address|where", _p(
        "M 512 812 C 392 672 292 572 292 452 C 292 322 392 222 512 222 C 632 222 732 322 732 452 C 732 572 632 672 512 812 Z")
        + [_dot(512, 452, 130)]),
    "flame": (r"fire|flame|hot|spicy|bbq|grill|burn|heat|candle|torch", _p(
        "M 512 812 C 352 812 282 692 302 572 C 322 452 442 402 452 232 C 572 312 652 432 652 532 C 692 492 702 452 702 422 "
        "C 772 532 752 812 512 812 Z")),
    "code": (r"code|dev|developer|program|software|api|app|tech|hack|script|terminal", _p(
        "M 412 312 L 232 512 L 412 712", "M 612 312 L 792 512 L 612 712")),
    "network": (r"ai|model|brain|smart|turing|assistant|agent|bot|neural|data|connect|network|machine", _p(
        "M 512 292 L 312 692 L 712 692 Z") + [_dot(512, 292, 170), _dot(312, 692, 170), _dot(712, 692, 170)]),
    "sun": (r"sun|summer|solar|bright|morning|day|light|shine|weather", [_ring(512, 512, 300)] + _p(
        "M 512 212 L 512 262", "M 512 762 L 512 812", "M 212 512 L 262 512", "M 762 512 L 812 512",
        "M 300 300 L 335 335", "M 689 689 L 724 724", "M 300 724 L 335 689", "M 689 335 L 724 300")),
    "bread": (r"bakery|bread|bake|baker|pastry|cake|dough|loaf|croissant|kitchen|food|cook|chef", _p(
        "M 232 712 L 232 552 C 232 392 352 312 512 312 C 672 312 792 392 792 552 L 792 712 Z",
        "M 392 452 L 432 552", "M 512 432 L 552 532", "M 632 452 L 672 552")),
    "cart": (r"shop|store|cart|buy|sell|market|retail|commerce|deal|price|grocery", _p(
        "M 212 292 L 312 292 L 382 632 L 732 632 L 792 392 L 342 392") + [_dot(412, 752, 110), _dot(702, 752, 110)]),
    "check": (r"task|todo|check|done|habit|goal|plan|list|productive|productivity|finish|verify", _p("M 272 532 L 432 692 L 752 352")),
    "paw": (r"pet|dog|cat|paw|vet|animal|puppy|kitten|groom", [
        {"type": "ellipse", "cx": 512, "cy": 632, "width": 300, "height": 240, "fill": "#FFFFFF"},
        _dot(332, 452, 130), _dot(452, 342, 130), _dot(572, 342, 130), _dot(692, 452, 130)]),
}


def keyword_glyph(description):
    """The glyph whose keywords the subject names plainly, or None. Whole words only, first match in table order."""
    text = "".join(c for c in unicodedata.normalize("NFD", description.lower()) if not unicodedata.combining(c))  # cafe for café
    for name, (words, _) in GLYPHS.items():
        if re.search(rf"\b(?:{words})(?:s|es|ing|er|ers)?\b", text):
            return name
    return None


def glyph_layers(glyph, palette):
    """The full layer list: the flat accent tile, then the glyph in white."""
    tile = {"type": "rounded_rectangle", "name": "Tile", "width": 880, "height": 880, "corner_radius": 200, "fill": GLYPH_PALETTES[palette][1]}
    return [tile] + [dict(l) for l in GLYPHS[glyph][1]]


GLYPH_SCHEMA = {"type": "object", "required": ["glyph", "palette"], "properties": {
    "glyph": {"enum": list(GLYPHS)}, "palette": {"enum": list(GLYPH_PALETTES)}}}


def _ext(color, mix=0.0):
    """An Icon Composer color: extended sRGB, darkened by mix (the brand kit's dark appearance)."""
    return "extended-srgb:" + ",".join(f"{int(color[i:i + 2], 16) / 255 * (1 - mix):.3f}" for i in (1, 3, 5)) + ",1.0"


def icon_bundle(glyph, palette, path, draw):
    """Write an Icon Composer bundle (the /icon skill's shape): icon.json with a light-to-deep gradient fill, a dark
    appearance, and the glyph as one layer, Assets/glyph.png, drawn by draw(layers, png) on a clear 1024 canvas.
    Only her own output bundle is ever replaced."""
    light, deep = GLYPH_PALETTES[palette]
    if os.path.isdir(path):
        shutil.rmtree(path)
    os.makedirs(os.path.join(path, "Assets"))
    draw(glyph_layers(glyph, palette)[1:], os.path.join(path, "Assets", "glyph.png"))
    icon = {"fill-specializations": [{"value": {"linear-gradient": [_ext(light), _ext(deep)]}},
                                     {"appearance": "dark", "value": {"linear-gradient": [_ext(deep, .72), _ext(deep, .88)]}}],
            "groups": [{"layers": [{"glass": False, "image-name": "glyph.png", "name": glyph}], "lighting": "individual", "name": glyph,
                        "shadow": {"kind": "neutral", "opacity": 0.3}, "specular": True, "translucency": {"enabled": False, "value": 0}}],
            "supported-platforms": {"squares": "shared"}}
    with open(os.path.join(path, "icon.json"), "w") as f:
        f.write(json.dumps(icon, indent=2) + "\n")
    return path
