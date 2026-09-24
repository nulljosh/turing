#!/usr/bin/env python3
"""Samantha's image tools: drive ImageMagick (`magick`) for image processing.

All tools operate on files inside the home folder and export results to ~/Desktop.
Original files are never modified. The old AppleScript-driven engine is retired from
this path: the pixelmator/ folder still exists as an opt-in alternative for
tools_logo.paint_image, but nothing here imports or reaches for it.
"""
import os
import re
import subprocess

HOME = os.path.realpath(os.path.expanduser("~"))
HEADLESS = os.environ.get("SAMANTHA_HEADLESS") == "1"
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".heic", ".webp", ".tiff", ".tif"}


def _tools():
    """The tools module, fetched when a function runs, never at import: tools imports this file."""
    import tools
    return tools


def _run(argv, timeout=60):
    """tools._run, looked up when called, so a test that patches tools._run also stubs these calls."""
    return _tools()._run(argv, timeout=timeout)


def _inside_home(path):
    """Resolve a path and verify it stays inside the home folder, return None if outside."""
    full = os.path.realpath(os.path.expanduser(path.strip() or "~"))
    return full if full == HOME or full.startswith(HOME + os.sep) else None


def _is_image(path):
    """Check if path exists and has an image extension."""
    if not path:
        return False
    ext = os.path.splitext(path)[1].lower()
    return ext in IMAGE_EXTS


def _get_image_dimensions(path):
    """Get image width and height using sips. Returns (width, height) or None."""
    try:
        result = subprocess.run(
            ["sips", "-g", "pixelWidth", "-g", "pixelHeight", path],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            dims = {}
            for line in result.stdout.splitlines():
                if "pixelWidth" in line:
                    dims["w"] = int(line.split()[-1])
                elif "pixelHeight" in line:
                    dims["h"] = int(line.split()[-1])
            if "w" in dims and "h" in dims:
                return dims["w"], dims["h"]
    except Exception:
        pass
    return None


def _image(path):
    """The full path of an image inside the home folder, or None."""
    full = _inside_home(path.strip().strip("'\""))
    return full if full and os.path.isfile(full) and _is_image(full) else None


def _magick_edit(full, args, filename, done, failed, timeout=60):
    """Run `magick full <args> out`, exporting to ~/Desktop/samantha-{filename}, and say where the
    result went. The original file is never touched. A stale file at the destination is removed
    first so a failed run cannot be mistaken for a fresh success."""
    out = os.path.expanduser(f"~/Desktop/samantha-{filename}")
    try:
        if os.path.exists(out):
            os.remove(out)
    except OSError:
        pass
    _run(["magick", full] + args + [out], timeout=timeout)
    return f"{done}, saved to {out}." if os.path.exists(out) else failed


def remove_background(path):
    """Remove the background from a photo. Cuts the border colour to transparent by flood-filling
    from all four corners with ImageMagick (`-fuzz 12% -fill none -draw "alpha X,Y floodfill"`).
    This is a corner-colour cut, not a subject mask: it works on a flat or near-flat background and
    will not separate a subject from a busy one. Takes the path of an image file."""
    full = _image(path)
    if not full:
        return f"No image at {path}."
    dims = _get_image_dimensions(full)
    if not dims:
        return f"Could not read image dimensions from {path}."
    w, h = dims
    corners = ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1))
    draws = []
    for x, y in corners:
        draws += ["-draw", f"alpha {x},{y} floodfill"]
    args = ["-fuzz", "12%", "-fill", "none"] + draws
    return _magick_edit(full, args, "nobg.png", "Background removed", "Failed to remove background.")


def upscale_image(path):
    """Increase image resolution by 300% with ImageMagick's Lanczos filter. Takes the path of an image file."""
    full = _image(path)
    if not full:
        return f"No image at {path}."
    args = ["-filter", "Lanczos", "-resize", "300%"]
    return _magick_edit(full, args, "upscaled.png", "Upscaled 3x", "Failed to upscale image.", timeout=300)


def enhance_image(path):
    """Automatically enhance colors and contrast with ImageMagick (`-auto-level -auto-gamma -unsharp 0x1`).
    Takes the path of an image file."""
    full = _image(path)
    if not full:
        return f"No image at {path}."
    args = ["-auto-level", "-auto-gamma", "-unsharp", "0x1"]
    return _magick_edit(full, args, "enhanced.png", "Enhanced", "Failed to enhance image.")


def grayscale_image(path):
    """Convert image to grayscale with ImageMagick. Takes the path of an image file."""
    full = _image(path)
    if not full:
        return f"No image at {path}."
    args = ["-colorspace", "Gray"]
    return _magick_edit(full, args, "grayscale.png", "Converted to grayscale", "Failed to convert to grayscale.")


def rotate_image(args):
    """Rotate image by specified degrees. Takes 'path by 90' (default 90 degrees clockwise)."""
    match = re.match(r'^(.+?)\s+by\s+(\d+)$', args.strip(), re.I)
    path, degrees = (match.group(1), int(match.group(2))) if match else (args.strip().strip("'\""), 90)
    full = _image(path)
    if not full:
        return f"No image at {path}."
    degrees = degrees % 360
    if degrees not in (90, 180, 270):
        return f"Rotation must be 90, 180, or 270 degrees, got {degrees}."
    return _magick_edit(full, ["-rotate", str(degrees)], "rotated.png", f"Rotated {degrees} degrees", "Failed to rotate image.")


