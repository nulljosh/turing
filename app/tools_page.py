"""Samantha's page check. check_page opens an HTML file inside the home folder in headless Chrome and says what is wrong
with it in one plain paragraph: the errors the page threw, and whether the picture is black, blown out, too dark, or
one flat colour with nothing in view. Read only: it writes nothing but a throwaway profile and one screenshot in a
temp folder it deletes. The network is switched off for the run (every address except localhost fails to resolve), so a
page that pulls a script from a CDN is told so and nothing leaves this Mac. The picture check is her self-fix loop's
eyes from the room benchmark (pure pixel counts, no model), kept as a tool of its own. tests/test_page.py mocks
subprocess, so no real Chrome run happens there.
"""
import os
import re
import shutil
import statistics
import subprocess
import tempfile

import tools_files

HOME = tools_files.HOME
_home = tools_files._home

_CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
_NO_CHROME = "Chrome is not installed here, so I cannot open a page."
_FORMATS = (".html", ".htm")
_FLAGS = ["--headless=new", "--hide-scrollbars", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist",
          "--window-size=1000,640", "--enable-logging=stderr", "--v=0", "--virtual-time-budget=4000",
          "--host-resolver-rules=MAP * ~NOTFOUND , EXCLUDE localhost"]
_CONSOLE = re.compile(r'CONSOLE:\d+\] "(.*)", source: (\S+) \((\d+)\)')
_W, _H = 96, 60


def _chrome():
    """The path to Chrome, or None when this Mac has none."""
    return _CHROME if os.path.exists(_CHROME) else shutil.which("chromium") or shutil.which("google-chrome")


def _errors(log):
    """The page's own errors from Chrome's log: console errors and uncaught exceptions, each once, as 'message (line N)'."""
    seen, out = set(), []
    for msg, _src, line in _CONSOLE.findall(log):
        if not re.search(r"error|uncaught|failed|not defined|cannot|could not", msg, re.I) or msg in seen:
            continue
        seen.add(msg)
        out.append(f"{msg[:140]} (line {line})")
    for url in dict.fromkeys(re.findall(r"Failed to load resource.*?(https?://[^\s\"')]+)|ERR_NAME_NOT_RESOLVED[^\n]*?(https?://[^\s\"')]+)", log)):
        out.append(f"it needs {next(u for u in url if u)} from the network")
    return out


def _look(png):
    """(black share, blown-out share, mean brightness, spread) of a screenshot from a 96x60 grey copy, or None."""
    magick = shutil.which("magick") or shutil.which("convert")
    if not magick:
        return None
    got = subprocess.run([magick, png, "-resize", f"{_W}x{_H}!", "-colorspace", "Gray", "-depth", "8", "gray:-"], capture_output=True, timeout=20)
    px = list(got.stdout)
    if got.returncode or len(px) != _W * _H:
        return None
    return (sum(v < 12 for v in px) / len(px), sum(v > 240 for v in px) / len(px), sum(px) / len(px), statistics.pstdev(px))


def _verdict(errors, look):
    """One paragraph from the errors and the picture numbers: what is wrong, or that it looks fine."""
    notes = []
    if errors:
        notes.append("It threw " + ("an error" if len(errors) == 1 else f"{len(errors)} errors") + ": " + "; ".join(errors[:3]) + ".")
    if look is None:
        notes.append("I could not look at the picture.")
    else:
        black, white, mean, spread = look
        if black > 0.6:
            notes.append(f"The picture is {black:.0%} black: nothing is lit or drawn, or the camera sees nothing.")
        elif white > 0.25:
            notes.append(f"The picture is {white:.0%} blown-out white.")
        elif spread < 8:
            notes.append("The picture is one flat colour with nothing in view.")
        elif mean < 40:
            notes.append(f"The picture is very dark (average brightness {mean:.0f} of 255).")
    return " ".join(notes) if notes else "It loads without errors and the picture has something in view."


def check_page(path):
    """Open an HTML file inside the home folder headless, with the network off, and say what is wrong with it: its errors, and whether the picture is black, blown out, dark or flat. Read only."""
    full = _home(path)
    if not full or not os.path.isfile(full) or not full.lower().endswith(_FORMATS):
        return f"No page {path.strip()} I am allowed to open."
    exe = _chrome()
    if not exe:
        return _NO_CHROME
    with tempfile.TemporaryDirectory() as tmp:
        shot = os.path.join(tmp, "page.png")
        try:
            run = subprocess.run([exe, *_FLAGS, f"--user-data-dir={tmp}/profile", f"--screenshot={shot}", "file://" + full],
                                 capture_output=True, text=True, timeout=60)
        except (OSError, subprocess.TimeoutExpired):
            return f"I could not finish opening {os.path.basename(full)}: Chrome did not answer in a minute."
        errors = _errors(run.stderr or "")
        look = _look(shot) if os.path.exists(shot) else None
    return f"{os.path.basename(full)}: " + _verdict(errors, look)


TOOLS = (check_page,)
_I = re.I
_PAGE = r"(\S+\.html?)"
# (pattern, tool name, what to hand it), same shape as tools_files.ROUTES. Only a path ending in .html or .htm matches,
# so "check my email" and "why is the sky black" stay with the other tools.
ROUTES = (
    (re.compile(r"^(?:check|test|debug|open and check) (?:the |my )?(?:page |site )?" + _PAGE + "$", _I), "check_page", lambda m: m.group(1)),
    (re.compile(r"^why is (?:the |my )?(?:page |site )?" + _PAGE + r" (?:black|blank|empty|broken|dark|not working|not loading)$", _I), "check_page", lambda m: m.group(1)),
)


def demo():
    """Self-check: the routes, the log parser, the verdicts and the refusals, no Chrome run."""
    assert ROUTES[0][0].match("check ~/Sites/index.html") and not ROUTES[0][0].match("check my email")
    assert ROUTES[1][0].match("why is ~/room.html black") and not ROUTES[1][0].match("why is the sky black")
    log = '[1:2:3:INFO:CONSOLE:26] "Uncaught Error: boom", source: file:///a.html (26)\n[1:2:3:INFO:CONSOLE:26] "Uncaught Error: boom", source: file:///a.html (26)'
    assert _errors(log) == ["Uncaught Error: boom (line 26)"]
    assert "black" in _verdict([], (0.9, 0, 3, 5)) and "flat" in _verdict([], (0.1, 0, 120, 2)) and "fine" not in _verdict(["x"], (0, 0, 120, 40))
    assert "loads without errors" in _verdict([], (0.1, 0, 120, 40))
    assert "allowed" in check_page("~/.ssh/a.html") and "allowed" in check_page("/etc/a.html")
    assert all(f.__doc__ for f in TOOLS)
    print("tools_page ok")


if __name__ == "__main__":
    demo()
