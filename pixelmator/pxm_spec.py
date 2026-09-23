"""pxm's trust boundary: what a spec may say. Exit codes, the shape and key tables, PxmError, colour and string
parsing, and validate_spec, which every spec passes before any AppleScript is written. Pure: no Mac, no app.
Split out of pxm.py, which re-exports every name here.
"""
import math
import os
import re

EXIT_USAGE = 2   # bad spec or arguments. Fix the input.
EXIT_ENV = 3     # this Mac is not ready: no app, no permission, not macOS.
EXIT_SCRIPT = 4  # Pixelmator refused something mid-script.
EXIT_VERIFY = 5  # script ran, but the result is not what the spec asked for.

SHAPES = {
    "rectangle": "rectangle shape layer",
    "rounded_rectangle": "rounded rectangle shape layer",
    "ellipse": "ellipse shape layer",
    "polygon": "polygon shape layer",
    "star": "star shape layer",
    "line": "line shape layer",
}
FORMATS = {
    "png": "PNG", "jpg": "JPEG", "jpeg": "JPEG", "tiff": "TIFF", "heic": "HEIC",
    "webp": "WebP", "svg": "SVG", "pdf": "PDF", "psd": "PSD", "pxd": "Pixelmator Pro",
}
SIPS_CAN_MEASURE = {"png", "jpg", "jpeg", "tiff", "heic"}
MAX_SIDE = 16384

COMMON_KEYS = {"type", "name", "x", "y", "cx", "cy", "opacity", "rotation"}
SHAPE_KEYS = COMMON_KEYS | {"width", "height", "fill", "stroke", "stroke_width"}
EXTRA_KEYS = {
    "rounded_rectangle": {"corner_radius"},
    "polygon": {"sides"},
    "star": {"points", "radius"},
}
CUTOUT_KEYS = COMMON_KEYS | {"ops", "fill", "stroke", "stroke_width"}
OPS = {"add": "add selection", "subtract": "subtract selection", "intersect": "intersect selection"}
OP_SHAPES = {"ellipse": "draw elliptical selection", "rectangle": "draw selection"}
TEXT_KEYS = COMMON_KEYS | {"text", "font", "size", "color"}
TOP_KEYS = {"width", "height", "background", "layers", "export", "keep_open"}


class PxmError(Exception):
    """A failure with an exit code and a hint, so the CLI can say what went wrong and what to try."""
    def __init__(self, message, hint="", code=EXIT_SCRIPT, number=None):
        """Keep the message, the hint, the exit code and the AppleScript error number."""
        super().__init__(message)
        self.message, self.hint, self.code, self.number = message, hint, code, number



# ---------- input: the trust boundary ----------

def parse_color(value):
    """'#RRGGBB' or '#RGB' -> (r, g, b) in AppleScript's 0..65535. None if invalid."""
    if not isinstance(value, str):
        return None
    m = re.fullmatch(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})", value)
    if not m:
        return None
    h = m.group(1)
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) * 257 for i in (0, 2, 4))


def as_string(text):
    """Quote text as an AppleScript string literal. Spec text can never become code."""
    out = []
    for ch in text:
        if ch in '\\"':
            out.append("\\" + ch)
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\t":
            out.append("\\t")
        elif ch == "\r":
            out.append("\\r")
        elif ord(ch) < 32 or ord(ch) == 127:
            raise PxmError("control character %r in text" % ch, code=EXIT_USAGE)
        else:
            out.append(ch)
    return '"' + "".join(out) + '"'


