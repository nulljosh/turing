"""Samantha's dev family: git status, recent commits, running the repo's own tests, open pull requests, and
opening a repo in the editor. Every repo is found by folder name (case-insensitive) under ~/Documents/Code;
no name means this repo, turing. A name that does not match a folder there is refused, and nothing here ever
looks outside ~/Documents/Code. git and gh are run with a fixed argv, never a string a model wrote.
"""
import glob
import json
import os
import re
import shutil
import subprocess

from tools_apps import HEADLESS

_I = re.I
CODE_DIR = os.path.realpath(os.path.expanduser("~/Documents/Code"))
_THIS_REPO = os.path.realpath(os.path.dirname(os.path.abspath(__file__)))


def _repo(name=""):
    """Resolve a repo name to its real path under ~/Documents/Code, matched case-insensitively by folder name.
    Blank is this repo, turing. Returns (path, None) or (None, an honest sentence)."""
    name = (name or "").strip().strip("'\"")
    if not name:
        return _THIS_REPO, None
    try:
        entries = os.listdir(CODE_DIR)
    except OSError:
        entries = []
    match = next((e for e in entries if e.lower() == name.lower()), None) or \
        next((e for e in entries if name.lower() in e.lower()), None)
    if not match:
        return None, f"No repo called {name!r} under ~/Documents/Code."
    path = os.path.realpath(os.path.join(CODE_DIR, match))
    rel = os.path.relpath(path, CODE_DIR)
    if rel.startswith("..") or os.sep in rel or not os.path.isdir(os.path.join(path, ".git")):
        return None, f"{match} is not a git repo under ~/Documents/Code I can work with."
    return path, None


def _shell(argv, cwd, timeout=20):
    """Run one fixed argv in cwd and return its stdout, "" if it fails. Never a string a model wrote."""
    try:
        r = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return ""
    return (r.stdout or "").strip()


# ---------- git status, recent commits: read only ----------

def git_status(repo=""):
    """Branch, ahead/behind, and a short list of changed files for a repo under ~/Documents/Code (`git status
    -sb`, capped at 15 lines). Read only."""
    path, err = _repo(repo)
    if err:
        return err
    out = _shell(["git", "status", "-sb"], path)
    if not out:
        return f"Could not read git status for {os.path.basename(path)}."
    return "\n".join(out.splitlines()[:15])


def recent_commits(repo=""):
    """The last 5 commits, one line each with a relative date (`git log -5 --format='%h %s (%cr)'`). Read
    only."""
    path, err = _repo(repo)
    if err:
        return err
    out = _shell(["git", "log", "-5", "--format=%h %s (%cr)"], path)
    return out if out else f"No commits found for {os.path.basename(path)}."


# ---------- run the repo's own tests: a write, it runs code ----------

def _npm_has_test(path):
    """True when package.json declares a real "test" script."""
    pkg = os.path.join(path, "package.json")
    if not os.path.isfile(pkg):
        return False
    try:
        with open(pkg) as f:
            data = json.load(f)
    except (OSError, ValueError):
        return False
    return bool((data.get("scripts") or {}).get("test"))


def _pytest_importable():
    """True when `python3 -c "import pytest"` succeeds."""
    try:
        r = subprocess.run(["python3", "-c", "import pytest"], capture_output=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return False
    return r.returncode == 0


def _run_timed(cmd, cwd, timeout):
    """One command's (returncode, combined stdout+stderr), honest on a timeout or a launch failure."""
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout or "") + (("\n" + r.stderr) if r.stderr else "")
    except subprocess.TimeoutExpired:
        return 1, f"Timed out after {timeout}s."
    except (OSError, subprocess.SubprocessError) as e:
        return 1, str(e)


def run_tests(repo=""):
    """Run the repo's own test command, in order: `npm test` if package.json has one, `python3 -m pytest -q`
    if a tests/ folder of test_*.py exists and pytest is importable, else each tests/test_*.py with python3,
    else `swift test` if there is a Package.swift, else an honest sentence that there is no test command.
    300s timeout, pass/fail and the last 15 lines. Asks first."""
    path, err = _repo(repo)
    if err:
        return err
    name = os.path.basename(path)
    test_files = sorted(glob.glob(os.path.join(path, "tests", "test_*.py")))
    if _npm_has_test(path):
        rc, out = _run_timed(["npm", "test"], path, 300)
        tail = out.splitlines()
    elif test_files and _pytest_importable():
        rc, out = _run_timed(["python3", "-m", "pytest", "-q"], path, 300)
        tail = out.splitlines()
    elif test_files:
        rc, tail = 0, []
        for f in test_files:
            frc, fout = _run_timed(["python3", f], path, 300)
            tail.extend(fout.splitlines())
            rc = rc or frc
    elif os.path.isfile(os.path.join(path, "Package.swift")):
        rc, out = _run_timed(["swift", "test"], path, 300)
        tail = out.splitlines()
    else:
        return f"{name} has no test command I know: no npm test script, no tests/test_*.py, no Package.swift."
    status = "passed" if rc == 0 else "failed"
    return f"Tests {status} for {name}.\n" + "\n".join(tail[-15:])


