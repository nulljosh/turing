"""Her hands on the screen: click the words you name, type, press a key. She finds what to click the way you would,
by reading the screen (macOS Vision OCR with positions, ocr.swift --boxes), and clicks with cliclick. Every one of
these is a write, so the harness shows the step and asks before it happens, and SAMANTHA_HEADLESS only describes it.

Needs cliclick (brew install cliclick), and Screen Recording plus Accessibility allowed for the terminal (macOS asks).
"""
import os
import re
import shutil
import subprocess
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
KEYS = {"return": "return", "enter": "enter", "tab": "tab", "escape": "esc", "esc": "esc", "space": "space",
        "delete": "delete", "backspace": "delete", "up": "arrow-up", "down": "arrow-down", "left": "arrow-left",
        "right": "arrow-right", "page up": "page-up", "page down": "page-down", "home": "home", "end": "end"}
TYPE_LIMIT = 500  # characters per type_text, a paste-sized step, never a novel


def _headless():
    """True when nothing visible may happen (evals, tests)."""
    return os.environ.get("SAMANTHA_HEADLESS") == "1"


def _run(argv, timeout=60):
    """Run a command and return its stdout, or "" when it failed or is missing."""
    try:
        return subprocess.run(argv, capture_output=True, text=True, timeout=timeout).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def screen_boxes():
    """Every line of text on the main screen as (text, x, y) with x, y the line's center in screen points,
    top to bottom. [] when the screen cannot be read."""
    fd, shot = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    try:
        _run(["screencapture", "-x", "-m", "-t", "png", shot], timeout=15)
        out = _run(["swift", os.path.join(HERE, "ocr.swift"), "--boxes", shot], timeout=90)
    finally:
        os.unlink(shot)
    return parse_boxes(out)


def parse_boxes(out):
    """ocr.swift --boxes output into [(text, x, y)] centers in points. Lines that do not parse are skipped."""
    lines = out.splitlines()
    if not lines or not lines[0].startswith("SCREEN\t"):
        return []
    try:
        width, height = (float(v) for v in lines[0].split("\t")[1:3])
    except ValueError:
        return []
    boxes = []
    for line in lines[1:]:
        parts = line.split("\t", 4)
        try:
            x, y, w, h = (float(v) for v in parts[:4])
        except ValueError:
            continue
        if len(parts) == 5 and parts[4].strip():
            boxes.append((parts[4].strip(), round((x + w / 2) * width), round((y + h / 2) * height)))
    return boxes


def find(target, boxes):
    """The best line for a target: an exact match first, then the shortest line that contains it. None if absent."""
    want = target.strip().lower()
    exact = [b for b in boxes if b[0].lower().strip(" .:") == want]
    if exact:
        return exact[0]
    holding = sorted((b for b in boxes if want in b[0].lower()), key=lambda b: len(b[0]))
    return holding[0] if holding else None


def click_text(target):
    """Click the words on the screen you name ("click Sign in"). She reads the screen to find them; asks first."""
    target = target.strip().strip("\"'")
    if not target:
        return 'Click what? Say it like "click Sign in".'
    if _headless():
        return f"Would click {target}."
    if not shutil.which("cliclick"):
        return "To click for you I need cliclick: brew install cliclick, then ask again."
    boxes = screen_boxes()
    if not boxes:
        return "I could not read the screen. Screen Recording may need to be allowed for this terminal."
    hit = find(target, boxes)
    if not hit:
        return f"I do not see {target} on the screen."
    _run(["cliclick", f"c:{hit[1]},{hit[2]}"], timeout=10)
    return f"Clicked {hit[0]}."


def type_text(text):
    """Type text into whatever has focus ("type hello world"). Asks first."""
    if not text.strip():
        return 'Type what? Say it like "type hello".'
    if len(text) > TYPE_LIMIT:
        return f"That is {len(text):,} characters; I type at most {TYPE_LIMIT} at a time."
    if _headless():
        return f"Would type {text}."
    if not shutil.which("cliclick"):
        return "To type for you I need cliclick: brew install cliclick, then ask again."
    _run(["cliclick", "t:" + text], timeout=30)
    return f"Typed {text}."


def press_key(key):
    """Press one key: return, tab, escape, space, delete, an arrow, page up or down, home, end. Asks first."""
    name = re.sub(r"\s+", " ", key.strip().lower()).removesuffix(" key")
    if name not in KEYS:
        return f"I can press {', '.join(sorted(KEYS))}."
    if _headless():
        return f"Would press {name}."
    if not shutil.which("cliclick"):
        return "To press keys for you I need cliclick: brew install cliclick, then ask again."
    _run(["cliclick", "kp:" + KEYS[name]], timeout=10)
    return f"Pressed {name}."
