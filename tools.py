#!/usr/bin/env python3
"""Samantha's hands: a small fixed set of things she can do on this Mac.

Two layers. act() is a regex router, instant and exact, same category as
arithmetic/clock in ask.py: a recognisable command has one right action, so no
model is involved. agent() is for anything multi-step ("poke around hacker news
and tell me what's up"): qwen3:1.7b via Ollama's native tool calling drives the
same TOOLS. The 0.5B cannot pick tools reliably, that is a hardware ceiling,
not a tuning problem, so she borrows a bigger head for her hands.

No shell tool, deliberately. Every tool is a fixed argv, never a string a model
wrote handed to sh.
"""
import html
import json
import math
import os
import re
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
import tools_util
from tools_image import remove_background, upscale_image, enhance_image, grayscale_image, rotate_image, flip_image, resize_image, crop_square, convert_image, image_info

AGENT_MODEL = "qwen3:1.7b"  # 8B was right but 7.6GB and minutes per run; 1.7B is right in 5s once the harness prefetches
OLLAMA_CHAT = "http://localhost:11434/api/chat"
BROWSER = "Google Chrome"
APP_DIRS = ("/Applications", "/System/Applications", "/System/Applications/Utilities",
            os.path.expanduser("~/Applications"))
SITES = {
    "hacker news": "https://news.ycombinator.com", "hn": "https://news.ycombinator.com",
    "github": "https://github.com", "youtube": "https://youtube.com",
    "gmail": "https://mail.google.com", "reddit": "https://reddit.com",
    "twitter": "https://x.com", "x": "https://x.com",
}


# SAMANTHA_HEADLESS=1: nothing visible or audible happens. For evals and
# development, so a test run never steals the screen from whoever is working.
HEADLESS = os.environ.get("SAMANTHA_HEADLESS") == "1"
_VISIBLE = ("open", "say", "screencapture")


def _run(argv, timeout=10):
    """Run a subprocess and return its output, or empty string in headless mode for visible apps."""
    if HEADLESS and argv[0] in _VISIBLE:
        return ""
    r = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    return (r.stdout or r.stderr).strip()


def installed_apps():
    """Scan Applications folders and return dict of app names to display names."""
    apps = {}
    for d in APP_DIRS:
        if os.path.isdir(d):
            for f in os.listdir(d):
                if f.endswith(".app"):
                    apps[f[:-4].lower()] = f[:-4]
    return apps


def _app_match(name):
    """Find an installed app by name, allowing partial matches and normalizing common names."""
    apps = installed_apps()
    key = re.sub(r"^(?:the |my )|(?: app)$", "", name.strip().lower())
    if key == "chrome":
        key = "google chrome"
    # exact, then unique-prefix: "pixelmator" finds "Pixelmator Pro"
    return apps.get(key) or next((v for k, v in sorted(apps.items()) if k.startswith(key)), None)


def open_app(name):
    """Open an installed macOS app by name."""
    match = _app_match(name)
    if not match:
        return f"No app called {name!r} on this Mac."
    _run(["open", "-a", match])
    return f"Opened {match}."


def _url(target):
    """Convert a target (URL, domain, or site name) to a full HTTPS URL."""
    t = target.strip().strip("\"'")
    if t.lower() in SITES:
        return SITES[t.lower()]
    if re.match(r"^https?://", t, re.I):
        return t
    if re.match(r"^[\w-]+(\.[\w-]+)+(/\S*)?$", t):
        return "https://" + t
    return None


def open_url(target):
    """Open a website in Chrome for Joshua to see. Returns no page contents. Takes a URL, a bare domain, or a known site name."""
    url = _url(target)
    if not url:
        return web_search(target)
    _run(["open", "-a", BROWSER, url])
    return f"Opened {url} in Chrome."


def web_search(query):
    """Open a web search in Chrome for Joshua to look at. Returns NO results to you. To learn what a page says, use read_page."""
    _run(["open", "-a", BROWSER, "https://duckduckgo.com/?q=" + urllib.parse.quote_plus(query)])
    return f"Searching for {query!r} in Chrome."


def current_tab():
    """Title and URL of the tab Chrome is showing right now."""
    out = _run(["osascript", "-e",
                f'tell application "{BROWSER}" to get (title of active tab of front window) & "\n" & (URL of active tab of front window)'])
    return out or "Chrome has no window open."


def read_page(target=""):
    """Fetch a web page and return its text. The ONLY way to know what a page says. Takes a URL, bare domain, or site name like 'hacker news'. No argument reads Chrome's current tab."""
    url = _url(target) if target else (current_tab().splitlines() or [""])[-1]
    if not url or not url.startswith("http"):
        return "No page to read."
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Macintosh) Samantha"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            raw = r.read(400_000).decode("utf-8", "ignore")
    except Exception as e:
        return f"Couldn't fetch {url}: {e}"
    raw = re.sub(r"(?is)<(script|style|noscript|svg)\b.*?</\1>", " ", raw)
    text = html.unescape(re.sub(r"<[^>]+>", " ", raw))
    # ponytail: tag-strip, not a readability parser. JS-rendered pages come back empty; add Chrome JS bridge then.
    return re.sub(r"\s+", " ", text).strip()[:3000]


