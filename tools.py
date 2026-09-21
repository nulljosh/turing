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
import subprocess
import sys
import urllib.parse
import urllib.request

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
    if HEADLESS and argv[0] in _VISIBLE:
        return ""
    r = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    return (r.stdout or r.stderr).strip()


def installed_apps():
    apps = {}
    for d in APP_DIRS:
        if os.path.isdir(d):
            for f in os.listdir(d):
                if f.endswith(".app"):
                    apps[f[:-4].lower()] = f[:-4]
    return apps


def _app_match(name):
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
    """Set the Mac's output volume, 0 to 100."""
    n = max(0, min(100, int(float(level))))
    _run(["osascript", "-e", f"set volume output volume {n}"])
    return f"Volume at {n}."


def current_volume():
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


HOME = os.path.realpath(os.path.expanduser("~"))


def _inside_home(path):
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


PXM = os.path.expanduser("~/Documents/Code/pixelmator-skill/pxm.py")
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
    tile, ink, accent = PALETTES[palette]
    C = 512

    def polar(r, deg):  # clock angle, 0 at the top, screen y grows downward
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


def make_logo(description):
    """Design a logo and build it live in Pixelmator Pro. Takes a short description of what the logo is for. Say 'complex' for an intricate one."""
    fancy = bool(_WANTS_COMPLEX.search(description))
    prompt = ("Pick a logo for this. letters: its one or two initials. palette: ember (warm amber on dark), ink (white and gold on "
              "near-black), forest (green on dark), signal (red on dark), paper (dark on cream). ")
    prompt += ("This one should be intricate, so be bold with the numbers. rings: concentric rings. rays: marks around the rim. "
               "ray_style: bars, dots or stars. orbit_dots: dots circling inside. star_points: points on the centre burst. "
               if fancy else "motif: ring, spark, underline or dot. ") + "Logo for: " + description
    body = json.dumps({"model": AGENT_MODEL, "stream": False, "think": False, "format": _COMPLEX_SCHEMA if fancy else _LOGO_SCHEMA,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    try:
        with urllib.request.urlopen(urllib.request.Request(OLLAMA_CHAT, body, {"Content-Type": "application/json"}), timeout=180) as r:
            pick = json.loads(json.load(r)["message"]["content"])
        spec = {"layers": _complex_layers(**pick) if fancy else _logo_layers(pick["letters"], pick["palette"], pick["motif"])}
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

TOOLS = {f.__name__: f for f in (open_app, open_url, web_search, current_tab, read_page, screenshot,
                                     clipboard, set_volume, battery, say, list_dir, read_file, make_logo)}

_ROUTES = (
    (re.compile(r"^(?:make|design|draw|create|build)(?: me)? (?:a |an )?(?:logo|icon)(?: for| of)? (.+)$", re.I), lambda m: make_logo(m.group(1))),
    (re.compile(r"^(?:(?:show me |tell me )?what(?:'s| is) (?:on|in) (?:my |the )?clipboard|(?:read|show)(?: me)? (?:my |the )?clipboard)\b", re.I), lambda m: clipboard()),
    (re.compile(r"^(?:set |turn |put )?(?:the |it |my )?(?:volume )?(?:up |down )?(?:to |at )(\d{1,3})\b", re.I), lambda m: set_volume(m.group(1))),
    (re.compile(r"^(?:set |turn )?(?:the )?volume (\d{1,3})\b", re.I), lambda m: set_volume(m.group(1))),
    (re.compile(r"^(?:turn )?(?:the |it )?(?:volume )?(up|down)$|^(?:turn )?(?:the )?volume (up|down)$|^(louder|quieter)$", re.I),
     lambda m: set_volume(current_volume() + (15 if (m.group(1) or m.group(2) or m.group(3)).lower() in ("up", "louder") else -15))),
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
# anything past the first verb phrase means more than one step: that is agent() work
_MULTISTEP = re.compile(r"\b(?:and (?:then )?(?:tell|read|find|summar|poke|look|check|see|click)|poke around|then )", re.I)
_ACTION = re.compile(r"^(?:open|launch|start|go to|visit|browse|pull up|search|google|look up|poke around|take a|grab a|screenshot|make|design|draw)\b", re.I)


# People do not type commands, they ask. "can you open chrome", "hey open
# github", "open up spotify for me please". Stripped once here so every route
# and is_action() see the bare command, instead of each regex growing its own
# politeness prefix. Live-tested 2026-09-20: 10 of 16 natural phrasings missed.
_LEAD = re.compile(r"^(?:(?:hey|ok|okay|yo|samantha|please|now|just)[, ]+)*"
                   r"(?:(?:can|could|would|will) you (?:please )?|i (?:want|need|would like|'d like) (?:you )?to |let's |go ahead and )?(?:please )?", re.I)
_TAIL = re.compile(r"(?:[, ]+(?:please|for me|real quick|now|thanks|thank you))+$", re.I)


def _bare(query):
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
    return bool(_ACTION.match(_bare(query)))


def _schema(fn):
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


def agent(task, max_steps=6, log=None):
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
                           "tools": [_schema(f) for f in TOOLS.values()]}).encode()
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
            fn = TOOLS.get(name)
            try:
                if fn:
                    takes = fn.__code__.co_varnames[:fn.__code__.co_argcount]
                    args = {k: v for k, v in args.items() if k in takes}
                result = fn(**args) if fn else f"No tool named {name}."
            except Exception as e:
                result = f"{name} failed: {e}"
            if log:
                log(f"  [{name}({', '.join(map(str, args.values()))})]")
            messages.append({"role": "tool", "tool_name": name, "content": str(result)})
    return "I ran out of steps before finishing that."


def do(query, log=None):
    """The one entry point: exact route first, agent if it's action-shaped, else None."""
    return act(query) or (agent(query, log=log) if is_action(query) else None)


def demo():
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
        assert _named_page("poke around hacker news and tell me") == "https://news.ycombinator.com"
        assert _named_page("read github.com/nulljosh/turing.") == "https://github.com/nulljosh/turing"
        assert _named_page("open pixelmator then tell me my battery") is None
        assert not is_action("Summarize what Turing is in one sentence.")  # real eval prompt, was hijacked
        assert act("volume 30") == "Volume at 30." and act("set the volume to 250") == "Volume at 100."
        assert "don't read hidden" in read_file("~/.ssh/id_rsa") or "No file" in read_file("~/.ssh/id_rsa")
        assert "No file" in read_file("/etc/passwd") and "No folder" in list_dir("~/../..")
        assert all(a[0] in ("open", "osascript", "screencapture", "pbpaste", "pmset") for a in calls)
    finally:
        _run = real
    print("tools ok")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        print(do(" ".join(sys.argv[1:]), log=print) or "Not an action.")
    else:
        demo()
