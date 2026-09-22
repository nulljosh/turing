"""Samantha's utility tools: forty-nine small things that need no app and no network, and their ROUTES.

Math, units, chance and text live in util_math.py, time and dates in util_dates.py; this module re-exports them.
The system readers (disk_space, uptime, memory_usage...) run one fixed argv each and
only read. Six tools touch the Mac or another program (copy_to_clipboard, sleep_display,
reveal_in_finder, run_shortcut, call_mcp_tool, close_tab) and stay silent under SAMANTHA_HEADLESS=1, so a test run
never clobbers a clipboard, blanks a screen or fires someone's Shortcut. Like the rest of her hands there is no
shell: every command is a fixed list, never a string someone wrote.

ROUTES is the regex table tools.py appends to its own, so each of these also works
with no model in the loop.
"""
import ast
import base64
import hashlib
import json
import math
import operator
import os
import random
import re
import secrets
import shutil
import string
import subprocess
import urllib.request
import uuid
from datetime import date, datetime
from zoneinfo import ZoneInfo

HEADLESS = os.environ.get("SAMANTHA_HEADLESS") == "1"


def _sh(argv, timeout=5):
    """Run one fixed argv and return its output, or "" if it is not here."""
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return ""
    return (r.stdout or "").strip()


# the pure tools live in their own files; every name is re-exported here so tools.py, the tests and ROUTES are unchanged
from util_math import *  # noqa: F401,F403
from util_math import _num, _eval, _OPS, _FUNCS, _CONSTS, _LENGTH, _MASS, _VOLUME, _TIME, _UNIT_ALIASES, _TEMPS, _MORSE  # noqa: F401
from util_dates import *  # noqa: F401,F403
from tools_claude import ask_claude  # noqa: E402  (the one tool that leaves the Mac, in its own file)
from util_dates import _ZONES, _HOLIDAYS, _MONTHS, _COUNT, _day, _shift, _long, _say, _MONTH_NAMES, _DAY_NAMES  # noqa: F401


# ---------- this Mac, read only ----------

def disk_space():
    """How much disk space is free on this Mac."""
    u = shutil.disk_usage("/")
    return f"{u.free / 1e9:.0f} GB free of {u.total / 1e9:.0f} GB."


def uptime():
    """How long this Mac has been on since its last restart."""
    m = re.search(r"sec = (\d+)", _sh(["sysctl", "-n", "kern.boottime"]))
    if not m:
        return "I cannot read the uptime here."
    s = int(datetime.now().timestamp()) - int(m.group(1))
    d, h, mins = s // 86400, s % 86400 // 3600, s % 3600 // 60
    return "Up " + ", ".join(f"{v} {k}{'s' * (v != 1)}" for v, k in ((d, "day"), (h, "hour"), (mins, "minute")) if v or k == "minute") + "."


def memory_usage():
    """How much memory this Mac has and roughly how much is free."""
    total = _sh(["sysctl", "-n", "hw.memsize"])
    vm = _sh(["vm_stat"])
    if not total.isdigit() or not vm:
        return "I cannot read memory here."
    page = int((re.search(r"page size of (\d+)", vm) or [0, 16384])[1])
    free = sum(int((re.search(rf"Pages {k}:\s+(\d+)", vm) or [0, 0])[1]) for k in ("free", "inactive", "speculative"))
    return f"{int(total) / 2 ** 30:.0f} GB of memory, about {free * page / 2 ** 30:.1f} GB free."


def cpu_load():
    """How busy the processor is: the load average across its cores."""
    a, b, c = os.getloadavg()
    return f"Load average {a:.2f}, {b:.2f}, {c:.2f} on {os.cpu_count()} cores."


def ip_address():
    """This Mac's IP address on the local network."""
    ip = _sh(["ipconfig", "getifaddr", "en0"]) or _sh(["ipconfig", "getifaddr", "en1"])
    return ip or "No network address. Are you online?"


def wifi_name():
    """The Wi-Fi network this Mac is on."""
    ports = _sh(["networksetup", "-listallhardwareports"])
    m = re.search(r"Hardware Port: Wi-Fi\s+Device: (\w+)", ports)
    if not m:
        return "This Mac has no Wi-Fi."
    out = _sh(["networksetup", "-getairportnetwork", m.group(1)])
    return out.replace("Current Wi-Fi Network: ", "On ") if out.startswith("Current") else "Not on a Wi-Fi network."


def system_info():
    """The macOS version, chip and memory of this Mac."""
    ver, chip, mem = _sh(["sw_vers", "-productVersion"]), _sh(["sysctl", "-n", "machdep.cpu.brand_string"]), _sh(["sysctl", "-n", "hw.memsize"])
    if not ver:
        return "I cannot read the system info here."
    return f"macOS {ver} on {chip or 'an unknown chip'}" + (f", {int(mem) / 2 ** 30:.0f} GB." if mem.isdigit() else ".")


# ---------- this Mac, does something ----------

