"""Samantha's file tools, read only: find a file by name (Spotlight), the newest downloads, how big a folder is.
Everything stays inside the home folder and skips hidden files, same rule as read_document. The write half of the
family (move, rename, zip, trash) is not here yet; each of those asks first when it lands.
"""
import os
import re
import shutil
import subprocess
import time

HOME = os.path.realpath(os.path.expanduser("~"))


def _home(path):
    """The real path of something inside the home folder, or None: outside it or hidden."""
    full = os.path.realpath(os.path.expanduser(path.strip().strip("'\"") or "~"))
    rel = os.path.relpath(full, HOME)
    if rel.startswith("..") or any(p.startswith(".") for p in rel.split(os.sep) if p != "."):
        return None
    return full


def _size(n):
    """1.2 MB, 340 KB, 12 bytes."""
    for unit in ("bytes", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.1f} {unit}" if unit != "bytes" else f"{int(n)} bytes"
        n /= 1024


def find_file(name):
    """Find files in the home folder by name, with Spotlight. Up to ten, newest first; hidden folders are skipped."""
    name = name.strip().strip("'\"")
    if not name:
        return "Find what? Give me a file name, like report.pdf."
    if not shutil.which("mdfind"):
        return "Spotlight is not on this machine, so I cannot search for files here."
    try:
        out = subprocess.run(["mdfind", "-onlyin", HOME, "-name", name], capture_output=True, text=True, timeout=15).stdout
    except (OSError, subprocess.SubprocessError):
        return "Spotlight did not answer."
    # dependency copies and app support files are never the one you meant
    noise = re.compile(r"/(?:node_modules|Library|\.venv|venv|site-packages)/")
    hits = [p for p in out.splitlines() if _home(p) and os.path.isfile(p) and not noise.search(p)]
    if not hits:
        return f"No file named {name} in your home folder."
    hits.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    shown = "\n".join(p.replace(HOME, "~", 1) for p in hits[:10])
    return shown + (f"\n...and {len(hits) - 10} more." if len(hits) > 10 else "")


def recent_downloads(count="5"):
    """The newest files in your Downloads folder, with size and age."""
    n = int(count) if str(count).strip().isdigit() else 5
    folder = os.path.join(HOME, "Downloads")
    if not os.path.isdir(folder):
        return "There is no Downloads folder here."
    files = [os.path.join(folder, f) for f in os.listdir(folder) if not f.startswith(".")]
    files = [f for f in files if os.path.isfile(f)]
    if not files:
        return "Downloads is empty."
    files.sort(key=os.path.getmtime, reverse=True)
    lines = []
    for f in files[:max(1, min(n, 20))]:
        age = time.time() - os.path.getmtime(f)
        when = "just now" if age < 3600 else (f"{int(age // 3600)} h ago" if age < 86400 else f"{int(age // 86400)} d ago")
        lines.append(f"{os.path.basename(f)}, {_size(os.path.getsize(f))}, {when}")
    return "\n".join(lines)


def folder_size(path):
    """How big a folder inside the home folder is, counting every file in it."""
    full = _home(path)
    if not full or not os.path.isdir(full):
        return f"No folder {path.strip()} I am allowed to read."
    total = 0
    for root, dirs, files in os.walk(full):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return f"{full.replace(HOME, '~', 1)} is {_size(total)}."


TOOLS = (find_file, recent_downloads, folder_size)

_I = re.I
# (pattern, tool name, what to hand it), same shape as tools_util.ROUTES. A file name is one word with an extension,
# so "find milk in document ~/a.pdf" and "find milk on my screen" stay with the document and screen tools.
ROUTES = (
    (re.compile(r"^(?:find|locate|where(?:'s| is)|search for)(?: the| my| a)?(?: file)?(?: called| named)? (\S+\.\w{1,5})$", _I), "find_file", lambda m: m.group(1)),
    (re.compile(r"^(?:what(?:'s| is) in |show(?: me)? |list )?(?:my )?(?:recent |latest |newest )?downloads$|^what did i (?:just )?download$", _I), "recent_downloads", lambda m: "5"),
    (re.compile(r"^(?:how big is|(?:what(?:'s| is) the )?size of|folder size (?:of|for)) (?:the |my )?(?:folder )?(\S+)$", _I), "folder_size", lambda m: m.group(1)),
)


def demo():
    """Self-check: the pure parts, no Spotlight needed."""
    assert _size(12) == "12 bytes" and _size(2048) == "2.0 KB" and _size(3 * 1024 ** 3) == "3.0 GB"
    assert _home("~/.ssh/id_rsa") is None and _home("/etc/passwd") is None and _home("~/Documents") is not None
    assert "No folder" in folder_size("~/.ssh") and "No folder" in folder_size("/etc")
    assert all(f.__doc__ for f in TOOLS)
    print("tools_files ok")


if __name__ == "__main__":
    demo()