# ---------- open pull requests: read only ----------

def open_prs(repo=""):
    """`gh pr list --limit 10` for a repo under ~/Documents/Code. Read only. Says plainly when gh is missing
    or not logged in."""
    path, err = _repo(repo)
    if err:
        return err
    if not shutil.which("gh"):
        return "The gh CLI is not installed, so I cannot list pull requests."
    try:
        r = subprocess.run(["gh", "pr", "list", "--limit", "10"], cwd=path, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return "Could not run gh."
    if r.returncode != 0:
        stderr = (r.stderr or "").strip()
        if re.search(r"auth login|not logged|authentication", stderr, _I):
            return "gh is not logged in. Run `gh auth login` first."
        return f"Could not list pull requests: {stderr or 'gh failed.'}"
    out = (r.stdout or "").strip()
    return out if out else f"No open pull requests for {os.path.basename(path)}."


# ---------- open in editor: classified like open_app, not a write ----------

def open_in_editor(repo=""):
    """Open a repo folder under ~/Documents/Code in the editor: `code` if it is on PATH, else Visual Studio
    Code via `open -a` if it is installed, else Finder. Classified like open_app: not a write, and it does
    nothing while headless."""
    path, err = _repo(repo)
    if err:
        return err
    name = os.path.basename(path)
    if shutil.which("code"):
        cmd = ["code", path]
    elif os.path.isdir("/Applications/Visual Studio Code.app"):
        cmd = ["open", "-a", "Visual Studio Code", path]
    else:
        cmd = ["open", path]
    if not HEADLESS:
        try:
            subprocess.run(cmd, timeout=10)
        except (OSError, subprocess.SubprocessError):
            pass
    return f"Opened {name} in the editor."


TOOLS = (git_status, recent_commits, run_tests, open_prs, open_in_editor)

# (pattern, tool name, what to hand it), same shape as tools_organizer.ROUTES and tools_system.ROUTES. tools.py
# splices these in ahead of the base router, alongside organizer's and system's: "run the tests" and "open prs"
# would otherwise fall through to nothing, or agent().
ROUTES = (
    (re.compile(r"^git status$", _I), "git_status", lambda m: ""),
    (re.compile(r"^git status (?:of|for) (.+)$", _I), "git_status", lambda m: m.group(1)),
    (re.compile(r"^what(?:'s| is) changed in (.+?)\??$|^what changed in (.+?)\??$", _I),
     "git_status", lambda m: m.group(1) or m.group(2)),

    (re.compile(r"^recent commits$|^last commits$", _I), "recent_commits", lambda m: ""),
    (re.compile(r"^recent commits (?:in|for|of) (.+)$|^last commits (?:in|for|of) (.+)$", _I),
     "recent_commits", lambda m: m.group(1) or m.group(2)),

    (re.compile(r"^run (?:the )?tests$", _I), "run_tests", lambda m: ""),
    (re.compile(r"^run (.+?)'s tests$", _I), "run_tests", lambda m: m.group(1)),
    (re.compile(r"^run (.+?) tests$", _I), "run_tests", lambda m: m.group(1)),

    (re.compile(r"^open prs$|^open pull requests$", _I), "open_prs", lambda m: ""),
    (re.compile(r"^(?:any )?open (?:pull requests|prs) (?:on|for|in) (.+?)\??$", _I),
     "open_prs", lambda m: m.group(1)),

    (re.compile(r"^open (?:the )?(.+?)(?: repo)? in (?:the editor|vs ?code)$", _I),
     "open_in_editor", lambda m: m.group(1)),
)


def demo():
    """Self-check: pure parsing and routing, no git, gh or subprocess needed."""
    for pat, name, arg in ROUTES:
        assert name in {f.__name__ for f in TOOLS}
    assert all(f.__doc__ for f in TOOLS)
    p, err = _repo("nonexistent-repo-xyz")
    assert p is None and err
    print("tools_dev ok")


if __name__ == "__main__":
    demo()
