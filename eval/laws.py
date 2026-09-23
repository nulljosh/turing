"""The laws in LAWS.md, checked against every tool, not a sample.

Run: python3 eval/laws.py    (exit 1 and the broken law on failure; gate.sh and CI run it)
"""
import glob
import json
import os
import re
import subprocess
import sys
from unittest import mock

os.environ["SAMANTHA_HEADLESS"] = "1"
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
import harness
import tools

# The tools that leave a mark or change the Mac. A new tool that does either must be added to one of tools.WRITES or
# tools.NOT_FOR_MODELS, and this list says which tools count as read-only. Anything not here and not classified fails law 1.
READ_ONLY = {"open_app", "open_url", "web_search", "current_tab", "read_page", "screenshot", "clipboard", "set_volume", "battery", "say",
             "list_dir", "read_file", "music", "weather", "timer", "calendar_today", "image_info", "calculate", "convert_units", "time_in",
             "current_date", "days_until", "date_math", "convert_time", "flip_coin", "roll_dice", "random_number", "make_password", "make_uuid", "hash_text",
             "base64_encode", "base64_decode", "word_count", "reverse_text", "shout", "morse_code", "json_pretty", "is_prime", "roman_numeral",
             "tip", "read_document", "find_in_document", "ask_document", "list_mcp_tools", "list_tabs", "switch_tab", "read_tab", "disk_space", "uptime", "memory_usage", "cpu_load", "ip_address", "wifi_name", "system_info", "list_shortcuts",
             "reveal_in_finder"}
# Tools whose side effect nobody sees coming. They never reach a model or MCP, whatever tools.NOT_FOR_MODELS says today.
MUST_HIDE = {"ask_claude", "run_shortcut", "copy_to_clipboard", "sleep_display", "call_mcp_tool", "close_tab", "remember", "recall", "forget", "read_screen", "ask_screen"}
# A spoken command for each write tool that has a route. The image tools are picked by her model or the agent, never by a route.
SPOKEN = {"ask_claude": "ask claude why is the sky blue", "new_note": "take a note buy milk", "new_reminder": "remind me to call mom", "make_logo": "make me a logo for turing",
          "copy_to_clipboard": "copy hello to my clipboard", "sleep_display": "sleep the screen", "run_shortcut": "run shortcut morning",
          "paint_image": "paint ~/Desktop/mona.jpg", "call_mcp_tool": "call mcp samantha calculate {}", "close_tab": "close the github tab", "remember": "remember that my dog is called biscuit", "forget": "forget biscuit", "read_screen": "read my screen", "ask_screen": "on my screen, what is the total"}
# Law 8: no god files. A ratchet: it only ever moves down, lowered after each split lands (CLAUDE.md, File size).
MAX_LINES = 825
PEOPLE_READ = ["README.md", "CLAUDE.md", "WHITEPAPER.md", "FAQ.md", "roadmap.md", "LAWS.md", "docs/ARCHITECTURE.md", "web/index.html",
               "web/demo.js", "web/samantha.js", "web/faq.json"]