def copy_to_clipboard(text):
    """Put some text on the clipboard."""
    if not HEADLESS:
        subprocess.run(["pbcopy"], input=text[:10000], text=True, timeout=5)
    return "Copied."


def sleep_display():
    """Put the screen to sleep, which locks it if a password is required on wake."""
    if not HEADLESS:
        _sh(["pmset", "displaysleepnow"])
    return "Screen off."


def _home_path(path):
    """The real path of something inside the home folder, or None: outside it, hidden, or not there."""
    home = os.path.realpath(os.path.expanduser("~"))
    full = os.path.realpath(os.path.expanduser(path.strip().strip("'\"")))
    rel = os.path.relpath(full, home)
    if rel.startswith("..") or any(part.startswith(".") and part != "." for part in rel.split(os.sep)) or not os.path.exists(full):
        return None
    return full


def _doc_text(path):
    """The text of a PDF, Word, RTF, HTML or plain text file, or (None, why). Home folder only, never hidden files."""
    full = _home_path(path)
    if not full or not os.path.isfile(full):
        return None, f"No file {path.strip()} I am allowed to read."
    ext = os.path.splitext(full)[1].lower()
    if ext == ".pdf":
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pdf.swift")
        text = _sh(["swift", script, full], timeout=90)
    elif ext in (".docx", ".doc", ".rtf", ".rtfd", ".html", ".htm", ".odt", ".webarchive"):
        text = _sh(["textutil", "-convert", "txt", "-stdout", full], timeout=30)
    elif ext in (".txt", ".md", ".csv", ".json", ".log", ""):
        try:
            text = open(full, errors="replace").read(400_000)
        except OSError:
            text = ""
    else:
        return None, f"I do not read {ext} files."
    text = re.sub(r"[ \t]+", " ", text or "").strip()
    return (text, None) if text else (None, "I found no text in that file. It may be a scan.")


def read_document(path):
    """Read the text of a PDF, Word, RTF, HTML or text file in the home folder. The first 3000 characters."""
    text, why = _doc_text(path)
    return why if why else re.sub(r"\s*\n\s*", " ", text)[:3000]


def find_in_document(request):
    """Find the passages of a document that mention some words. Takes 'words<TAB>path'. Up to three passages."""
    words, _, path = request.partition("\t")
    text, why = _doc_text(path)
    if why:
        return why
    want = _words(words)
    if not want:
        return "Tell me what to look for."
    flat = re.sub(r"\s+", " ", text)
    hits, seen = [], 0
    for m in re.finditer(r"[^.!?\n]{0,160}(?:" + "|".join(re.escape(w) for w in sorted(want)) + r")[^.!?\n]{0,160}", flat, re.I):
        if m.start() < seen:
            continue
        hits.append(m.group(0).strip())
        seen = m.end()
        if len(hits) == 3:
            break
    return " | ".join(hits) if hits else f"I do not see {words.strip()} in that document."


OLLAMA_CHAT = "http://localhost:11434/api/chat"
READER = "qwen3:1.7b"  # the same small reader ask.py uses for articles: it reads text, it does not recall


def _passages(text, question, limit=5000):
    """The parts of a long text that share the most words with a question, in reading order, up to a size limit."""
    if len(text) <= limit:
        return text
    chunks = [c.strip() for c in re.split(r"(?<=[.!?])\s+|\n{2,}", text) if c.strip()]
    want = _words(question)
    ranked = sorted(range(len(chunks)), key=lambda i: -len(want & _words(chunks[i])))
    keep, size = [], 0
    for i in ranked:
        if size + len(chunks[i]) > limit:
            break
        keep.append(i)
        size += len(chunks[i]) + 1
    return " ".join(chunks[i] for i in sorted(keep))


