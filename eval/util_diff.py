"""Do tools_util.py and its JavaScript twin in web/samantha.js say the same thing?

Every phrasing below goes through tools.act() and through Samantha.route() plus
Samantha.util[tool](arg) under node. The two must return the exact same words, or
the landing page is showing a tool that does not behave like the real one. Only
tools with a fixed answer are diffed; dice, coins, passwords and uuids are checked
for shape.

Run: python3 eval/util_diff.py
"""
import json
import os
import re
import subprocess
import sys

os.environ["SAMANTHA_HEADLESS"] = "1"
os.environ["SAMANTHA_MEMORY"] = "/nonexistent/samantha-memory.json"  # the diff must not read anyone's real memory
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
import tools

FIXED = [
    "calculate 17*23", "calc 2^10", "compute 15% of 80", "math sqrt(144) + 1", "calculate 1/0", "calculate 10 // 3", "calculate -7 % 3",
    "calculate 2 ** -1", "calculate -2**2", "calculate (1+2)*(3+4)", "calculate 0.1 + 0.2", "calculate pi", "calculate 9**9999", "calculate hello",
    "calculate __import__('os')", "calculate 1,000 * 3", "calculate 3 x 4", "calculate 7 / 2", "calculate 2 +", "calculate ((2)", "calculate abs(-5)",
    "convert 5 km to miles", "convert 212 f to c", "convert 0 c to k", "convert 1 lb to oz", "convert 1 mile to feet", "convert 2 hours to minutes",
    "convert 3 cups to ml", "convert 5 km to kg", "convert nonsense", "convert 100 celsius to fahrenheit", "convert -40 f to c", "convert 1 gallon to liters",
    "sha256 of hello", "hash hello world", "hash: turing",
    "base64 encode hi there", "base64 decode aGkgdGhlcmU=", "base64 decode %%%", "base64 encode café", "base64 decode Y2Fmw6k=",
    "count words in one two three", "word count of hi", "word count: a  b   c",
    "reverse abc", "reverse: hello world", "shout hey there", "uppercase quiet please", "morse sos", "morse code for hello 42",
    "pretty print json {\"a\":[1,2]}", "format json {bad", "prettify json [1, 2, 3]",
    "is 17 prime", "is 91 a prime", "factor 84", "prime factors of 600851475143", "is 1 prime", "factorize 97",
    "roman numerals for 2026", "roman numeral 4", "1999 in roman numerals", "roman numerals for 4000",
    "tip on 45", "what's the tip on 100", "tip for 12.5", "tip on 0",
    "days until 2000-01-01", "days until 2999-12-31", "days until soon", "days until 2026-02-31",
    "recall my dog", "forget zebra", "can you please calculate 6*7 for me", "hey calculate 8 + 8", "please convert 10 km to miles",
]
NOT_COMMANDS = ["what is turing", "calculating machines are cool", "roll call", "hash browns are good", "reverse psychology"]
SHAPES = {"flip a coin": r"(Heads|Tails)\.", "roll 2d6": r"\d+ \+ \d+ = \d+", "roll a die": r"[1-6]", "roll d20": r"\d+",
          "random number between 5 and 9": r"[5-9]", "make me a password": r".{16}", "generate a strong password of 24 characters": r".{24}",
          "make a uuid": r"[0-9a-f-]{36}", "time in tokyo": r"It is \d+:\d\d [AP]M on \w+ in Tokyo\.", "what day is it": r"It is \w+, \w+ \d+, \d{4}\.",
          "days until christmas": r"\d+ days? until December 25, \d{4}\.|That is today\.", "roll 500d6": r"Up to 100 dice.*"}
MAC_ONLY = ["disk space", "uptime", "how much memory do i have", "cpu load", "what is my ip", "what wifi am i on", "system info",
            "copy hello to my clipboard", "lock the screen", "reveal ~/Documents in finder", "list my shortcuts", "run shortcut morning routine", "list my mcp tools", "call mcp samantha calculate {}", "read my screen", "find milk on my screen", "list my tabs", "switch to the github tab", "close the github tab", "read tab 2", "read this tab"]

JS = """
require(process.argv[1]);
const S = globalThis.Samantha, cases = JSON.parse(process.argv[2]);
(async () => {
  const out = [];
  for (const q of cases) {
    const r = S.route(q);
    out.push(r && r.tool && S.util[r.tool] ? {tool: r.tool, text: await S.util[r.tool](r.arg)} : {tool: r && r.tool || null, text: null});
  }
  console.log(JSON.stringify(out));
})();
"""


def js(queries):
    """Run every query through the JS router and its util tool, under node."""
    p = subprocess.run(["node", "-e", JS, os.path.join(REPO, "web", "samantha.js"), json.dumps(queries)], capture_output=True, text=True)
    if p.returncode:
        sys.exit("node failed:\n" + p.stderr[-600:])
    return json.loads(p.stdout)


def main():
    """Diff every phrasing between Python and JavaScript and exit non-zero on any difference."""
    fails = 0
    queries = FIXED + NOT_COMMANDS + list(SHAPES) + MAC_ONLY
    theirs = dict(zip(queries, js(queries)))
    for q in FIXED:
        py, web = tools.act(q), theirs[q]["text"]
        if py != web:
            fails += 1
            print(f"DIFF  {q!r}\n      python: {py!r}\n      js:     {web!r}")
    for q in NOT_COMMANDS:
        if tools.act(q) is not None or theirs[q]["tool"] is not None:
            fails += 1
            print(f"STOLE {q!r}: python {tools.act(q)!r}, js tool {theirs[q]['tool']!r}")
    for q, shape in SHAPES.items():
        for side, text in (("python", tools.act(q)), ("js", theirs[q]["text"])):
            if not re.fullmatch(shape, text or ""):
                fails += 1
                print(f"SHAPE {side} {q!r}: {text!r}")
    for q in MAC_ONLY:
        if not theirs[q]["tool"] or "real Mac" not in (theirs[q]["text"] or ""):
            fails += 1
            print(f"ROUTE js {q!r} -> {theirs[q]}")
        if tools.act(q) is None:
            fails += 1
            print(f"ROUTE python {q!r} -> None")
    total = len(FIXED) + len(NOT_COMMANDS) + len(SHAPES) * 2 + len(MAC_ONLY) * 2
    print(f"{total - fails}/{total} agree")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