def broken():
    """Every law that does not hold right now, as sentences."""
    out = []
    unknown = tools.WRITES | tools.NOT_FOR_MODELS
    out += [f"law 1: {n} is in WRITES or NOT_FOR_MODELS but is not a tool" for n in unknown - set(tools.TOOLS)]
    out += [f"law 1: {n} is not classified: add it to WRITES, NOT_FOR_MODELS or READ_ONLY in eval/laws.py" for n in set(tools.TOOLS) - unknown - READ_ONLY]
    out += [f"law 1: {n} is both read-only and a writer" for n in READ_ONLY & unknown if n not in ("reveal_in_finder",)]

    import mcp_server
    out += [f"law 2: {n} must stay in NOT_FOR_MODELS" for n in sorted(MUST_HIDE - tools.NOT_FOR_MODELS)]
    served = {t["name"] for t in mcp_server._tools()}
    out += [f"law 2: {n} is served over MCP" for n in sorted(served & MUST_HIDE)]
    out += [f"law 2: {n} is on a model's menu" for n in sorted(set(tools.model_tools()) & MUST_HIDE)]

    import tempfile
    mem = os.path.join(tempfile.mkdtemp(), "memory.json")
    os.environ["SAMANTHA_MEMORY"] = mem  # a denied remember must leave no file behind, and must never touch the real one
    for name, spoken in SPOKEN.items():
        with mock.patch.object(tools, "_run") as run, mock.patch.object(tools, "_app") as app, mock.patch("subprocess.run") as sp, \
                mock.patch("subprocess.Popen") as po, mock.patch("tools_util.subprocess.run") as usp:
            reply = harness.Session(confirm=lambda n, a: False, log=lambda line: None).ask(spoken)
            ran = run.call_count + app.call_count + sp.call_count + po.call_count + usp.call_count
        if name in tools.WRITES and (ran or reply != "Okay, I will not."):
            out.append(f"law 3: saying no to {name!r} ({spoken!r}) still ran {ran} command(s), reply {reply!r}")
    if os.path.exists(mem):
        out.append("law 3: saying no to remember or forget still wrote the memory file")
    os.environ.pop("SAMANTHA_MEMORY", None)
    out += [f"law 3: {n} has no spoken command in eval/laws.py and is not an image tool" for n in tools.WRITES - set(SPOKEN)
            if not n.endswith("_image") and n not in ("crop_square", "remove_background")]

    for probe in ("~/.ssh/id_rsa", "/etc/passwd", "~/../../etc/passwd"):
        for fn in (tools.read_file, tools.list_dir, tools_util_reveal(), tools_util_doc()):
            if not re.search(r"(?i)no file|no folder|not allowed|don't read|can't", str(fn(probe))):
                out.append(f"law 4: {fn.__name__}({probe!r}) was not refused")

    bare = [n for n, f in tools.TOOLS.items() if not f.__doc__]
    out += [f"law 5: tool {n} has no docstring" for n in bare]
    if subprocess.run([sys.executable, "stats.py", "--check"], cwd=REPO, capture_output=True).returncode:
        out.append("law 5: docs coverage is below 100 percent (python3 stats.py --check names the gaps)")
    arch = open(os.path.join(REPO, "docs", "ARCHITECTURE.md")).read()
    out += [f"law 5: {os.path.basename(p)} has no row in docs/ARCHITECTURE.md" for p in sorted(glob.glob(os.path.join(REPO, "*.py")))
            if os.path.basename(p) not in arch]

    if subprocess.run([sys.executable, "eval/util_diff.py"], cwd=REPO, capture_output=True).returncode:
        out.append("law 6: the JavaScript tools and the Python tools disagree (python3 eval/util_diff.py shows where)")

    for path in PEOPLE_READ:
        text = open(os.path.join(REPO, path)).read()
        if "—" in text:
            out.append(f"law 7: em dash in {path}")
    for path in sorted(glob.glob(os.path.join(REPO, "*.py")) + glob.glob(os.path.join(REPO, "eval", "*.py")) + glob.glob(os.path.join(REPO, "pixelmator", "*.py"))):
        with open(path) as f:
            n = sum(1 for _ in f)
        if n > MAX_LINES:
            out.append(f"law 8: {os.path.relpath(path, REPO)} is {n} lines, over {MAX_LINES}: split it (CLAUDE.md, File size)")
    demo = open(os.path.join(REPO, "web", "demo.js")).read()
    if "startDemo(); return;" not in demo:
        out.append("law 7: web/demo.js must not probe localhost for every visitor")
    return out


def tools_util_doc():
    """read_document, which lives in tools_util."""
    import tools_util
    return tools_util.read_document


def tools_util_reveal():
    """reveal_in_finder, which lives in tools_util."""
    import tools_util
    return tools_util.reveal_in_finder


def main():
    """Print every broken law and exit 1, or print how many held."""
    bad = broken()
    for line in bad:
        print("BROKEN", line)
    print("laws: %s" % ("all hold" if not bad else f"{len(bad)} broken"))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
