"""One line that says how the repo stands, for docs/PROGRESS.md and the loop: tools, tests, docs, laws, the biggest file,
and whether the Python and JavaScript routers agree. Nothing here needs a Mac or the network.

Run: python3 eval/scorecard.py
"""
import glob
import os
import re
import subprocess
import sys

os.environ["SAMANTHA_HEADLESS"] = "1"
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)


def run(*argv):
    """The last line a check prints, from the repo root."""
    out = subprocess.run([sys.executable, *argv], cwd=REPO, capture_output=True, text=True, timeout=600)
    lines = (out.stdout + out.stderr).strip().splitlines()
    return lines[-1] if lines else ""


def biggest():
    """The largest Python file and its line count."""
    sizes = []
    for path in glob.glob(os.path.join(REPO, "*.py")) + glob.glob(os.path.join(REPO, "tests", "*.py")) + glob.glob(os.path.join(REPO, "training", "*.py")) + glob.glob(os.path.join(REPO, "eval", "*.py")) + glob.glob(os.path.join(REPO, "pixelmator", "*.py")):
        with open(path) as f:
            sizes.append((sum(1 for _ in f), os.path.relpath(path, REPO)))
    return max(sizes)


def card():
    """The scorecard as one line."""
    import tools
    tests = sum(len(re.findall(r"^\s+def test_|^def test_", open(p).read(), re.M)) for p in glob.glob(os.path.join(REPO, "tests", "test_*.py")) + glob.glob(os.path.join(REPO, "pixelmator", "test_*.py")))
    with open(os.path.join(REPO, "VERSION")) as f:
        version = f.read().strip()
    lines, name = biggest()
    return " · ".join([f"v{version}", f"{len(tools.TOOLS)} tools", f"{tests} tests", run("stats.py", "--check"),
                       run("eval/laws.py").replace("laws: ", "laws "), f"biggest {name} {lines}",
                       "actions " + run("eval/actions.py").split()[0], "parity " + run("eval/web_parity.py").split()[0],
                       "util_diff " + run("eval/util_diff.py").split()[0]])


if __name__ == "__main__":
    print(card())