def _read_and_answer(text, question):
    """Ask the local reader model one question about a text and check the answer against the text. None if it cannot say."""
    body = json.dumps({"model": READER, "stream": False, "think": False, "options": {"temperature": 0}, "messages": [
        {"role": "system", "content": "Answer the question in one short sentence using ONLY the text. If the text does not contain the answer, reply exactly UNKNOWN."},
        {"role": "user", "content": f"Text:\n{_passages(text, question)}\n\nQuestion: {question}"}]}).encode()
    try:
        req = urllib.request.Request(OLLAMA_CHAT, body, {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as r:
            answer = json.load(r)["message"]["content"]
    except Exception:
        return "NO_MODEL"
    answer = re.sub(r"(?s)<think>.*?</think>", "", answer).strip()
    # every number and every capitalised name in the answer must be in the text or in the question: a guess is worse than a decline
    claims = re.findall(r"\d[\d,.]*\d|\d|\b[A-Z][a-z]{2,}\b", answer)
    grounded = all(c.lower().rstrip(".,") in text.lower() or c.lower() in question.lower() for c in claims[1:] or claims)
    declined = re.search(r"unknown|does not (?:contain|mention|say|provide|specify)|doesn't (?:contain|mention|say)|not (?:mentioned|stated|specified|provided)|no (?:information|mention)", answer, re.I)
    return None if not answer or declined or not grounded else answer


def ask_document(request):
    """Answer a question about a document in the home folder, from its text only. Takes 'question<TAB>path'. Needs Ollama running."""
    question, _, path = request.partition("\t")
    text, why = _doc_text(path)
    if why:
        return why
    if not question.strip():
        return "Ask me something about the document."
    got = _read_and_answer(text, question)
    if got == "NO_MODEL":
        return "My reader needs Ollama running with " + READER + ". These are the closest passages instead: " + find_in_document(question + "\t" + path)
    return got or "I could not find that in the document."


def ask_screen(question):
    """Answer a question about what is on the screen right now, from its text only. Private, asks first, needs Ollama running."""
    if HEADLESS:
        return "Would read the screen and answer."
    seen = read_screen()
    if not seen or seen.startswith(("I could not", "Would")):
        return seen
    got = _read_and_answer(seen.replace(" | ", "\n"), question)
    if got == "NO_MODEL":
        return "My reader needs Ollama running with " + READER + ". Here is what the screen says: " + seen[:600]
    return got or "I could not find that on the screen."


def reveal_in_finder(path):
    """Show a file or folder in Finder. Only inside the home folder, never hidden files."""
    full = _home_path(path)
    if not full:
        return f"No file or folder {path.strip()} I am allowed to show."
    if not HEADLESS:
        _sh(["open", "-R", full])
    return f"Showing {os.path.basename(full)} in Finder."


def _shortcuts():
    """The names of the Shortcuts on this Mac, from the shortcuts command."""
    return [n.strip() for n in _sh(["shortcuts", "list"], timeout=15).splitlines() if n.strip()]


def list_shortcuts():
    """List the Apple Shortcuts on this Mac by name."""
    names = _shortcuts()
    if not names:
        return "No Shortcuts found on this Mac."
    return f"{len(names)} Shortcuts: " + ", ".join(names[:40]) + (f", and {len(names) - 40} more." if len(names) > 40 else ".")


def run_shortcut(name):
    """Run one of the user's Apple Shortcuts by its exact name. Only when asked by name, never chosen by a model."""
    want = name.strip().strip("'\"")
    match = next((n for n in _shortcuts() if n.lower() == want.lower()), None)
    if not match:
        return f"I do not see a Shortcut called {want}. Say \"list my shortcuts\" to see them."
    if HEADLESS:
        return f"Would run {match}."
    out = _sh(["shortcuts", "run", match], timeout=60)
    return f"Ran {match}." + (f" It said: {out[:500]}" if out else "")


_CHROME = "Google Chrome"
_TABS = (f'tell application "{_CHROME}"\nset out to ""\nset wi to 0\nrepeat with w in windows\nset wi to wi + 1\nset ti to 0\n'
         'repeat with t in tabs of w\nset ti to ti + 1\nset out to out & wi & "." & ti & (ASCII character 9) & (title of t) & (ASCII character 9) & (URL of t) & linefeed\n'
         'end repeat\nend repeat\nreturn out\nend tell')


def _tabs():
    """Chrome's open tabs as (window, tab, title, url), or [] when Chrome has none."""
    rows = []
    if not _sh(["pgrep", "-x", _CHROME]):  # asking a closed Chrome about its tabs would launch it
        return rows
    for line in _sh(["osascript", "-e", _TABS], timeout=15).splitlines():
        pos, _, rest = line.partition("\t")
        title, _, url = rest.partition("\t")
        w, _, t = pos.partition(".")
        if w.isdigit() and t.isdigit():
            rows.append((int(w), int(t), title, url))
    return rows


def _find_tab(query):
    """The tab a phrase means: a number like 2 or 1.3, or a word from its title or address. Returns (tab, None) or (None, why)."""
    tabs, q = _tabs(), query.strip().lower().strip("'\"")
    if not tabs:
        return None, "Chrome has no tabs open."
    if not q:
        return tabs[0], None
    m = re.fullmatch(r"(?:(\d+)\.)?(\d+)", q)
    if m:
        want = (int(m.group(1) or 1), int(m.group(2)))
        hit = next((t for t in tabs if (t[0], t[1]) == want), None)
        return (hit, None) if hit else (None, f"No tab {q}.")
    hit = next((t for t in tabs if q in t[2].lower() or q in t[3].lower()), None)
    return (hit, None) if hit else (None, f"No tab matches {q}.")


def list_tabs():
    """List the tabs open in Chrome, numbered, with their titles and sites."""
    tabs = _tabs()
    if not tabs:
        return "Chrome has no tabs open."
    site = lambda url: re.sub(r"^https?://(?:www\.)?", "", url).split("/")[0]
    lines = [f"{w}.{t} {title[:60]} ({site(url)})" for w, t, title, url in tabs[:25]]
    return "\n".join(lines) + (f"\nand {len(tabs) - 25} more" if len(tabs) > 25 else "")


def switch_tab(query):
    """Bring a Chrome tab to the front. Takes a number like 2 or 1.3, or a word from its title or address."""
    tab, why = _find_tab(query)
    if not tab:
        return why
    if not HEADLESS:
        _sh(["osascript", "-e", f'tell application "{_CHROME}"\nset active tab index of window {tab[0]} to {tab[1]}\nset index of window {tab[0]} to 1\nactivate\nend tell'])
    return f"Switched to {tab[2][:60]}."


def close_tab(query):
    """Close one Chrome tab. Takes a number like 2 or 1.3, or a word from its title or address. Asks first, never chosen by a model."""
    tab, why = _find_tab(query)
    if not tab or not query.strip():
        return why or "Say which tab: a number, or a word from its title."
    if not HEADLESS:
        _sh(["osascript", "-e", f'tell application "{_CHROME}" to close tab {tab[1]} of window {tab[0]}'])
    return f"Closed {tab[2][:60]}."


def read_tab(query=""):
    """Read the text of a Chrome tab as it is rendered, so pages built by JavaScript work too. No argument reads the front tab."""
    tab, why = _find_tab(query) if query.strip() else (next(iter(_tabs()), None), None)
    if not tab:
        return why or "Chrome has no tabs open."
    if HEADLESS:
        return f"Would read {tab[2][:60]}."
    out = _sh(["osascript", "-e", f'tell application "{_CHROME}" to execute (tab {tab[1]} of window {tab[0]}) javascript "document.body.innerText"'], timeout=20)
    if not out:
        return "Chrome would not hand over the page. Turn on View, Developer, Allow JavaScript from Apple Events, then ask again."
    return re.sub(r"\s+", " ", out).strip()[:3000]


def read_screen(query=""):
    """Read the text on the screen right now, with macOS Vision OCR. Private, so it asks first and is only used when named."""
    if HEADLESS:
        return "Would read the screen."
    import tempfile
    fd, shot = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    try:
        _sh(["screencapture", "-x", "-t", "png", shot], timeout=15)
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ocr.swift")
        text = _sh(["swift", script, shot], timeout=90)
    finally:
        os.unlink(shot)
    if not text:
        return "I could not read the screen. Screen Recording may need to be allowed for this app, or nothing on it is text."
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    want = _words(query)
    if want:
        lines = [ln for ln in lines if want & _words(ln)] or lines[:0]
        if not lines:
            return f"I do not see {query.strip()} on the screen."
    return " | ".join(lines)[:1500]


def _memory_path():
    """Where her memory lives: ~/.samantha/memory.json, or SAMANTHA_MEMORY (the tests use it)."""
    return os.path.expanduser(os.environ.get("SAMANTHA_MEMORY", "~/.samantha/memory.json"))


def _facts():
    """Everything she has been told to remember, oldest first."""
    try:
        got = json.load(open(_memory_path()))
    except (OSError, ValueError):
        return []
    return [f for f in got if isinstance(f, str)] if isinstance(got, list) else []


def _save(facts):
    """Write the memory file, creating its folder. Only ever the last 500 facts."""
    path = _memory_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(facts[-500:], open(path, "w"), indent=1)


def _words(text):
    """The words worth matching on: lowercase, longer than two letters."""
    return {w for w in re.findall(r"[a-z0-9']+", text.lower()) if len(w) > 2}


def recall_lines(query):
    """The remembered facts that share the most words with a query, best first, at most three."""
    want = _words(query)
    scored = sorted(((len(want & _words(f)), i, f) for i, f in enumerate(_facts())), key=lambda t: (-t[0], -t[1]))
    return [f for n, _, f in scored if n][:3]


def remember(text):
    """Remember a fact across sessions, in a file on this Mac. Asks first, and only when told to, never chosen by a model."""
    fact = " ".join(text.split())[:300]
    if not fact:
        return "Tell me what to remember."
    facts = _facts()
    if fact.lower() in (f.lower() for f in facts):
        return "I already know that."
    _save(facts + [fact])
    return f"Remembered: {fact}"


def recall(query):
    """Say what she remembers about a subject. Private, so only asked for by name."""
    found = recall_lines(query)
    return "\n".join(found) if found else f"I do not remember anything about {query.strip() or 'that'}."


def forget(query):
    """Forget the facts that mention every word of a phrase. Asks first, never chosen by a model."""
    want = _words(query)
    if not want:
        return "Say what to forget."
    facts = _facts()
    hit = [f for f in facts if want <= _words(f)]
    if not hit:
        return f"I do not remember anything about {query.strip()}."
    if len(hit) > 5:
        return f"That matches {len(hit)} things. Be more specific."
    _save([f for f in facts if f not in hit])
    return f"Forgot {len(hit)} thing{'s' * (len(hit) != 1)}."


def _mcp_config():
    """The MCP servers she may call: name to argv, from ~/.samantha/mcp.json (or SAMANTHA_MCP_CONFIG). Argv only, never a shell string."""
    path = os.path.expanduser(os.environ.get("SAMANTHA_MCP_CONFIG", "~/.samantha/mcp.json"))
    try:
        servers = json.load(open(path)).get("servers", {})
    except (OSError, ValueError):
        return {}
    return {n: a for n, a in servers.items() if isinstance(a, list) and a and all(isinstance(x, str) for x in a)}


def _mcp_talk(argv, calls, timeout=30):
    """Run one MCP server for a short conversation: initialize, then each (method, params) in calls. Returns the results in order."""
    msgs = [{"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                                                                              "clientInfo": {"name": "samantha", "version": "1"}}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"}]
    msgs += [{"jsonrpc": "2.0", "id": i + 1, "method": m, "params": p} for i, (m, p) in enumerate(calls)]
    try:
        r = subprocess.run(argv, input="\n".join(json.dumps(m) for m in msgs) + "\n", capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as e:
        raise RuntimeError(f"could not run it: {e}")
    replies = {}
    for line in r.stdout.splitlines():
        try:
            m = json.loads(line)
        except ValueError:
            continue
        if isinstance(m, dict) and "id" in m:
            replies[m["id"]] = m
    out = []
    for i in range(len(calls)):
        m = replies.get(i + 1)
        if not m or "error" in m:
            raise RuntimeError((m or {}).get("error", {}).get("message", "no answer"))
        out.append(m["result"])
    return out


def list_mcp_tools():
    """List the tools of the MCP servers in her config, so she knows what else she can call."""
    servers = _mcp_config()
    if not servers:
        return "No MCP servers configured. Add some to ~/.samantha/mcp.json."
    lines = []
    for name, argv in servers.items():
        try:
            tools_ = _mcp_talk(argv, [("tools/list", {})])[0]["tools"]
            lines.append(f"{name}: " + ", ".join(t["name"] for t in tools_[:30]) + (f", and {len(tools_) - 30} more" if len(tools_) > 30 else ""))
        except (RuntimeError, KeyError, TypeError) as e:
            lines.append(f"{name}: unavailable ({e})")
    return "\n".join(lines)


def call_mcp_tool(request):
    """Call one tool on one of her MCP servers. Takes 'server tool {json arguments}'. Asks first, and only when named, never chosen by a model."""
    parts = request.strip().split(None, 2)
    if len(parts) < 2:
        return 'Say it like: call mcp samantha calculate {"expression": "2+2"}'
    server, tool, raw = parts[0], parts[1], (parts[2] if len(parts) > 2 else "{}")
    servers = _mcp_config()
    if server not in servers:
        return f"I do not have an MCP server called {server}." + (f" I have: {', '.join(servers)}." if servers else " None are configured.")
    try:
        args = json.loads(raw)
        if not isinstance(args, dict):
            raise ValueError("arguments must be an object")
    except ValueError as e:
        return f"Those arguments are not a JSON object: {e}."
    try:
        res = _mcp_talk(servers[server], [("tools/call", {"name": tool, "arguments": args})])[0]
    except RuntimeError as e:
        return f"{server} said no: {e}."
    text = " ".join(c.get("text", "") for c in res.get("content", []) if isinstance(c, dict) and c.get("type") == "text").strip()
    return ("Error from " + server + ": " if res.get("isError") else "") + (text[:2000] or "Done, with no text back.")


TOOLS = (ask_claude, calculate, convert_units, time_in, convert_time, current_date, days_until, date_math, flip_coin, roll_dice, random_number, make_password,
         make_uuid, hash_text, base64_encode, base64_decode, word_count, reverse_text, shout, morse_code, json_pretty,
         is_prime, roman_numeral, tip, disk_space, uptime, memory_usage, cpu_load, ip_address, wifi_name, system_info,
         copy_to_clipboard, sleep_display, reveal_in_finder, list_shortcuts, run_shortcut, list_mcp_tools, call_mcp_tool, list_tabs, switch_tab, close_tab, read_tab, remember, recall, forget, read_screen, read_document, find_in_document, ask_document, ask_screen)

_I = re.I
# (pattern, tool name, what to hand it). Names, not functions: tools.py looks each one up at call time.
ROUTES = (
    # only by name: "ask claude ...", "claude, ..." (the harness asks before anything leaves the Mac)
    (re.compile(r"^(?:ask|have|let) claude(?: to| about| whether| if|:|,)?\s+(.+)$|^(?:hey )?claude[,:]\s*(.+)$", _I),
     "ask_claude", lambda m: m.group(1) or m.group(2)),
    # a time in one zone to another: ahead of convert_units, so "convert 3pm pst to tokyo" is a time, not a unit
    (re.compile(r"^(?:what(?:'s| is)(?: the time)?|what time is|when is|convert)?\s*((?:noon|midnight|\d{1,2}:\d{2}(?:\s*(?:am|pm|a\.m\.|p\.m\.))?|\d{1,2}\s*(?:am|pm|a\.m\.|p\.m\.))\s+.*\b(?:in|to)\s+.+)$", _I),
     "convert_time", lambda m: m.group(1)),
    (re.compile(r"^(?:calc(?:ulate)?|compute|work out|math)[: ]+(.+)$", _I), "calculate", lambda m: m.group(1)),
    (re.compile(r"^(?:convert )?(-?\d+) (?:to|in|into) roman(?: numerals?)?$", _I), "roman_numeral", lambda m: m.group(1)),
    (re.compile(r"^convert (.+)$", _I), "convert_units", lambda m: m.group(1)),
    (re.compile(r"^what time is it in (.+)$|^(?:what(?:'s| is) )?(?:the )?time in (.+)$", _I), "time_in", lambda m: m.group(1) or m.group(2)),
    (re.compile(r"^what(?:'s| is)(?: the)? date(?: today)?$|^what day is it(?: today)?$|^today'?s date$", _I), "current_date", lambda m: ""),
    (re.compile(r"^(?:how many )?days? between (.+?) and (.+)$", _I), "date_math", lambda m: f"between {m.group(1)} and {m.group(2)}"),
    (re.compile(r"^(?:how many )?days? (?:until|till|to) (.+)$|^how long (?:until|till) (.+)$", _I), "days_until", lambda m: m.group(1) or m.group(2)),
    (re.compile(r"^(?:what(?:'s| is)(?: the date)? |what day is |when is |what date is )?((?:\d{1,6}|a|an|one|two|three|four|five|six|seven|eight|nine|ten) (?:day|week|month|year)s? (?:from(?: .+)?|ago|after .+|before .+))$", _I),
     "date_math", lambda m: m.group(1)),
    (re.compile(r"^(?:what )?day of (?:the )?week (?:is|was|will be|for) (.+)$|^what day (?:is|was|will be) ((?:\w+ \d{1,2}(?:st|nd|rd|th)?,? \d{3,4})|(?:\d{1,2} \w+ \d{3,4})|\d{4}-\d{2}-\d{2})$", _I),
     "date_math", lambda m: "weekday " + (m.group(1) or m.group(2))),
    (re.compile(r"^(?:flip|toss) a coin$", _I), "flip_coin", lambda m: ""),
    (re.compile(r"^roll (?:a |an )?(\d*d\d+)$", _I), "roll_dice", lambda m: m.group(1)),
    (re.compile(r"^roll (?:a |the )?(?:dice|die)$", _I), "roll_dice", lambda m: "1d6"),
    (re.compile(r"^(?:pick |give me |generate )?(?:a )?random number(?: (?:between|from) (.+))?$", _I), "random_number", lambda m: m.group(1) or ""),
    (re.compile(r"^(?:generate|make|create|give me)(?: me)? (?:a |an )?(?:strong |secure |random )?password(?:(?: of| with)? (\d+)(?: char\w*)?)?$", _I), "make_password", lambda m: m.group(1) or "16"),
    (re.compile(r"^(?:generate|make|create|give me)(?: me)? (?:a |an )?(?:new |random )?(?:uuid|guid)$", _I), "make_uuid", lambda m: ""),
    (re.compile(r"^sha-?256(?: of)?[: ]+(.+)$|^hash(?: of|:) (.+)$", _I), "hash_text", lambda m: (m.group(1) or m.group(2))),
    (re.compile(r"^base64 encode[: ]+(.+)$", _I), "base64_encode", lambda m: m.group(1)),
    (re.compile(r"^base64 decode[: ]+(.+)$", _I), "base64_decode", lambda m: m.group(1)),
    (re.compile(r"^(?:count (?:the )?words in|word count(?: of)?)[: ]+(.+)$", _I), "word_count", lambda m: m.group(1)),
    (re.compile(r"^reverse(?: the)? (?:text|words?|string)[: ]+(.+)$|^reverse: (.+)$", _I), "reverse_text", lambda m: (m.group(1) or m.group(2))),
    (re.compile(r"^(?:shout|uppercase)[: ]+(.+)$", _I), "shout", lambda m: m.group(1)),
    (re.compile(r"^morse(?: code)?(?: for| of)?[: ]+(.+)$", _I), "morse_code", lambda m: m.group(1)),
    (re.compile(r"^(?:pretty ?print|format|prettify) json[: ]+(.+)$", _I), "json_pretty", lambda m: m.group(1)),
    (re.compile(r"^is (-?\d+) (?:a )?prime$|^(?:prime factors of|factor|factorize) (-?\d+)$", _I), "is_prime", lambda m: m.group(1) or m.group(2)),
    (re.compile(r"^roman numerals? (?:for |of )?(-?\d+)$|^(-?\d+) in roman numerals$", _I), "roman_numeral", lambda m: m.group(1) or m.group(2)),
    (re.compile(r"^(?:(?:what(?:'s| is) )?(?:the |a )?tip on|tip(?: for)?) (-?\$?-?\d+(?:\.\d+)?)$", _I), "tip", lambda m: m.group(1)),
    (re.compile(r"^(?:check )?disk space$|^how much (?:disk |storage )?space (?:do i have|is (?:left|free))(?: left)?$|^how much storage (?:do i have|is left)$", _I), "disk_space", lambda m: ""),
    (re.compile(r"^how long has (?:my mac|this mac|it) been (?:on|up|running)$|^uptime$", _I), "uptime", lambda m: ""),
    (re.compile(r"^(?:how much )?(?:ram|memory)(?: (?:do i have|is free|is left|am i using))?$|^(?:ram|memory) usage$", _I), "memory_usage", lambda m: ""),
    (re.compile(r"^(?:cpu|processor) (?:load|usage)$|^how busy is (?:my mac|the cpu)$|^load average$", _I), "cpu_load", lambda m: ""),
    (re.compile(r"^(?:what(?:'s| is) )?my (?:local )?ip(?: address)?$", _I), "ip_address", lambda m: ""),
    (re.compile(r"^(?:what|which) wi-?fi(?: network)?(?: am i (?:on|connected to))?$|^wi-?fi name$", _I), "wifi_name", lambda m: ""),
    (re.compile(r"^(?:system|mac) info$|^what mac (?:is this|am i on)$|^about this mac$", _I), "system_info", lambda m: ""),
    (re.compile(r"^copy (.+) to (?:the |my )?clipboard$", _I), "copy_to_clipboard", lambda m: m.group(1)),
    (re.compile(r"^(?:lock|sleep)(?: the| my)? (?:screen|display)$", _I), "sleep_display", lambda m: ""),
    (re.compile(r"^(?:reveal|show)(?: me)? (.+?) in finder$", _I), "reveal_in_finder", lambda m: m.group(1)),
    (re.compile(r"^(?:list|show)(?: me)?(?: all)?(?: my)? shortcuts$|^what shortcuts do i have$", _I), "list_shortcuts", lambda m: ""),
    (re.compile(r"^(?:list|show)(?: me)?(?: all)?(?: my)? mcp tools$|^what mcp tools do i have$", _I), "list_mcp_tools", lambda m: ""),
    (re.compile(r"^call mcp (\S+ \S+(?: .+)?)$", _I), "call_mcp_tool", lambda m: m.group(1)),
    (re.compile(r"^(?:list|show)(?: me)?(?: all)?(?: my| the)?(?: open)? (?:chrome )?tabs$|^what tabs (?:do i have(?: open)?|are open)(?: in chrome)?$", _I), "list_tabs", lambda m: ""),
    (re.compile(r"^switch to tab (\d+(?:\.\d+)?)$|^switch to (?:the )?(.+?) tab$", _I), "switch_tab", lambda m: (m.group(1) or m.group(2))),
    (re.compile(r"^close tab (\d+(?:\.\d+)?)$|^close (?:the )?(.+?) tab$", _I), "close_tab", lambda m: (m.group(1) or m.group(2))),
    (re.compile(r"^read tab (\d+(?:\.\d+)?)$|^read (?!(?:this|the current) tab$)(?:the )?(.+?) tab$|^read (?:this|the current) tab$", _I), "read_tab", lambda m: (m.group(1) or m.group(2) or "")),
    (re.compile(r"^(?:read|ocr) (?:my |the )?screen$|^what(?:'s| is) on my screen$|^what does my screen say$", _I), "read_screen", lambda m: ""),
    (re.compile(r"^find (.+) on (?:my |the )?screen$|^is (.+) on (?:my |the )?screen$", _I), "read_screen", lambda m: (m.group(1) or m.group(2))),
    (re.compile(r"^read (?:the )?(?:document|pdf|doc|file called) (.+)$", _I), "read_document", lambda m: m.group(1)),
    (re.compile(r"^find (.+?) in (?:the )?(?:document|pdf|doc) (.+)$", _I), "find_in_document", lambda m: m.group(1) + "\t" + m.group(2)),
    (re.compile(r"^what does (?:the )?(?:document|pdf|doc) (\S+) say about (.+)$", _I), "ask_document", lambda m: "what does it say about " + m.group(2) + "\t" + m.group(1)),
    (re.compile(r"^in (?:the )?(?:document|pdf|doc) (\S+?),? (.+)$", _I), "ask_document", lambda m: m.group(2) + "\t" + m.group(1)),
    (re.compile(r"^(?:on|from) my screen,? (.+)$", _I), "ask_screen", lambda m: m.group(1)),
    (re.compile(r"^remember that (.+)$", _I), "remember", lambda m: m.group(1)),
    (re.compile(r"^(?:recall|what do you remember about|what did i tell you about) (.+)$", _I), "recall", lambda m: m.group(1)),
    (re.compile(r"^forget (?:that |about )?(.+)$", _I), "forget", lambda m: m.group(1)),
    (re.compile(r"^run (?:the |my )?shortcut (.+)$|^run (.+) shortcut$", _I), "run_shortcut", lambda m: (m.group(1) or m.group(2))),
)


def demo():
    """Self-check: the pure tools exactly, the system readers for shape, the Mac-touching ones silent."""
    global HEADLESS
    HEADLESS = True  # a self-check never touches the clipboard, the screen or Finder
    assert calculate("17*23") == "391" and calculate("2^10") == "1024" and calculate("15% of 80") == "12"
    assert calculate("sqrt(144) + 1") == "13" and calculate("1/0") == "You cannot divide by zero."
    assert calculate("__import__('os')").startswith("Cannot") and calculate("9**9999").startswith("Cannot")
    assert convert_units("5 km to miles") == "5 km is 3.1069 mi." and convert_units("212 f to c") == "212 F is 100 C."
    assert convert_units("1 lb to oz") == "1 lb is 16 oz." and convert_units("1 mile to feet") == "1 mi is 5280 ft."
    assert "cannot convert" in convert_units("5 km to kg") and convert_units("nonsense").startswith("Say it")
    assert time_in("tokyo").endswith("in Tokyo.") and "time zone" in time_in("atlantis") and time_in().startswith("It is")
    assert current_date().startswith("It is ") and days_until("christmas") != days_until("halloween")
    assert days_until("2000-01-01").endswith("since January 1, 2000.") and days_until("soon").startswith("Give me")
    assert flip_coin() in ("Heads.", "Tails.") and 1 <= int(roll_dice("d20")) <= 20 and roll_dice("3d6").count("+") == 2
    assert roll_dice("500d6").startswith("Up to") and roll_dice("banana").startswith("Say it")
    assert 5 <= int(random_number("between 5 and 9")) <= 9 and 1 <= int(random_number()) <= 100
    assert len(make_password("20")) == 20 and len(make_password("3")) == 8 and len(make_password("999")) == 64
    assert len(make_uuid()) == 36 and hash_text("hello").startswith("2cf24dba")
    assert base64_encode("hi there") == "aGkgdGhlcmU=" and base64_decode("aGkgdGhlcmU=") == "hi there" and "not valid" in base64_decode("%%%")
    assert word_count("one two three") == "3 words, 13 characters." and word_count("hi") == "1 word, 2 characters."
    assert reverse_text("abc") == "cba" and shout("hey") == "HEY" and morse_code("sos") == "... --- ..."
    assert json_pretty('{"a":[1,2]}').count("\n") == 5 and "not valid" in json_pretty("{")
    assert is_prime("17") == "17 is prime." and is_prime("84") == "84 is not prime: 2 x 2 x 3 x 7." and is_prime("1").startswith("Give me")
    assert roman_numeral("2026") == "MMXXVI" and roman_numeral("4") == "IV" and roman_numeral("4000").startswith("Roman")
    assert tip("45") == "Tip on 45.00: 15% is 6.75, 18% is 8.10, 20% is 9.00." and tip("abc").startswith("Give me")
    assert disk_space().endswith("GB.") and "cores" in cpu_load()
    assert copy_to_clipboard("x") == "Copied." and sleep_display() == "Screen off." and reveal_in_finder("~").startswith("Showing")
    assert reveal_in_finder("~/.ssh").startswith("No file") and reveal_in_finder("/etc/passwd").startswith("No file")
    assert run_shortcut("zzz-not-real").startswith("I do not see") and (list_shortcuts().startswith("No Shortcuts") or "Shortcuts:" in list_shortcuts())
    assert len(TOOLS) == 50 and all(f.__doc__ for f in TOOLS)
    call = lambda name, a: globals()[name](a) if globals()[name].__code__.co_argcount else globals()[name]()
    hit = lambda q: next((call(name, arg(m)) for pat, name, arg in ROUTES if (m := pat.match(q))), None)
    assert hit("calculate 17 * 23") == "391" and hit("convert 5 km to miles") == "5 km is 3.1069 mi."
    assert hit("time in tokyo").endswith("in Tokyo.") and hit("what time is it in london").endswith("in London.")
    assert hit("roll 2d6").count("+") == 1 and hit("flip a coin") in ("Heads.", "Tails.") and hit("hash of hello").startswith("2cf2")
    assert len(hit("make me a password")) == 16 and len(hit("generate a strong password of 24 characters")) == 24
    assert hit("base64 encode hi there") == "aGkgdGhlcmU=" and hit("is 91 prime") == "91 is not prime: 7 x 13."
    assert hit("roman numerals for 1999") == "MCMXCIX" and hit("tip on 45").startswith("Tip on 45.00") and hit("morse sos") == "... --- ..."
    assert hit("what is my ip") is not None and hit("how much disk space do i have").endswith("GB.")
    assert hit("copy hello world to my clipboard") == "Copied." and hit("what is turing") is None and hit("open chrome") is None
    assert hit("run shortcut zzz-not-real").startswith("I do not see") and hit("run tests") is None and hit("run the build") is None
    assert hit("convert 2026 to roman numerals") == "MMXXVI" and hit("1999 in roman numerals") == "MCMXCIX"
    assert hit("read this tab") is not None and hit("read the github tab") is not None
    assert hit("hash browns are good") is None and hit("reverse psychology") is None and hit("reverse the text abc") == "cba" and hit("hash: hello").startswith("2cf2")
    print("tools_util ok")


if __name__ == "__main__":
    demo()
