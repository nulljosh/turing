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
        # ponytail: Spotlight lags a few seconds on a brand new file (dogfooded: "find b.txt" missed one made a moment
        # earlier), so walk the usual folders, three levels deep, before saying no. Full-disk walk if that ever misses.
        for top in ("Desktop", "Documents", "Downloads", "Pictures", "Movies", "Music"):
            root = os.path.join(HOME, top)
            for cur, dirs, files in os.walk(root):
                dirs[:] = [d for d in dirs if not d.startswith(".") and d != "node_modules" and cur.count(os.sep) - root.count(os.sep) < 2]
                hits += [os.path.join(cur, f) for f in files if f.lower() == name.lower()]
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


HEADLESS = os.environ.get("SAMANTHA_HEADLESS") == "1"


def _pair(request):
    """(source, destination) from 'src<TAB>dst', each a real path inside home, or (None, why)."""
    src, _, dst = request.partition("\t")
    full = _home(src) if src.strip() else None
    if not full or not os.path.exists(full):
        return None, f"No file or folder {src.strip()} I am allowed to touch."
    target = _home(dst) if dst.strip() else None
    if not target:
        return None, f"I can only put things inside your home folder, not {dst.strip() or 'nowhere'}."
    return (full, target), None


def _short(path):
    """~/Desktop/x.txt for a path under home."""
    return path.replace(HOME, "~", 1)


def move_file(request):
    """Move a file or folder somewhere inside the home folder. Takes 'source<TAB>destination'; a folder destination keeps the name. Asks first."""
    pair, why = _pair(request)
    if why:
        return why
    src, dst = pair
    if os.path.isdir(dst):
        dst = os.path.join(dst, os.path.basename(src))
    if os.path.exists(dst):
        return f"{_short(dst)} is already there. Say where else, or rename it first."
    if not HEADLESS:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.move(src, dst)
    return f"Moved {_short(src)} to {_short(dst)}."


def copy_file(request):
    """Copy a file or folder somewhere inside the home folder. Takes 'source<TAB>destination'. Asks first."""
    pair, why = _pair(request)
    if why:
        return why
    src, dst = pair
    if os.path.isdir(dst):
        dst = os.path.join(dst, os.path.basename(src))
    if os.path.exists(dst):
        return f"{_short(dst)} is already there."
    if not HEADLESS:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        (shutil.copytree if os.path.isdir(src) else shutil.copy2)(src, dst)
    return f"Copied {_short(src)} to {_short(dst)}."


def rename_file(request):
    """Rename a file or folder in place. Takes 'path<TAB>new name' (a name, not a path). Asks first."""
    src, _, name = request.partition("\t")
    name = name.strip().strip("'\"")
    if not name or os.sep in name or name.startswith("."):
        return f"{name or 'That'} is not a name I can use: one word or phrase, no slashes, not hidden."
    pair, why = _pair(src + "\t" + os.path.join(os.path.dirname(os.path.expanduser(src.strip())), name))
    if why:
        return why
    old, new = pair
    if os.path.exists(new):
        return f"There is already a {name} there."
    if not HEADLESS:
        os.rename(old, new)
    return f"Renamed {_short(old)} to {name}."


def zip_file(path):
    """Zip a file or folder into a .zip next to it, inside the home folder. Asks first."""
    full = _home(path)
    if not full or not os.path.exists(full):
        return f"No file or folder {path.strip()} I am allowed to touch."
    out = full.rstrip(os.sep) + ".zip"
    if os.path.exists(out):
        return f"{_short(out)} already exists."
    if not HEADLESS:
        if os.path.isdir(full):
            shutil.make_archive(full.rstrip(os.sep), "zip", os.path.dirname(full), os.path.basename(full.rstrip(os.sep)))
        else:
            import zipfile
            with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
                z.write(full, os.path.basename(full))
    return f"Zipped to {_short(out)}."


def unzip_file(path):
    """Unzip a .zip inside the home folder into a folder of the same name next to it. Asks first."""
    full = _home(path)
    if not full or not os.path.isfile(full) or not full.lower().endswith(".zip"):
        return f"No zip file {path.strip()} I am allowed to open."
    out = full[:-4]
    if os.path.exists(out):
        return f"{_short(out)} already exists."
    if not HEADLESS:
        shutil.unpack_archive(full, out, "zip")
    return f"Unzipped to {_short(out)}."


