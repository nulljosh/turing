"""Samantha Sans: Inter (rsms/inter, SIL Open Font License 1.1, no reserved name), renamed and shipped as her face.

Inter was drawn for screens in the spirit of SF and Helvetica, which is the look Joshua asked for (2026-10-18); the hand
drawn monoline face it replaces read too technical. Three weights, Latin only, pinned to one release so every build
is the same bytes. The OFL travels with the fonts in web/fonts/OFL.txt and the copyright stays in the name table.

    python3 scripts/gen_font.py            # downloads Inter once, writes web/fonts/SamanthaSans-{Regular,Medium,Semibold}.{ttf,woff2}
    python3 scripts/gen_font.py --check    # the shipped fonts: named Samantha Sans, OFL present, proportional, I l 1 O 0 all different
Needs fonttools and brotli, none of which the apps themselves need.
"""
import io
import os
import sys
import urllib.request

from fontTools.ttLib import TTFont

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "web", "fonts")
SOURCE = "https://cdn.jsdelivr.net/npm/@fontsource/inter@5.2.8/"
WEIGHTS = {"Regular": 400, "Medium": 500, "Semibold": 600}


def fetch(path):
    """Bytes of one file from the pinned Inter release."""
    with urllib.request.urlopen(SOURCE + path, timeout=60) as r:
        return r.read()


def rename(font, style):
    """Give Inter's outlines her name; copyright (0) and license (13, 14) stay as Inter's authors wrote them."""
    names = {1: "Samantha Sans", 2: style, 3: f"SamanthaSans-{style}", 4: f"Samantha Sans {style}", 5: "Version 2.000",
             6: f"SamanthaSans-{style}", 16: "Samantha Sans", 17: style}
    table = font["name"]
    table.names = [n for n in table.names if n.nameID in (0, 13, 14)]
    for nid, text in names.items():
        table.setName(text, nid, 3, 1, 0x409)
        table.setName(text, nid, 1, 0, 0)
    font["head"].created = font["head"].modified = 3_700_000_000   # fixed, so every build is the same bytes
    font["OS/2"].achVendID = "SMTH"


def to_bytes(font, flavor):
    """The font as TTF (flavor None) or WOFF2 bytes."""
    font.flavor = flavor
    buf = io.BytesIO()
    font.save(buf, reorderTables=False)
    return buf.getvalue()


def check():
    """Self-check of the shipped files: her name, the license beside them, proportional figures, no look-alikes."""
    assert os.path.exists(os.path.join(OUT, "OFL.txt")), "the OFL must ship with the fonts"
    for style in WEIGHTS:
        for ext in ("ttf", "woff2"):
            f = TTFont(os.path.join(OUT, f"SamanthaSans-{style}.{ext}"))
            assert f["name"].getDebugName(1) == "Samantha Sans" and f["name"].getDebugName(6) == f"SamanthaSans-{style}"
            assert "Inter" in f["name"].getDebugName(0), "Inter's copyright must stay in the name table"
            cmap, hmtx, glyf = f.getBestCmap(), f["hmtx"], f["glyf"]
            assert hmtx[cmap[ord("i")]][0] < hmtx[cmap[ord("m")]][0], "letters are not proportional"
            assert hmtx[cmap[ord("1")]][0] < hmtx[cmap[ord("0")]][0], "figures are not proportional"
            shapes = {glyf[cmap[ord(c)]].coordinates.array.tobytes() for c in "Il1O0"}
            assert len(shapes) == 5, "two of I l 1 O 0 are drawn the same"
    print("font ok: Samantha Sans (Inter, OFL), 3 weights")


def main():
    """Fetch Inter, rename it, write every weight and the license to web/fonts; or run the check."""
    if "--check" in sys.argv:
        return check()
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "OFL.txt"), "wb") as f:
        f.write(fetch("LICENSE"))
    for style, weight in WEIGHTS.items():
        font = TTFont(io.BytesIO(fetch(f"files/inter-latin-{weight}-normal.woff2")))
        rename(font, style)
        for ext, flavor in (("ttf", None), ("woff2", "woff2")):
            with open(os.path.join(OUT, f"SamanthaSans-{style}.{ext}"), "wb") as f:
                f.write(to_bytes(font, flavor))
        print(f"SamanthaSans-{style}: Inter {weight}")


if __name__ == "__main__":
    main()
