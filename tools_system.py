"""Samantha's system family: dark mode, what's running, quitting an app, and the honest edges around Do Not
Disturb and Bluetooth (no blueutil and no brightness CLI on this Mac, and nothing gets installed to get them).
Every AppleScript rides through tools_apps._app, argv only, never spliced into the script; every shell command
through _shell here, a fixed argv, never a string a model wrote.
"""
import re
import subprocess

from tools_apps import _app, HEADLESS

_I = re.I


# ---------- dark mode ----------

_DARK_SET = ('tell application "System Events"\ntell appearance preferences\nset dark mode to %s\n'
             'return dark mode\nend tell\nend tell')
_DARK_ON = _DARK_SET % "true"
_DARK_OFF = _DARK_SET % "false"
_DARK_TOGGLE = _DARK_SET % "not dark mode"


def dark_mode(arg=""):
    """Turn dark mode on, off, or toggle it, and say which it landed on. Takes "on", "off", "toggle", or free
    text like "switch to light mode"."""
    a = (arg or "").strip().lower()
    if "toggle" in a:
        script = _DARK_TOGGLE
    elif "light" in a or re.search(r"\boff\b", a):
        script = _DARK_OFF
    else:
        script = _DARK_ON
    out = _app(script).strip().lower()
    return f"Dark mode is {'off' if 'false' in out else 'on'}."


# ---------- running apps, quit ----------

_RUNNING_APPS = ('tell application "System Events" to get name of every process '
                  'whose visible is true and background only is false')


def running_apps():
    """Which apps are open and visible right now, names sorted. Read only."""
    names = sorted({n.strip() for n in _app(_RUNNING_APPS).split(",") if n.strip()})
    return ", ".join(names) if names else "No apps running."


_QUIT = '''on run argv
tell application (item 1 of argv) to quit
end run'''

_PROTECTED = {"finder", "terminal", "iterm2", "iterm", "ghostty", "warp", "cmux", "kitty", "alacritty", "wezterm", "claude"}


def quit_app(name):
    """Quit a running app by its exact name. Refuses Finder and the terminal running her (Terminal, iTerm2,
    Ghostty, Warp, cmux and friends), checked on the app it actually matched, so "quit find" never reaches Finder, and refuses an app that is not actually running, checked first. Asks first."""
    want = (name or "").strip().strip("'\"")
    if not want:
        return "Quit which app? Give me a name."
    if want.lower() in _PROTECTED:
        return f"I will not quit {want}. That is Finder or the terminal running me."
    names = [n.strip() for n in _app(_RUNNING_APPS).split(",") if n.strip()]
    match = next((n for n in names if n.lower() == want.lower()), None) or \
        next((n for n in names if want.lower() in n.lower()), None)
    if match and match.lower() in _PROTECTED:
        return f"I will not quit {match or want}. That is Finder or the terminal running me."
    if not match:
        return f"{want} is not running."
    _app(_QUIT, match)
    return f"Quit {match}."


# ---------- do not disturb: honest, no scripting for Focus ----------

def _shell(argv, timeout=15):
    """Run one fixed argv and return its output, "" if it fails or this run is headless. Never a string a model
    wrote."""
    if HEADLESS:
        return ""
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return ""
    return (r.stdout or "").strip()


def do_not_disturb(arg=""):
    """Turn Do Not Disturb on or off, by running a Shortcut named "Turn On Do Not Disturb" / "Turn Off Do Not
    Disturb" if one exists. macOS has no scripting for Focus, so when that Shortcut is missing this says so
    plainly, names the "Set Focus" action, and does nothing else. Asks first."""
    a = (arg or "").strip().lower()
    wanted = "Turn Off Do Not Disturb" if re.search(r"\boff\b", a) else "Turn On Do Not Disturb"
    names = [n.strip() for n in _shell(["shortcuts", "list"]).splitlines() if n.strip()]
    match = next((n for n in names if n.lower() == wanted.lower()), None)
    if not match:
        return (f'I do not see a Shortcut called "{wanted}". Make one in the Shortcuts app with the '
                '"Set Focus" action, and I can run it.')
    _shell(["shortcuts", "run", match], timeout=60)
    return f"Ran {match}."