def trash_file(path):
    """Move a file or folder to the Trash (recoverable, never a hard delete), inside the home folder. Asks first."""
    full = _home(path)
    if not full or not os.path.exists(full):
        return f"No file or folder {path.strip()} I am allowed to touch."
    if full == HOME:
        return "Not your whole home folder."
    if not HEADLESS:
        script = 'on run argv\ntell application "Finder" to delete (POSIX file (item 1 of argv) as alias)\nend run'
        subprocess.run(["osascript", "-e", script, full], capture_output=True, text=True, timeout=30)
    return f"Moved {_short(full)} to the Trash."


TOOLS = (find_file, recent_downloads, folder_size, move_file, copy_file, rename_file, zip_file, unzip_file, trash_file)

_I = re.I
# (pattern, tool name, what to hand it), same shape as tools_util.ROUTES. A file name is one word with an extension,
# so "find milk in document ~/a.pdf" and "find milk on my screen" stay with the document and screen tools.
ROUTES = (
    (re.compile(r"^(?:find|locate|where(?:'s| is)|search for)(?: the| my| a)?(?: file)?(?: called| named)? (\S+\.\w{1,5})$", _I), "find_file", lambda m: m.group(1)),
    (re.compile(r"^(?:what(?:'s| is) in |show(?: me)? |list )?(?:my )?(?:recent |latest |newest )?downloads$|^what did i (?:just )?download$", _I), "recent_downloads", lambda m: "5"),
    (re.compile(r"^(?:how big is|(?:what(?:'s| is) the )?size of|folder size (?:of|for)) (?:the |my )?(?:folder )?(\S+)$", _I), "folder_size", lambda m: m.group(1)),
    # the write half: every path is one word (~/Desktop/x.txt), so a sentence with spaces never becomes a file op
    (re.compile(r"^move (?:the )?(?:file |folder )?(\S+) (?:to|into) (?:the )?(?:folder )?(\S+)$", _I), "move_file", lambda m: m.group(1) + "\t" + m.group(2)),
    (re.compile(r"^copy (?:the )?(?:file |folder )?(\S+) (?:to|into) (?:the )?(?:folder )?(\S+)$", _I), "copy_file", lambda m: m.group(1) + "\t" + m.group(2)),
    (re.compile(r"^rename (?:the )?(?:file |folder )?(\S+) (?:to|as) (\S+)$", _I), "rename_file", lambda m: m.group(1) + "\t" + m.group(2)),
    (re.compile(r"^(?:zip|compress|archive) (?:the )?(?:file |folder )?(\S+)$", _I), "zip_file", lambda m: m.group(1)),
    (re.compile(r"^(?:unzip|extract|unarchive) (?:the )?(?:file |zip )?(\S+)$", _I), "unzip_file", lambda m: m.group(1)),
    (re.compile(r"^(?:trash|delete|remove|throw away|throw out) (?:the )?(?:file |folder )?(\S+)$", _I), "trash_file", lambda m: m.group(1)),
)


def demo():
    """Self-check: the pure parts, no Spotlight needed."""
    assert _size(12) == "12 bytes" and _size(2048) == "2.0 KB" and _size(3 * 1024 ** 3) == "3.0 GB"
    assert _home("~/.ssh/id_rsa") is None and _home("/etc/passwd") is None and _home("~/Documents") is not None
    assert "No folder" in folder_size("~/.ssh") and "No folder" in folder_size("/etc")
    for bad in ("~/.ssh/id_rsa\t~/Desktop", "/etc/passwd\t~/Desktop", "~/../../etc/passwd\t~/Desktop"):
        assert "allowed" in move_file(bad) and "allowed" in copy_file(bad), bad
    assert "inside your home" in move_file(os.path.expanduser("~") + "\t/tmp") and "Not your whole" in trash_file("~")
    assert "not a name" in rename_file("~/Desktop\t../evil") and "not a name" in rename_file("~/Desktop\t.hidden")
    assert "No zip" in unzip_file("~/Desktop") and "allowed" in trash_file("~/.ssh")
    assert all(f.__doc__ for f in TOOLS)
    print("tools_files ok")


if __name__ == "__main__":
    demo()