def screenshot():
    """Take a screenshot of the screen and return the file path."""
    path = os.path.expanduser("~/Desktop/samantha-shot.png")
    _run(["screencapture", "-x", path])
    return f"Saved {path}."


def clipboard():
    """Read what is on the clipboard."""
    return _run(["pbpaste"])[:2000] or "The clipboard is empty."


def set_volume(level):
    """Set the Mac's output volume. Takes 0 to 100, or "up" or "down"."""
    step = {"up": 15, "down": -15}.get(str(level).strip().lower())
    n = max(0, min(100, current_volume() + step if step else int(float(level))))
    _run(["osascript", "-e", f"set volume output volume {n}"])
    return f"Volume at {n}."


def current_volume():
    """The Mac's output volume, 50 if it cannot be read."""
    out = _run(["osascript", "-e", "output volume of (get volume settings)"])
    return int(out) if out.isdigit() else 50


def battery():
    """Battery or power status of this Mac."""
    return _run(["pmset", "-g", "batt"]).splitlines()[-1].strip()


def say(text):
    """Speak text out loud."""
    if not HEADLESS:
        subprocess.Popen(["say", text[:500]])
    return f"Saying: {text[:80]}"


def _app(script, *args):
    """AppleScript that drives another app. Text rides in argv, never spliced into the script. Headless does nothing: no app launches, no note gets written."""
    return "" if HEADLESS else _run(["osascript", "-e", script, *args], timeout=30)


_MUSIC = {"play": ("play", "Playing."), "pause": ("pause", "Paused."),
          "next": ("next track", "Skipped."), "previous": ("previous track", "Went back one.")}
_NOW_PLAYING = '''if application "Music" is running then
tell application "Music"
if player state is playing then return (name of current track) & " by " & (artist of current track)
end tell
end if
return ""'''


def music(command):
    """Control the Music app. command is one of: play, pause, next, previous, playing."""
    c = command.strip().lower()
    if c == "playing":
        return _app(_NOW_PLAYING) or "Nothing is playing."
    if c not in _MUSIC:
        return f"I can play, pause, skip, go back, or tell you what's playing. Not {command!r}."
    # ponytail: Music.app only, no "play <song>". Add a library search when she gets asked for one.
    _app(f'tell application "Music" to {_MUSIC[c][0]}')
    return _MUSIC[c][1]


def weather(place=""):
    """Current weather. Takes a city, or nothing for here."""
    # ponytail: wttr.in one-liner, located by IP. Swap for Open-Meteo if it gets flaky.
    url = "https://wttr.in/" + urllib.parse.quote(place.strip()) + "?format=%l:+%C,+%t,+feels+%f"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "curl/8"}), timeout=10) as r:
            out = r.read(300).decode("utf-8", "ignore").strip()
    except Exception as e:
        return f"Couldn't get the weather: {e}"
    return out if "°" in out else f"No weather for {place!r}."


_TIMER = ("import sys,time,subprocess;time.sleep(float(sys.argv[1]));"
          "subprocess.run(['osascript','-e','display notification \"Time is up.\" with title \"Samantha\" sound name \"Glass\"']);"
          "subprocess.run(['say','Time is up'])")


_NUMBER_WORDS = {w: n for n, w in enumerate("zero one two three four five six seven eight nine ten".split())} | {"a": 1, "an": 1, "half": 0.5}


def duration(text):
    """Minutes in a spoken length of time: "90 seconds", "an hour", "half an hour", "5". None if it is not one."""
    t = str(text).lower().strip()
    m = re.match(r"^(\d+(?:\.\d+)?|[a-z]+)(?: an| a)?[ -]?(s|m|h)?[a-z]*$", t)
    if not m:
        return None
    n = float(m.group(1)) if m.group(1)[0].isdigit() else _NUMBER_WORDS.get(m.group(1))
    return None if n is None else round(n * {"s": 1 / 60, "m": 1, "h": 60}[m.group(2) or "m"], 4)


def timer(minutes):
    """Start a timer. Takes a length of time: "5", "90 seconds", "half an hour". Notifies and speaks when it is done."""
    span = duration(minutes)
    if span is None:
        return f"{minutes!r} is not a length of time."
    secs = span * 60
    if not 0 < secs <= 86400:
        return "A timer runs from a second to a day."
    # ponytail: a sleeping child process. No cancel, gone on reboot. Fine for tea.
    if not HEADLESS:
        subprocess.Popen([sys.executable, "-c", _TIMER, str(secs)], start_new_session=True)
    return f"Timer set for {secs / 60:g} minutes." if secs >= 60 else f"Timer set for {secs:g} seconds."


def new_note(text):
    """Create a note in the Notes app."""
    _app('on run argv\ntell application "Notes" to make new note with properties {body:item 1 of argv}\nend run', text)
    return f"Noted: {text[:80]}"


def new_reminder(text):
    """Add a reminder to the Reminders app."""
    # ponytail: no due date, "at 5" stays in the title. Parse times when that gets annoying.
    _app('on run argv\ntell application "Reminders" to make new reminder with properties {name:item 1 of argv}\nend run', text)
    return f"I'll remind you: {text[:80]}"