# ---------- bluetooth: read only, no blueutil on this Mac ----------

def bluetooth_status():
    """Bluetooth on or off, and any connected device names, from system_profiler. Read only: this Mac has no
    blueutil, so turning Bluetooth on or off is not something Samantha can do."""
    out = _shell(["system_profiler", "SPBluetoothDataType"], timeout=15)
    if not out:
        return "Could not read Bluetooth status."
    m = re.search(r"State:\s*(On|Off)", out, _I)
    if not m:
        return "Could not tell if Bluetooth is on."
    if m.group(1).capitalize() == "Off":
        return "Bluetooth is off."
    section = re.search(r"(?<!Not )Connected:\s*\n(.*?)(?:\n\s*Not Connected:|\Z)", out, re.S)
    devices = []
    if section:
        skip = ("address", "services", "vendor", "product", "firmware", "rssi", "connected", "minor type", "manufacturer")
        for line in section.group(1).splitlines():
            t = line.strip().rstrip(":")
            if line.strip().endswith(":") and t and not t.lower().startswith(skip):
                devices.append(t)
    return "Bluetooth is on. " + (f"Connected: {', '.join(devices)}." if devices else "No devices connected.")


TOOLS = (dark_mode, running_apps, quit_app, do_not_disturb, bluetooth_status)

# (pattern, tool name, what to hand it), same shape as tools_organizer.ROUTES. tools.py splices these in AHEAD of
# the base router: "close the app slack" needs the "app" word so it never steals "close the github tab" (close_tab),
# and "what apps are running" needs to land here, not fall through to agent().
_QUIT_RE = re.compile(r"^(?:quit|kill) (.+)$|^close the app (.+)$", _I)

ROUTES = (
    (re.compile(r"^turn on dark mode$|^dark mode on$|^switch to dark mode$", _I), "dark_mode", lambda m: "on"),
    (re.compile(r"^turn off dark mode$|^dark mode off$|^switch to light mode$", _I), "dark_mode", lambda m: "off"),
    (re.compile(r"^toggle dark mode$", _I), "dark_mode", lambda m: "toggle"),
    (re.compile(r"^(?:what apps are running|list open apps|what(?:'s| is) running|show(?: me)? (?:my )?open apps|what apps do i have open)\??$", _I),
     "running_apps", lambda m: ""),
    (_QUIT_RE, "quit_app", lambda m: m.group(1) or m.group(2)),
    (re.compile(r"^turn on (?:do not disturb|dnd|focus)$|^(?:do not disturb|dnd|focus) on$|^enable (?:do not disturb|dnd|focus)$", _I),
     "do_not_disturb", lambda m: "on"),
    (re.compile(r"^turn off (?:do not disturb|dnd|focus)$|^(?:do not disturb|dnd|focus) off$|^disable (?:do not disturb|dnd|focus)$", _I),
     "do_not_disturb", lambda m: "off"),
    (re.compile(r"^(?:is )?bluetooth(?: status| on| enabled)?\??$|^what(?:'s| is) (?:my )?bluetooth (?:status|doing)\??$|^what(?:'s| is) connected (?:via |over )?bluetooth\??$", _I),
     "bluetooth_status", lambda m: ""),
)


def demo():
    """Self-check: pure parsing and routing, no AppleScript or shell needed."""
    for pat, name, arg in ROUTES:
        assert name in {f.__name__ for f in TOOLS}
    assert _QUIT_RE.match("quit spotify").group(1) == "spotify"
    assert _QUIT_RE.match("close the app slack").group(2) == "slack"
    assert all(f.__doc__ for f in TOOLS)
    print("tools_system ok")


if __name__ == "__main__":
    demo()
