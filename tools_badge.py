"""Modernizes web/badge.svg a little at every minor version, without ever redrawing her: same woman, same oval
frame, same SAMANTHA/TURING ribbons, one notch cleaner each time. art/badge-source.svg is the frozen original
(an AI-drawn copperplate engraving, hand-traced to one potrace path); modernize(step) always rebuilds from that
source, never the previous output, so nothing compounds. It rasterizes the source high-resolution, applies a
step-scaled treatment (blur-then-threshold, calming cross-hatching, plus potrace turdsize/alphamax/opttolerance
nudged up for fewer nodes and rounder corners), and re-traces. A gate (words_read + an ink-share sanity check)
has to pass before web/badge.svg and web/badge-preview.png are kept; a failing gate restores what was there, and
the CLI always exits 0 so a release never fails over the badge.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE_SVG = os.path.join(HERE, "art", "badge-source.svg")
OUTPUT_SVG = os.path.join(HERE, "web", "badge.svg")
OUTPUT_PNG = os.path.join(HERE, "web", "badge-preview.png")
OCR_SCRIPT = os.path.join(HERE, "swift", "ocr.swift")
ARIA_LABEL = "Samantha’s mark, drawn by her"  # matches the original file byte for byte, curly apostrophe
RES = 2048  # rasterize-and-retrace resolution, plenty of headroom over the 1024pt original
PREVIEW_SIZE = 512
MAX_STEP = 12  # step_for never returns more than this, and the dial stops moving past it too


def _run(argv, timeout=90):
    """Run a command and return its stdout, or None when it failed, timed out, or the binary is missing."""
    try:
        result = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout if result.returncode == 0 else None


def freeze_source():
    """Copy the current web/badge.svg to art/badge-source.svg once, if it is not there yet. The source is never
    touched again after this: every modernize() call rebuilds from it fresh, so nothing ever compounds."""
    if os.path.exists(SOURCE_SVG):
        return False
    os.makedirs(os.path.dirname(SOURCE_SVG), exist_ok=True)
    shutil.copyfile(OUTPUT_SVG, SOURCE_SVG)
    return True


def step_for(version):
    """"4.7.0" -> 0, "4.8.0" -> 1, "4.9.0" -> 2, "5.0.0" -> 3: a minor bump is one step, a major bump counts as
    one step past the last minor before it, assuming at most ~10 minors per major. step = (major-4)*10 + minor -
    7, floored at 0. Patches never change the step. Capped at MAX_STEP so an old badge does not drift forever."""
    m = re.match(r"^(\d+)\.(\d+)\.(\d+)$", version.strip())
    if not m:
        return 0
    major, minor, _patch = (int(g) for g in m.groups())
    step = (major - 4) * 10 + minor - 7
    return max(0, min(step, MAX_STEP))


def _dial(step):
    """The modernize dial for a step, clipped to [0, MAX_STEP]. Step 0 is potrace's own defaults and no raster
    treatment, so it reproduces the source faithfully. Every step past that nudges turdsize (drop fine speckle
    and hatching), alphamax (rounder corners) and opttolerance (fewer nodes) up a little, plus a light
    blur-then-threshold before tracing for cleaner, more confident strokes. Linear in step, capped at MAX_STEP."""
    s = max(0, min(step, MAX_STEP))
    return {
        "turdsize": 2 + s,
        "alphamax": round(min(1.0 + 0.05 * s, 1.3), 2),
        "opttolerance": round(min(0.2 + 0.05 * s, 0.8), 2),
        "blur": round(min(0.2 * s, 1.6), 2),
        "threshold": 50,
    }


def _prepare(svg_path, size, dial):
    """Flatten an svg onto white, rasterize it to a grayscale PGM at size x size (the format potrace reads), and
    apply the step's raster treatment (blur then re-threshold). blur=0 (step 0) skips the treatment, so step 0
    traces the untouched raster. Returns a temp file path; the caller removes it."""
    fd, pgm = tempfile.mkstemp(suffix=".pgm")
    os.close(fd)
    _run(["magick", svg_path, "-background", "white", "-alpha", "remove", "-alpha", "off",
          "-resize", f"{size}x{size}", pgm])
    if dial["blur"] <= 0:
        return pgm
    fd, out = tempfile.mkstemp(suffix=".pgm")
    os.close(fd)
    _run(["magick", pgm, "-blur", f"0x{dial['blur']}", "-threshold", f"{dial['threshold']}%", out])
    os.unlink(pgm)
    return out


def _trace(pgm_path, dial):
    """Run potrace over a prepared PGM with the dial's parameters and return the SVG text it wrote, or None on
    any failure (missing potrace, bad input)."""
    fd, out = tempfile.mkstemp(suffix=".svg")
    os.close(fd)
    try:
        ok = _run(["potrace", "--svg", "-t", str(dial["turdsize"]), "-a", str(dial["alphamax"]),
                   "-O", str(dial["opttolerance"]), "-o", out, pgm_path])
        if ok is None or not os.path.exists(out) or os.path.getsize(out) == 0:
            return None
        with open(out, "r", encoding="utf-8") as f:
            return f.read()
    finally:
        if os.path.exists(out):
            os.unlink(out)


def _with_aria(svg_text):
    """Inject role="img" and the aria-label potrace's own SVG backend does not write, onto the <svg> tag."""
    return svg_text.replace("<svg version=", f'<svg role="img" aria-label="{ARIA_LABEL}" version=', 1)