def _is_num(v):
    """A real, finite number that is not a bool."""
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def validate_spec(spec):
    """Check everything, report every problem at once, return a normalized copy."""
    errs = []

    def num(obj, key, where, lo, hi, default=None, required=False, integer=False):
        """A validated number from a spec object, or an error saying what was expected."""
        v = obj.get(key, default)
        if v is None:
            if required:
                errs.append("%s%s: required" % (where, key))
            return default
        if not _is_num(v) or (integer and int(v) != v) or not lo <= v <= hi:
            kind = "whole number" if integer else "number"
            errs.append("%s%s: expected a %s from %s to %s, got %r" % (where, key, kind, lo, hi, v))
            return default
        return int(v) if integer else v

    def color(obj, key, where):
        """A validated #RRGGBB color from a spec object, or an error."""
        if key not in obj:
            return None
        c = parse_color(obj[key])
        if c is None:
            errs.append('%s%s: expected "#RRGGBB", got %r' % (where, key, obj[key]))
        return c

    def coord(obj, key, where, default):
        """A validated coordinate: a number or the word center."""
        v = obj.get(key, default)
        if v is None and default is None:
            return None
        if v != "center" and not (_is_num(v) and abs(v) <= MAX_SIDE * 2):
            errs.append('%s%s: expected a number or "center", got %r' % (where, key, v))
        return v

    if not isinstance(spec, dict):
        raise PxmError("spec must be a JSON object", code=EXIT_USAGE)
    for k in sorted(set(spec) - TOP_KEYS):
        errs.append("%s: unknown key (allowed: %s)" % (k, ", ".join(sorted(TOP_KEYS))))

    out = {
        "width": num(spec, "width", "", 1, MAX_SIDE, required=True, integer=True),
        "height": num(spec, "height", "", 1, MAX_SIDE, required=True, integer=True),
        "background": color(spec, "background", ""),
        "keep_open": spec.get("keep_open", True),
        "layers": [],
        "export": [],
    }
    if not isinstance(out["keep_open"], bool):
        errs.append("keep_open: expected true or false, got %r" % (out["keep_open"],))

    layers = spec.get("layers", [])
    if not isinstance(layers, list):
        errs.append("layers: expected a list")
        layers = []
    if not layers and "background" not in spec:
        errs.append("layers: nothing to draw (give layers or a background)")

    for i, raw in enumerate(layers):
        where = "layers[%d]." % i
        if not isinstance(raw, dict):
            errs.append("layers[%d]: expected an object" % i)
            continue
        kind = raw.get("type")
        if kind not in ("text", "cutout") and kind not in SHAPES:
            errs.append("%stype: expected one of %s, got %r"
                        % (where, ", ".join(sorted(list(SHAPES) + ["text", "cutout"])), kind))
            continue
        allowed = {"text": TEXT_KEYS, "cutout": CUTOUT_KEYS}.get(
            kind, SHAPE_KEYS | EXTRA_KEYS.get(kind, set()))
        for k in sorted(set(raw) - allowed):
            errs.append("%s%s: unknown key for a %s layer" % (where, k, kind))

        layer = {
            "type": kind,
            "name": raw.get("name"),
            # A cutout is drawn in canvas coordinates, so it stays put unless told to move.
            "x": coord(raw, "x", where, None if kind == "cutout" else "center"),
            "y": coord(raw, "y", where, None if kind == "cutout" else "center"),
            # cx/cy place the layer by its center. Needed when the size is only known in the app.
            "cx": num(raw, "cx", where, -MAX_SIDE, MAX_SIDE * 2),
            "cy": num(raw, "cy", where, -MAX_SIDE, MAX_SIDE * 2),
            "opacity": num(raw, "opacity", where, 0, 100, integer=True),
            "rotation": num(raw, "rotation", where, 0, 359.999),  # counterclockwise, like the app
        }
        for a, b in (("x", "cx"), ("y", "cy")):
            if a in raw and b in raw:
                errs.append("%s%s: give %s or %s, not both" % (where, a, a, b))
        if layer["name"] is not None and not isinstance(layer["name"], str):
            errs.append("%sname: expected text" % where)

        if kind == "cutout":
            # Curves without a pen tool: combine ovals and rectangles, then turn the result
            # into one vector shape.
            ops = raw.get("ops")
            if not isinstance(ops, list) or not ops:
                errs.append("%sops: expected a non-empty list" % where)
                ops = []
            clean = []
            for j, op in enumerate(ops):
                w2 = "%sops[%d]." % (where, j)
                if not isinstance(op, dict):
                    errs.append("%sops[%d]: expected an object" % (where, j))
                    continue
                for k in sorted(set(op) - {"op", "shape", "x", "y", "width", "height"}):
                    errs.append("%s%s: unknown key" % (w2, k))
                if op.get("op", "add") not in OPS:
                    errs.append("%sop: expected add, subtract or intersect, got %r" % (w2, op.get("op")))
                if op.get("shape", "ellipse") not in OP_SHAPES:
                    errs.append("%sshape: expected ellipse or rectangle, got %r" % (w2, op.get("shape")))
                clean.append({
                    "op": op.get("op", "add"), "shape": op.get("shape", "ellipse"),
                    "x": num(op, "x", w2, -MAX_SIDE, MAX_SIDE, required=True, integer=True),
                    "y": num(op, "y", w2, -MAX_SIDE, MAX_SIDE, required=True, integer=True),
                    "width": num(op, "width", w2, 1, MAX_SIDE, required=True, integer=True),
                    "height": num(op, "height", w2, 1, MAX_SIDE, required=True, integer=True)})
            if clean and clean[0]["op"] != "add":
                errs.append("%sops[0].op: the first op must be add" % where)
            layer.update(ops=clean, fill=color(raw, "fill", where), stroke=color(raw, "stroke", where),
                         stroke_width=num(raw, "stroke_width", where, 0, 200))
            if "fill" not in raw and "stroke" not in raw:
                errs.append("%sfill: a shape needs a fill or a stroke, or it is invisible" % where)
            if "stroke" in raw and not layer["stroke_width"]:
                layer["stroke_width"] = 4
        elif kind == "text":
            text = raw.get("text")
            if not isinstance(text, str) or not text.strip():
                errs.append("%stext: required, non-empty" % where)
            font = raw.get("font")
            if font is not None and (not isinstance(font, str) or not font.strip()):
                errs.append("%sfont: expected a font name" % where)
            layer.update(text=text, font=font, color=color(raw, "color", where),
                         size=num(raw, "size", where, 1, 5000, default=72, integer=True))
        else:
            layer.update(
                width=num(raw, "width", where, 1, MAX_SIDE, required=True),
                height=num(raw, "height", where, 1, MAX_SIDE, required=True),
                fill=color(raw, "fill", where), stroke=color(raw, "stroke", where),
                stroke_width=num(raw, "stroke_width", where, 0, 200),
                corner_radius=num(raw, "corner_radius", where, 0, MAX_SIDE),
                sides=num(raw, "sides", where, 3, 11, integer=True),
                points=num(raw, "points", where, 3, 20, integer=True),
                radius=num(raw, "radius", where, 10, 100),
            )
            if "fill" not in raw and "stroke" not in raw:
                errs.append("%sfill: a shape needs a fill or a stroke, or it is invisible" % where)
            if "stroke" in raw and not layer["stroke_width"]:
                layer["stroke_width"] = 4
        out["layers"].append(layer)

    exports = spec.get("export", [])
    if isinstance(exports, str):
        exports = [exports]
    if not isinstance(exports, list):
        errs.append("export: expected a path or a list of paths")
        exports = []
    for p in exports:
        ext = p.rsplit(".", 1)[-1].lower() if isinstance(p, str) and "." in p else ""
        if ext not in FORMATS:
            errs.append("export: %r must end in one of: %s" % (p, ", ".join(sorted(FORMATS))))
            continue
        out["export"].append(os.path.abspath(os.path.expanduser(p)))

    if errs:
        raise PxmError("invalid spec:\n  " + "\n  ".join(errs),
                       hint="Fix the listed keys. See SKILL.md for the full spec.", code=EXIT_USAGE)
    return out