# ponytail: a repeating event only shows on the day it was first made, Calendar's scripting does not expand them. EventKit if that bites.
_TODAY = '''set d0 to current date
set time of d0 to 0
set d1 to d0 + 1 * days
set out to ""
tell application "Calendar"
repeat with c in calendars
repeat with e in (every event of c whose start date is greater than or equal to d0 and start date is less than d1)
set out to out & (time string of (get start date of e)) & " " & (summary of e) & linefeed
end repeat
end repeat
end tell
return out'''


def calendar_today():
    """What is on the calendar today."""
    return _app(_TODAY) or "Nothing on the calendar today."


HOME = os.path.realpath(os.path.expanduser("~"))


def _inside_home(path):
    """Resolve a path and verify it stays inside the home folder, return None if outside."""
    # realpath first: a symlink or ../ must not walk a read out of the home folder
    full = os.path.realpath(os.path.expanduser(path.strip() or "~"))
    return full if full == HOME or full.startswith(HOME + os.sep) else None


def list_dir(path="~"):
    """List a folder inside the home folder."""
    full = _inside_home(path)
    if not full or not os.path.isdir(full):
        return f"No folder at {path!r} inside your home folder."
    names = sorted(n for n in os.listdir(full) if not n.startswith("."))
    return ", ".join(names[:80]) or "Empty folder."


def read_file(path):
    """Read a text file inside the home folder."""
    full = _inside_home(path)
    if not full or not os.path.isfile(full):
        return f"No file at {path!r} inside your home folder."
    # ponytail: refuses dotfiles outright instead of a secrets allowlist; .env and .ssh stay unread
    if any(part.startswith(".") for part in os.path.relpath(full, HOME).split(os.sep)):
        return "I don't read hidden files."
    with open(full, "rb") as f:
        return f.read(3000).decode("utf-8", "ignore")


PXM = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pixelmator", "pxm.py")
# A 1.7B picks well and composes badly: left to write layers itself it put a
# pink rectangle over everything and set "TURING" at 360pt, and pxm rejected
# the spec. So she chooses, the harness lays out. Three choices, all enums.
PALETTES = {"ember": ("#15110D", "#F4C893", "#E8A96A"), "ink": ("#101418", "#FFFFFF", "#F2B33D"),
            "forest": ("#0F1A14", "#E9F2EA", "#6FBF73"), "signal": ("#16161A", "#FFFFFF", "#E5484D"),
            "paper": ("#F3EDE2", "#1A1410", "#C2562D")}
_LOGO_SCHEMA = {"type": "object", "required": ["letters", "palette", "motif"], "properties": {
    "letters": {"type": "string", "minLength": 1, "maxLength": 2},
    "palette": {"enum": list(PALETTES)}, "motif": {"enum": ["ring", "spark", "underline", "dot"]}}}


def _logo_layers(letters, palette, motif):
    """Build layer list for a simple logo design."""
    tile, ink, accent = PALETTES[palette]
    layers = [{"type": "rounded_rectangle", "name": "Tile", "width": 880, "height": 880, "corner_radius": 200, "fill": tile}]
    if motif == "ring":
        layers.append({"type": "ellipse", "name": "Ring", "width": 640, "height": 640, "stroke": accent, "stroke_width": 28})
    layers.append({"type": "text", "name": "Mark", "text": letters.upper(), "font": "HelveticaNeue-Bold",
                   "size": 340 if len(letters) == 1 else 280, "color": ink})
    if motif == "spark":
        layers.append({"type": "star", "name": "Spark", "x": 690, "y": 190, "width": 150, "height": 150, "points": 4, "radius": 35, "fill": accent})
    if motif == "underline":
        layers.append({"type": "rounded_rectangle", "name": "Line", "x": 362, "y": 730, "width": 300, "height": 28, "corner_radius": 14, "fill": accent})
    if motif == "dot":
        layers.append({"type": "ellipse", "name": "Dot", "x": 700, "y": 640, "width": 90, "height": 90, "fill": accent})
    return layers


# "Complex" mode: same rule, bigger control panel. She turns seven dials, the
# harness does the trigonometry, so whatever she picks comes out symmetric.
_COMPLEX_SCHEMA = {"type": "object", "required": ["letters", "palette", "rings", "rays", "ray_style", "orbit_dots", "star_points"],
                   "properties": {
    "letters": {"type": "string", "minLength": 1, "maxLength": 2}, "palette": {"enum": list(PALETTES)},
    "rings": {"type": "integer", "minimum": 2, "maximum": 5}, "rays": {"type": "integer", "minimum": 12, "maximum": 36},
    "ray_style": {"enum": ["bars", "dots", "stars"]}, "orbit_dots": {"type": "integer", "minimum": 0, "maximum": 16},
    "star_points": {"type": "integer", "minimum": 4, "maximum": 12}}}
_WANTS_COMPLEX = re.compile(r"\b(?:complex|intricate|detailed|elaborate|ornate|fancy|crazy|insane)\b", re.I)


def _complex_layers(letters, palette, rings, rays, ray_style, orbit_dots, star_points):
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
    L.append({"type": "text", "name": "Mark", "text": letters.upper(), "font": "HelveticaNeue-Bold",
              "size": 190 if len(letters) == 1 else 150, "color": ink})
    return L