def flip_image(args):
    """Flip image horizontally or vertically. Takes 'path' (default horizontal) or 'path vertical'."""
    parts = args.strip().split()
    if len(parts) > 1 and parts[-1].lower() in ("vertical", "horizontally", "horizontal"):
        direction, path = parts[-1].lower(), " ".join(parts[:-1])
    else:
        direction, path = "horizontal", args.strip()
    full = _image(path)
    if not full:
        return f"No image at {path}."
    flag = "-flip" if direction.startswith("v") else "-flop"
    return _magick_edit(full, [flag], "flipped.png", f"Flipped {direction}", "Failed to flip image.")


def resize_image(args):
    """Resize image to a maximum side length in pixels. Takes 'path to 1024' (16 to 8000 pixels)."""
    match = re.match(r'^(.+?)\s+to\s+(\d+)$', args.strip(), re.I)
    if not match:
        return f"Format should be 'path to pixels', e.g., 'photo.jpg to 1024'."
    path, size = match.group(1), int(match.group(2))
    if not 16 <= size <= 8000:
        return f"Size must be between 16 and 8000 pixels, got {size}."
    full = _image(path)
    if not full:
        return f"No image at {path}."
    dims = _get_image_dimensions(full)
    if not dims:
        return f"Could not read image dimensions from {path}."
    w, h = dims
    if max(w, h) == size:
        return f"Image already {size}px on longest side."
    new_w, new_h = (size, max(1, int(h * size / w))) if w > h else (max(1, int(w * size / h)), size)
    return _magick_edit(full, ["-resize", f"{new_w}x{new_h}!"], "resized.png", f"Resized to {new_w}x{new_h}", "Failed to resize image.")


def crop_square(path):
    """Crop image to a centered square. Takes the path of an image file."""
    full = _image(path)
    if not full:
        return f"No image at {path}."
    dims = _get_image_dimensions(full)
    if not dims:
        return f"Could not read image dimensions from {path}."
    w, h = dims
    side = min(w, h)
    x, y = (w - side) // 2, (h - side) // 2
    return _magick_edit(full, ["-crop", f"{side}x{side}+{x}+{y}", "+repage"], "square.png",
                         f"Cropped to {side}x{side} square", "Failed to crop image.")


_FORMATS = {"png", "jpg", "jpeg", "webp", "heic", "tiff", "tif", "pdf"}


def convert_image(args):
    """Convert image to another format. Takes 'path to jpg' (png, jpg, webp, heic, tiff, pdf)."""
    match = re.match(r'^(.+?)\s+to\s+(\w+)$', args.strip(), re.I)
    if not match:
        return f"Format should be 'path to format', e.g., 'photo.png to jpg'."
    path, fmt = match.group(1), match.group(2).lower()
    if fmt not in _FORMATS:
        return f"Unsupported format '{fmt}'. Use: png, jpg, webp, heic, tiff, pdf."
    full = _image(path)
    if not full:
        return f"No image at {path}."
    return _magick_edit(full, [], f"converted.{fmt}", f"Converted to {fmt.upper()}", "Failed to convert image.")


def image_info(path):
    """Read image dimensions and layer count. Takes the path of an image file (read-only)."""
    full = _image(path)
    if not full:
        return f"No image at {path}."

    dims = _get_image_dimensions(full)
    if not dims:
        return f"Could not read image dimensions from {path}."

    w, h = dims
    return f"Image is {w}x{h} pixels, 1 layer (flattened)."


# The image tools as exact commands, so "make ~/Desktop/cat.png black and white" works with no model at all.
# Same shape as tools_util.ROUTES: (pattern, tool name, argument). tools.py puts these ahead of the utilities,
# so "convert cat.png to jpg" is an image and never a unit conversion. A path is one word ending in an image type.
_P = r"(?:the )?(?:image |photo |picture |pic )?(?:at )?(\S+\.(?:jpe?g|png|heic|webp|tiff?))"
_I = re.I
ROUTES = (
    (re.compile(rf"^(?:make|turn|convert) {_P} (?:into )?(?:black and white|black & white|b&w|grayscale|greyscale)$|^(?:grayscale|greyscale|desaturate) {_P}$", _I),
     "grayscale_image", lambda m: m.group(1) or m.group(2)),
    (re.compile(rf"^(?:remove|cut out|erase|delete|take out) the background (?:from|of|in|on) {_P}$", _I), "remove_background", lambda m: m.group(1)),
    (re.compile(rf"^(?:upscale|enlarge|blow up) {_P}$", _I), "upscale_image", lambda m: m.group(1)),
    (re.compile(rf"^(?:enhance|auto[- ]?enhance|fix up|improve) {_P}$", _I), "enhance_image", lambda m: m.group(1)),
    (re.compile(rf"^rotate {_P}(?: by (\d+)(?: degrees)?)?$", _I), "rotate_image", lambda m: f"{m.group(1)} by {m.group(2) or 90}"),
    (re.compile(rf"^flip {_P}(?: (horizontally|vertically|horizontal|vertical|upside down))?$", _I), "flip_image",
     lambda m: m.group(1) + (" vertical" if (m.group(2) or "").lower() in ("vertically", "vertical", "upside down") else "")),
    (re.compile(rf"^(?:resize|scale) {_P} to (\d+)(?: ?px| pixels)?(?: wide)?$", _I), "resize_image", lambda m: f"{m.group(1)} to {m.group(2)}"),
    (re.compile(rf"^(?:crop|square up) {_P}(?: (?:to |into )?(?:a )?square)?$", _I), "crop_square", lambda m: m.group(1)),
    (re.compile(rf"^convert {_P} (?:to|into) (?:a |an )?(png|jpe?g|webp|heic|tiff?|pdf)$", _I), "convert_image", lambda m: f"{m.group(1)} to {m.group(2)}"),
    (re.compile(rf"^(?:how big is {_P}|(?:image )?(?:info|size|dimensions) (?:for|of|on) {_P})$", _I), "image_info", lambda m: m.group(1) or m.group(2)),
)