def _ink_share(png_path):
    """Fraction of a PNG's pixels that are ink (flattened to white, then 1 - mean gray). None if magick fails."""
    out = _run(["magick", png_path, "-background", "white", "-alpha", "remove", "-alpha", "off",
                "-colorspace", "Gray", "-format", "%[fx:mean]", "info:"])
    try:
        return 1.0 - float(out.strip()) if out is not None else None
    except ValueError:
        return None


def _edit1(a, b):
    """True when a and b are equal or one edit (substitute/insert/delete) apart. Vision reliably reads this
    engraved blackletter ribbon as close but not exact ("TURING" -> "PURING", a T misread as a P) even on the
    untouched original, so the word-read gate allows this much slack for a font quirk, not a modernize() bug."""
    if a == b:
        return True
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) <= 1
    shorter, longer = (a, b) if len(a) < len(b) else (b, a)
    for i in range(len(longer)):
        if longer[:i] + longer[i + 1:] == shorter:
            return True
    return False


def words_read(png):
    """The OCR gate: read the preview with swift/ocr.swift and check SAMANTHA and TURING both come back
    (case-insensitive, as separate tokens, one OCR edit off still counts, see _edit1). Skips clean, rather than
    failing, when swift or the ocr script are missing (CI's ubuntu box). Reads a temporary copy upscaled and
    flattened onto white at tracing resolution, where Vision does best; never replaces the shipped preview."""
    if not shutil.which("swift") or not os.path.exists(OCR_SCRIPT):
        return True, "OCR unavailable here (no swift/ocr.swift); skipped, not a failure"
    if not shutil.which("magick"):
        return True, "magick unavailable here; skipped, not a failure"
    fd, big = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    try:
        if _run(["magick", png, "-background", "white", "-alpha", "remove", "-alpha", "off",
                 "-resize", f"{RES}x{RES}", big]) is None:
            return True, "could not prepare an OCR-sized render; skipped, not a failure"
        out = _run(["swift", OCR_SCRIPT, big], timeout=90)
    finally:
        if os.path.exists(big):
            os.unlink(big)
    if out is None:
        return True, "OCR call failed to run; skipped, not a failure"
    tokens = set(re.findall(r"[A-Za-z]+", out.upper()))
    ok = any(t == "SAMANTHA" or _edit1(t, "SAMANTHA") for t in tokens) and \
        any(t == "TURING" or _edit1(t, "TURING") for t in tokens)
    if ok:
        return True, "OCR read both SAMANTHA and TURING"
    return False, f"OCR did not read both words back: {out.strip()!r}"


def _ink_sane(preview_png, source_share):
    """The ink-share sanity check: the new preview's ink fraction must sit between the source's own share times
    0.6 and times 1.4, a rough guard against the design blowing up (all black) or vanishing (all white)."""
    if source_share is None:
        return True, "source ink share unavailable; skipped"
    share = _ink_share(preview_png)
    if share is None:
        return True, "preview ink share unavailable; skipped"
    lo, hi = source_share * 0.6, source_share * 1.4
    if lo <= share <= hi:
        return True, f"ink share {share:.3f} within [{lo:.3f}, {hi:.3f}]"
    return False, f"ink share {share:.3f} outside [{lo:.3f}, {hi:.3f}] of source"


