"""Does the landing page's router agree with tools.py?

web/samantha.js is a hand port of tools._ROUTES. A port drifts. This runs every
eval/actions.py case through the JavaScript router under node and fails the
moment the two disagree on which tool fires or what it is handed.

Run: python3 eval/web_parity.py
"""
import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "eval"))
from actions import CASES

JS = """
require(process.argv[1]);
const cases = JSON.parse(process.argv[2]);
console.log(JSON.stringify(cases.map(c => globalThis.Samantha.route(c))));
"""


def main():
    out = subprocess.run(["node", "-e", JS, os.path.join(REPO, "web", "samantha.js"), json.dumps([c[0] for c in CASES])],
                         capture_output=True, text=True, timeout=30)
    if out.returncode:
        sys.exit(out.stderr)
    bad = 0
    for (cmd, tool, arg), got in zip(CASES, json.loads(out.stdout)):
        got_tool = (got or {}).get("tool")
        ok = got_tool == tool and (arg or "").lower() in str((got or {}).get("arg", "")).lower()
        if not ok:
            bad += 1
            print(f"  DIFF {cmd!r}: tools.py {tool}({arg!r}), samantha.js {got}")
    print(f"{len(CASES) - bad}/{len(CASES)} agree")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