# Wordless mode: no letters at all. She turns four dials, the harness lays the cells on a golden-angle spiral (the way a
# sunflower packs its seeds), so it is never symmetric in the same way twice and never has text.
_BLOOM_SCHEMA = {"type": "object", "required": ["palette", "cells", "shape", "lit"], "properties": {
    "palette": {"enum": list(PALETTES)}, "cells": {"type": "integer", "minimum": 55, "maximum": 233},
    "shape": {"enum": ["circle", "square"]}, "lit": {"type": "integer", "minimum": 1, "maximum": 5}}}
_WANTS_WORDLESS = re.compile(r"\b(?:no (?:text|letters|words|lettering)|wordless|textless|without (?:text|letters|words)|original|abstract)\b", re.I)


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
    """Design a logo and build it live in Pixelmator Pro. Takes a short description of what the logo is for. Say 'complex' for an intricate one."""
    fancy = bool(_WANTS_COMPLEX.search(description))
    wordless = bool(_WANTS_WORDLESS.search(description))
    prompt = ("Pick a logo for this. letters: its one or two initials. palette: ember (warm amber on dark), ink (white and gold on "
              "near-black), forest (green on dark), signal (red on dark), paper (dark on cream). ")
    if wordless:
        prompt = ("Pick a wordless logo, no letters at all. palette: ember (warm amber on dark), ink (white and gold on near-black), forest "
                  "(green on dark), signal (red on dark), paper (dark on cream). cells: how many cells spiral out from the centre, a Fibonacci "
                  "number reads best. shape: circle or square. lit: how many cells glow in the accent color. Logo for: " + description)
    else:
        prompt += ("This one should be intricate, so be bold with the numbers. rings: concentric rings. rays: marks around the rim. "
                   "ray_style: bars, dots or stars. orbit_dots: dots circling inside. star_points: points on the centre burst. "
                   if fancy else "motif: ring, spark, underline or dot. ") + "Logo for: " + description
    body = json.dumps({"model": AGENT_MODEL, "stream": False, "think": False, "format": _BLOOM_SCHEMA if wordless else _COMPLEX_SCHEMA if fancy else _LOGO_SCHEMA,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    try:
        with urllib.request.urlopen(urllib.request.Request(OLLAMA_CHAT, body, {"Content-Type": "application/json"}), timeout=180) as r:
            pick = json.loads(json.load(r)["message"]["content"])
        spec = {"layers": _bloom_layers(**pick) if wordless else _complex_layers(**pick) if fancy else _logo_layers(pick["letters"], pick["palette"], pick["motif"])}
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


TOOLS = {f.__name__: f for f in (open_app, open_url, web_search, current_tab, read_page, screenshot,
                                     clipboard, set_volume, battery, say, list_dir, read_file, make_logo, paint_image,
                                     music, weather, timer, new_note, new_reminder, calendar_today,
                                     remove_background, upscale_image, enhance_image, grayscale_image, rotate_image, flip_image, resize_image, crop_square, convert_image, image_info)}
TOOLS.update({f.__name__: f for f in tools_util.TOOLS})
globals().update({f.__name__: f for f in tools_util.TOOLS})  # eval/actions.py swaps every TOOLS name on this module for a recorder

_UNIT = {"s": 1 / 60, "m": 1, "h": 60}

_ROUTES = (
    (re.compile(r"^(?:play|resume)(?: (?:the |some |my )?(?:music|song|tunes))?$", re.I), lambda m: music("play")),
    (re.compile(r"^pause$|^(?:pause|stop) (?:the |my |this )?(?:music|song|track)$", re.I), lambda m: music("pause")),
    (re.compile(r"^(?:skip|next)(?: (?:this |the )?(?:song|track|one))?$", re.I), lambda m: music("next")),
    (re.compile(r"^(?:previous|last|go back a|go back one)(?: (?:song|track))?$", re.I), lambda m: music("previous")),
    (re.compile(r"^what(?:'s| is) (?:this song|playing)\b|^what song is (?:this|playing)", re.I), lambda m: music("playing")),
    (re.compile(r"^(?:what(?:'s| is) the |how(?:'s| is) the )?weather\b(?: like)?(?: today| outside| right now| now)*(?: (?:in|for) (.+))?$", re.I),
     lambda m: weather(m.group(1) or "")),
    (re.compile(r"^(?:set |start )?(?:a |an )?(?:timer (?:for )?(\d+(?:\.\d+)?) ?(s|m|h)\w*|(\d+(?:\.\d+)?)[ -]?(s|m|h)\w* timer)$", re.I),
     lambda m: timer(float(m.group(1) or m.group(3)) * _UNIT[(m.group(2) or m.group(4)).lower()])),
    (re.compile(r"^remind me (?:to |that |about )?(.+)$|^(?:add|create|make|set|new) (?:a |me a )?(?:new )?reminder(?: to| that says| saying|:)? (.+)$", re.I),
     lambda m: new_reminder(m.group(1) or m.group(2))),
    (re.compile(r"^(?:(?:make|create|take|write|add|new) (?:a |me a )?(?:new )?note|note)(?: that says| saying| that|:)? (.+)$", re.I), lambda m: new_note(m.group(1))),
    (re.compile(r"^what(?:'s| is) on (?:my |the )?(?:calendar|schedule|agenda)\b|^(?:my )?(?:calendar|schedule|agenda)(?: for)?(?: today)?$|^what do i have (?:on )?today", re.I),
     lambda m: calendar_today()),
    (re.compile(r"^(?:make|design|draw|create|build)(?: me)? (?:a |an )?((?:(?:complex|intricate|detailed|elaborate|ornate|fancy|crazy|insane|original|wordless|abstract|textless) )*)(?:logo|icon)(?: for| of)? (.+)$", re.I), lambda m: make_logo((m.group(1) or "") + m.group(2))),
    (re.compile(r"^(?:paint|repaint)(?: me)? (?:a picture of |a painting of |the (?:image|photo|picture) (?:at )?)?(\S+\.(?:jpe?g|png|heic|webp|tiff?))$", re.I), lambda m: paint_image(m.group(1))),
    (re.compile(r"^(?:(?:show me |tell me )?what(?:'s| is) (?:on|in) (?:my |the )?clipboard|(?:read|show)(?: me)? (?:my |the )?clipboard)\b", re.I), lambda m: clipboard()),
    (re.compile(r"^(?:set |turn |put )?(?:the |it |my )?(?:volume )?(?:up |down )?(?:to |at )(\d{1,3})\b", re.I), lambda m: set_volume(m.group(1))),
    (re.compile(r"^(?:set |turn )?(?:the )?volume (\d{1,3})\b", re.I), lambda m: set_volume(m.group(1))),
    (re.compile(r"^(?:turn )?(?:the |it )?(?:volume )?(up|down)$|^(?:turn )?(?:the )?volume (up|down)$|^(louder|quieter)$", re.I),
     lambda m: set_volume("up" if (m.group(1) or m.group(2) or m.group(3)).lower() in ("up", "louder") else "down")),
    (re.compile(r"^mute\b", re.I), lambda m: set_volume(0)),
    (re.compile(r"^(?:how(?:'s| is) (?:my |the )?battery|battery(?: level| status)?$|what(?:'s| is) (?:my |the )?battery|how much battery)", re.I), lambda m: battery()),
    (re.compile(r"^say (.+)$", re.I), lambda m: say(m.group(1))),
    (re.compile(r"^(?:list|show)(?: me)? (?:the )?(?:files|folder|contents) (?:in|of|at) (.+)$", re.I), lambda m: list_dir(m.group(1))),
    (re.compile(r"^(?:read|show|cat)(?: me)? (?:the )?file (.+)$", re.I), lambda m: read_file(m.group(1))),
    (re.compile(r"^(?:take a |grab a )?screenshot\b", re.I), lambda m: screenshot()),
    (re.compile(r"^what(?:'s| is) (?:on |in )?(?:my |the )?(?:current |open )?(?:tab|chrome|browser)\b", re.I), lambda m: current_tab()),
    (re.compile(r"^(?:search|google|look up)(?: the web)?(?: for)? (.+)$", re.I), lambda m: web_search(m.group(1))),
    (re.compile(r"^(?:open|launch|start) (?:up )?(?:chrome|the browser) (?:and |then )?(?:go to|open|visit|load) (.+)$", re.I), lambda m: open_url(m.group(1))),
    (re.compile(r"^(?:go to|visit|browse to|pull up) (.+)$", re.I), lambda m: open_url(m.group(1))),
    (re.compile(r"^(?:open|launch|start) (?:up )?(.+)$", re.I),
     # one unknown word is a mistyped app, say so. A phrase that is no app
     # ("the turing repo on github") is something to look for.
     lambda m: open_url(m.group(1)) if _url(m.group(1)) or (" " in m.group(1).strip() and not _app_match(m.group(1))) else open_app(m.group(1))),
)


def _util_route(name, arg):
    """A tools_util route as a tools.py one. The function is looked up on this module at call
    time, so eval/actions.py can swap it for a recorder like every other tool."""
    takes = getattr(tools_util, name).__code__.co_argcount
    return lambda m: globals()[name](arg(m)) if takes else globals()[name]()


_ROUTES = _ROUTES + tuple((pat, _util_route(name, arg)) for pat, name, arg in tools_util.ROUTES)  # 31 utility tools: math, text, dice, this Mac's vitals

# anything past the first verb phrase means more than one step: that is agent() work
_MULTISTEP = re.compile(r"\b(?:and (?:then )?(?:tell|read|find|summar|poke|look|check|see|click)|poke around|then )", re.I)
_ACTION = re.compile(r"^(?:open|launch|start|go to|visit|browse|pull up|search|google|look up|poke around|take a|grab a|screenshot|make|design|draw|paint|repaint|play|pause|skip|remind me|set a)\b", re.I)


# People do not type commands, they ask. "can you open chrome", "hey open
# github", "open up spotify for me please". Stripped once here so every route
# and is_action() see the bare command, instead of each regex growing its own
# politeness prefix. Live-tested 2026-09-20: 10 of 16 natural phrasings missed.
_LEAD = re.compile(r"^(?:(?:hey|ok|okay|yo|samantha|please|now|just)[, ]+)*"
                   r"(?:(?:can|could|would|will) you (?:please )?|i (?:want|need|would like|'d like) (?:you )?to |let's |go ahead and )?(?:please )?", re.I)
_TAIL = re.compile(r"(?:[, ]+(?:please|for me|real quick|now|thanks|thank you))+$", re.I)


def _bare(query):
    """Strip politeness markers (please, can you, etc.) from a command."""
    q = query.strip().rstrip(".!?")
    return _TAIL.sub("", _LEAD.sub("", q, count=1)).strip()


def act(query):
    """Do a recognisable single command, exactly. Returns the result or None."""
    q = _bare(query)
    if _MULTISTEP.search(q):
        return None
    for pattern, fn in _ROUTES:
        m = pattern.match(q)
        if m:
            return fn(m)
    return None


def is_action(query):
    """Check if query starts with an action verb, after stripping politeness markers."""
    return bool(_ACTION.match(_bare(query)))


def _schema(fn):
    """Build OpenAI tool schema from function signature and docstring."""
    args = fn.__code__.co_varnames[:fn.__code__.co_argcount]
    return {"type": "function", "function": {
        "name": fn.__name__, "description": fn.__doc__,
        "parameters": {"type": "object", "properties": {a: {"type": "string"} for a in args},
                       "required": [a for a in args if a != "target" or fn is open_url]}}}


def _named_page(task):
    """The URL or known site a task mentions, if any."""
    m = re.search(r"https?://\S+|\b[\w-]+(?:\.[\w-]+)+(?:/\S*)?", task)
    if m and _url(m.group(0).rstrip(".,")):
        return _url(m.group(0).rstrip(".,"))
    low = task.lower()
    return next((url for name, url in sorted(SITES.items(), key=lambda kv: -len(kv[0]))
                 if re.search(rf"\b{re.escape(name)}\b", low)), None)


# These fire something with a side effect the user did not see coming (a Shortcut can send a
# message, a clipboard write loses what was there, the screen goes dark). Only a command that
# names them runs them, never a model's own choice. The real fix is the harness asking first.
NOT_FOR_MODELS = {"run_shortcut", "copy_to_clipboard", "sleep_display", "call_mcp_tool"}


def model_tools():
    """The tools a model may choose from: everything except NOT_FOR_MODELS."""
    return {n: f for n, f in TOOLS.items() if n not in NOT_FOR_MODELS}


def agent(task, max_steps=6, log=None, confirm=None):
    """Multi-step: let qwen3:8b drive TOOLS until it has an answer."""
    messages = [
        {"role": "system", "content": "You are Samantha, acting on Joshua's Mac through tools. Do what is asked in as few tool calls as possible, then answer in two or three plain sentences. Never invent page contents, read the page first."},
        {"role": "user", "content": task},
    ]
    # A small model asked to "poke around hacker news" opens a search and then
    # invents three stories. Same lesson as the rest of this project: the
    # harness retrieves, the model only reads. If the task names a page, it is
    # already fetched before the model says a word.
    named = _named_page(task)
    if named:
        if log:
            log(f"  [read_page({named})]")
        messages[1]["content"] += f"\n\nI already fetched {named} for you. Its text:\n{read_page(named)}"
    for _ in range(max_steps):
        body = json.dumps({"model": AGENT_MODEL, "messages": messages, "stream": False, "think": False,
                           "tools": [_schema(f) for f in model_tools().values()]}).encode()
        req = urllib.request.Request(OLLAMA_CHAT, body, {"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                msg = json.load(r)["message"]
        except Exception as e:
            return f"My hands need Ollama running with {AGENT_MODEL}, and it didn't answer: {e}"
        messages.append(msg)
        calls = msg.get("tool_calls") or []
        if not calls:
            return re.sub(r"(?s)<think>.*?</think>", "", msg.get("content", "")).strip()
        for c in calls:
            name, args = c["function"]["name"], c["function"].get("arguments") or {}
            fn = model_tools().get(name)
            try:
                if not fn:
                    result = f"No tool named {name}."
                elif confirm and name in WRITES and not confirm(name, tuple(map(str, args.values()))):
                    result = "The user said no."
                else:
                    takes = fn.__code__.co_varnames[:fn.__code__.co_argcount]
                    args = {k: v for k, v in args.items() if k in takes}
                    result = fn(**args)
            except Exception as e:
                result = f"{name} failed: {e}"
            if log:
                log(f"  [{name}({', '.join(map(str, args.values()))})]")
            messages.append({"role": "tool", "tool_name": name, "content": str(result)})
    return "I ran out of steps before finishing that."


HANDS_ADAPTER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hands-adapter")
HANDS_SYSTEM = 'You are Samantha\'s hands. Reply with one JSON tool call. If this is not a command, reply {"tool": null, "arg": ""}.'
_hands = None


# A pick with no argument to check (disk_space, uptime...) or a loose one needs evidence in the sentence: some word that
# is really about that tool. Round four confused ip_address with wifi_name and let "let me know in 10 minutes" write a note.
_EVIDENCE = {
    "disk_space": r"disk|storage|space|drive|room|full", "uptime": r"\bup\b|uptime|restart|reboot|been on|running|booted",
    "memory_usage": r"memory|\bram\b", "cpu_load": r"cpu|processor|load|busy|maxed|working|doing", "ip_address": r"\bip\b|address",
    "wifi_name": r"wi-?fi|network", "system_info": r"system|\bmac\b|macos|chip|computer|specs|about this", "list_shortcuts": r"shortcut",
    "flip_coin": r"coin|heads|tails", "make_uuid": r"uuid|guid", "time_in": r"time|clock|late", "days_until": r"\bday|sleeps|until|till|far away|count",
    "roll_dice": r"roll|dice|\bdie\b|\bd\d|throw|toss", "random_number": r"random|number", "make_password": r"password",
    "hash_text": r"hash|sha|checksum", "word_count": r"word", "tip": r"\btip", "is_prime": r"prime|factor|divid", "roman_numeral": r"roman",
    "morse_code": r"morse", "new_note": r"note|jot|write|remember|save|down", "say": r"\bsay|speak|announce|voice|aloud|out loud|words",
}
# ...and words that say the sentence is about a different tool. "say help in morse code" is morse_code, not say.
_AGAINST = {"say": r"morse|clock say", "wifi_name": r"address|\bip\b", "open_app": r"shortcut", "weather": r"\bapp\b", "web_search": r"\.(?:com|org|net|io|ca)\b"}


def _sound(tool, arg, query):
    """Is this pick safe to run? She was trained to copy her argument out of
    the sentence, never to compose one. So an argument that is not in the
    sentence is a guess, and a guess does not get to touch the Mac."""
    q_lower = query.lower()

    if tool in _EVIDENCE and not re.search(_EVIDENCE[tool], q_lower):
        return False
    if tool in _AGAINST and re.search(_AGAINST[tool], q_lower):
        return False

    if tool == "set_volume":
        # "mute" and "kill the sound" mean 0, and no digit appears in the sentence
        silent = arg == "0" and re.search(r"\b(?:mute|silen\w+|(?:sound|volume|audio) off|kill the (?:sound|volume|audio))\b", query, re.I)
        return arg in ("up", "down") or bool(silent) or (arg.isdigit() and arg in query)
    if tool == "music":
        # arg must be an exact command, not a loose phrase
        return arg in _MUSIC or arg == "playing"
    if tool == "timer":
        return duration(arg) is not None and arg.lower() in q_lower
    if tool in ("list_dir", "read_file"):
        return bool(arg)

    # An app or a site with no name is never a real command.
    if not arg and tool in ("open_app", "open_url"):
        return False

    # "notes" is the app, not something to write down.
    if tool == "new_note" and len(arg.split()) == 1 and arg.lower() in TOOLS:
        return False

    # Reject say() if arg looks like a timer duration
    if tool == "say" and duration(arg) is not None:
        return False  # "say 8 minutes" is likely a mispicked timer

    # Reject new_reminder() if query says "notes" not "remind"
    if tool == "new_reminder" and re.search(r"\bnotes?\b", q_lower) and not re.search(r"\b(?:remind|reminder)\b", q_lower):
        return False  # picked reminder when user said "notes"

    # Reject web_search for multi-step queries (dig through, poke around)
    if tool == "web_search" and re.search(r"\b(?:dig through|poke around|find something)\b", q_lower):
        return False  # this is agent work, not a simple search

    # Reject open_url() if arg looks like an app name
    if tool == "open_url":
        if arg.lower() in ("chrome", "safari", "firefox"):
            return False  # these are apps, not URLs
        if _url(arg) is None and " " not in arg.strip():
            return False  # one word that is no site. A phrase is something to look for, open_url searches it

    # Default: arg must appear in the query (lowercased)
    return tool in TOOLS and arg.lower() in q_lower


def pick(query):
    """Her own head for tool picking: the 0.5B with hands-adapter, trained by
    gen_hands_data.py, scored by eval/hands.py. Returns (tool, arg), ("agent",
    ""), or None when it is not a command, the pick is unsound, or the adapter
    or MLX is not here. None always means: carry on as if she had not looked."""
    global _hands
    if _hands is None:
        try:
            from mlx_lm import load
            _hands = load("mlx-community/Qwen2.5-0.5B-Instruct-4bit", adapter_path=HANDS_ADAPTER) if os.path.isdir(HANDS_ADAPTER) else False
        except Exception:
            _hands = False
    if not _hands:
        return None
    from mlx_lm import generate
    model, tok = _hands
    prompt = tok.apply_chat_template([{"role": "system", "content": HANDS_SYSTEM}, {"role": "user", "content": query}],
                                     add_generation_prompt=True, tokenize=False)
    try:
        got = json.loads(re.search(r"\{.*?\}", generate(model, tok, prompt=prompt, max_tokens=48, verbose=False), re.S).group(0))
        tool, arg = got.get("tool"), str(got.get("arg") or "").strip()
    except Exception:
        return None
    if tool == "agent":
        return "agent", ""
    return (tool, arg) if tool and _sound(tool, arg, query) else None


# Tools that leave something behind or send something out: a note, a reminder, a file on the
# Desktop, a Shortcut, the clipboard, a dark screen. The harness asks before any of these run.
WRITES = {"call_mcp_tool", "new_note", "new_reminder", "make_logo", "paint_image", "run_shortcut", "copy_to_clipboard", "sleep_display",
          "remove_background", "upscale_image", "enhance_image", "grayscale_image", "rotate_image", "flip_image",
          "resize_image", "crop_square", "convert_image"}


def plan(query):
    """Which tools would act() fire for this command, and with what? Nothing runs: every tool is
    swapped for a recorder while the router looks at the sentence, the way eval/actions.py does."""
    calls, names = [], [n for n in TOOLS if n in globals()]
    saved = {n: globals()[n] for n in names}
    try:
        for n in names:
            globals()[n] = lambda *a, _n=n, **k: calls.append((_n, tuple(str(x) for x in a))) or "ok"
        act(query)
    finally:
        globals().update(saved)
    return calls


def do(query, log=None, confirm=None):
    """The one entry point. The regex router first: instant, exact, and it has
    never fired the wrong tool. What it does not recognise goes to her own
    head, which understands phrasings nobody wrote a rule for. Multi-step work
    goes to agent(). Anything else is not a command: None."""
    if confirm or log:
        for name, args in plan(query):
            if log:
                log(f"  [{name}({', '.join(args)})]")
            if confirm and name in WRITES and not confirm(name, args):
                return "Okay, I will not."
    done = act(query)
    if done:
        return done
    if _MULTISTEP.search(_bare(query)):
        return agent(query, log=log, confirm=confirm)
    picked = pick(query)
    if picked and picked[0] != "agent":
        if log:
            log(f"  [{picked[0]}({picked[1]})]")
        if confirm and picked[0] in WRITES and not confirm(picked[0], (picked[1],)):
            return "Okay, I will not."
        fn = TOOLS[picked[0]]
        return fn(picked[1]) if fn.__code__.co_argcount else fn()
    return agent(query, log=log, confirm=confirm) if picked or is_action(query) else None


def demo():
    """Self-check for the router, the tools and the guard, with every subprocess mocked."""
    global _run
    calls, real = [], _run
    _run = lambda argv, timeout=10: calls.append(argv) or ""
    try:
        assert act("open chrome") == "Opened Google Chrome."
        assert act("go to hacker news").startswith("Opened https://news.ycombinator.com")
        assert act("open chrome and go to github.com") == "Opened https://github.com in Chrome."
        assert act("search for mlx lora").startswith("Searching")
        assert "No app" in act("open definitelynotanapp")
        assert act("open chrome and poke around hacker news") is None  # multi-step, agent's job
        assert act("what is turing") is None and not is_action("what is turing")
        assert is_action("poke around hacker news")
        for pal in PALETTES:
            for motif in ("ring", "spark", "underline", "dot"):
                assert _logo_layers("t", pal, motif)[0]["type"] == "rounded_rectangle"
        big = _complex_layers("t", "ember", 5, 36, "bars", 16, 12)
        assert len(big) == 1 + 36 + 5 + 16 + 3 and all(0 <= l.get("rotation", 0) < 360 for l in big)
        assert not any(l["type"] == "text" for l in _bloom_layers("ember", 89, "square", 3)) and len(_bloom_layers("paper", 144, "circle", 2)) == 145
        assert _WANTS_WORDLESS.search("a wordless logo for turing") and not _WANTS_WORDLESS.search("a logo for a surf school")
        assert _named_page("poke around hacker news and tell me") == "https://news.ycombinator.com"
        assert _named_page("read github.com/nulljosh/turing.") == "https://github.com/nulljosh/turing"
        assert _named_page("open pixelmator then tell me my battery") is None
        assert not is_action("Summarize what Turing is in one sentence.")  # real eval prompt, was hijacked
        assert act("volume 30") == "Volume at 30." and act("set the volume to 250") == "Volume at 100."
        assert "don't read hidden" in read_file("~/.ssh/id_rsa") or "No file" in read_file("~/.ssh/id_rsa")
        assert "No file" in read_file("/etc/passwd") and "No folder" in list_dir("~/../..")
        assert act("play some music") == "Playing." and act("skip this song") == "Skipped." and act("pause") == "Paused."
        assert [duration(x) for x in ("5", "90 seconds", "an hour", "half an hour", "ten minutes", "2 hrs", "soon")] == [5, 1.5, 60, 30, 10, 120, None]
        assert act("set a timer for 0 minutes").startswith("A timer runs") and act("what's playing") == "Nothing is playing."
        assert act("remind me to call mom") == "I'll remind you: call mom" and act("take a note buy milk") == "Noted: buy milk"
        assert act("what's on my calendar today") == "Nothing on the calendar today."
        assert act("what is the weather system") is None and act("play chess with me") is None  # questions, not commands
        if not HEADLESS:  # headless never reaches osascript at all
            note = [a for a in calls if a[-1] == "buy milk"][0]
            assert "buy milk" not in note[2]  # her words ride in argv, never inside the script
        assert _sound("set_volume", "40", "crank it to 40") and not _sound("set_volume", "90", "crank it to 40")
        assert _sound("new_note", "buy milk", "jot down buy milk") and not _sound("new_note", "sell the car", "jot down buy milk")
        assert not _sound("timer", "soon", "time me soon") and not _sound("rm_rf", "", "anything")
        assert all(a[0] in ("open", "osascript", "screencapture", "pbpaste", "pmset") for a in calls)
    finally:
        _run = real
    tools_util.demo()
    assert NOT_FOR_MODELS <= set(TOOLS) and "run_shortcut" in NOT_FOR_MODELS  # side-effect tools never reach the model's menu
    print("tools ok")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        print(do(" ".join(sys.argv[1:]), log=print) or "Not an action.")
    else:
        demo()