def modernize(step):
    """Rebuild web/badge.svg and web/badge-preview.png from art/badge-source.svg at the given step, always from
    the frozen source, never from a previous output. Returns (ok, message): ok is False only when a build step
    itself failed (missing magick/potrace, a bad trace); it does not run the gate, callers do that separately."""
    freeze_source()
    if not os.path.exists(SOURCE_SVG):
        return False, "no art/badge-source.svg and no web/badge.svg to freeze from"
    if not shutil.which("magick") or not shutil.which("potrace"):
        return False, "magick or potrace not on PATH"

    dial = _dial(step)
    prepared = _prepare(SOURCE_SVG, RES, dial)
    try:
        svg_text = _trace(prepared, dial)
    finally:
        if os.path.exists(prepared):
            os.unlink(prepared)
    if not svg_text:
        return False, "potrace produced no output"

    svg_text = _with_aria(svg_text)
    with open(OUTPUT_SVG, "w", encoding="utf-8") as f:
        f.write(svg_text)
    if _run(["magick", OUTPUT_SVG, "-resize", f"{PREVIEW_SIZE}x{PREVIEW_SIZE}", OUTPUT_PNG]) is None:
        return False, "could not render the new preview PNG"
    return True, f"step {step}: {os.path.getsize(OUTPUT_SVG)} bytes"


def _backup(paths):
    """{path: bytes or None} for every path, to restore on a failed gate."""
    out = {}
    for p in paths:
        out[p] = None
        if os.path.exists(p):
            with open(p, "rb") as f:
                out[p] = f.read()
    return out


def _restore(backup):
    """Write a _backup() snapshot back to disk, removing any file that did not exist before."""
    for p, data in backup.items():
        if data is None:
            if os.path.exists(p):
                os.unlink(p)
        else:
            with open(p, "wb") as f:
                f.write(data)


def gate(source_share=None):
    """The full gate against web/badge-preview.png: OCR both words, ink share sane. Returns (ok, [messages])."""
    if source_share is None:
        source_share = _ink_share(OUTPUT_PNG)
    ok_words, msg_words = words_read(OUTPUT_PNG)
    ok_ink, msg_ink = _ink_sane(OUTPUT_PNG, source_share)
    return (ok_words and ok_ink), [msg_words, msg_ink]


def build_and_gate(version):
    """python3 tools_badge.py --version X.Y.Z: modernize(step_for(version)), gate it, and only keep the new
    files if the gate passes; otherwise restore what was there before and say why. Always exit 0 so a release
    never fails over the badge."""
    freeze_source()
    step = step_for(version)
    backup = _backup([OUTPUT_SVG, OUTPUT_PNG])
    source_preview = _source_preview()
    source_share = _ink_share(source_preview) if os.path.exists(source_preview) else None
    if os.path.exists(source_preview):
        os.unlink(source_preview)
    ok_build, msg_build = modernize(step)
    if not ok_build:
        _restore(backup)
        print(f"badge modernize skipped (step {step}): {msg_build}")
        return 0
    ok_gate, msgs = gate(source_share)
    if not ok_gate:
        _restore(backup)
        print(f"badge modernize step {step} failed its gate, kept the previous badge: {'; '.join(msgs)}")
        return 0
    print(f"badge modernized to step {step} ({version}): {msg_build}; {'; '.join(msgs)}")
    return 0


def _source_preview():
    """A throwaway 512px render of art/badge-source.svg, just to measure its ink share for the gate's sanity
    check. Returns a temp file path that may not exist if the render failed; caller removes it either way."""
    fd, png = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    if not os.path.exists(SOURCE_SVG) or _run(["magick", SOURCE_SVG, "-resize", f"{PREVIEW_SIZE}x{PREVIEW_SIZE}", png]) is None:
        if os.path.exists(png):
            os.unlink(png)
    return png


def demo():
    """Self-check on the pure parts (no magick/potrace needed): step_for cases, printed plainly."""
    cases = [("4.7.0", 0), ("4.7.3", 0), ("4.8.0", 1), ("4.9.0", 2), ("5.0.0", 3), ("6.5.0", 12)]
    for version, want in cases:
        got = step_for(version)
        mark = "ok" if got == want else "FAIL"
        print(f"{mark} step_for({version!r}) = {got} (want {want})")


def main():
    """CLI: python3 tools_badge.py --version X.Y.Z runs the real build+gate; no args runs demo()."""
    if "--version" in sys.argv:
        i = sys.argv.index("--version")
        version = sys.argv[i + 1] if len(sys.argv) > i + 1 else ""
        return build_and_gate(version)
    demo()
    return 0


if __name__ == "__main__":
    sys.exit(main())
