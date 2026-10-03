"""Samantha's word tools: what she remembers for you (remember, recall, forget) and what a word means (define_word,
the Mac's own dictionary, offline). Split out of tools_util.py, which re-exports every name here, so callers and the
ROUTES table are unchanged."""
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def define_word(word):
    """What a word means, from the Mac's own dictionary, offline. Takes one word or a short phrase."""
    word = " ".join(re.sub(r"[^\w' -]", " ", word).split())[:60]
    if not word:
        return 'Define what? Say it like "define serendipity".'
    if sys.platform != "darwin" or not shutil.which("swift"):
        return "Definitions come from the Mac's dictionary, and this machine has none."
    try:
        out = subprocess.run(["swift", os.path.join(HERE, "swift", "define.swift"), word],
                             capture_output=True, text=True, timeout=60).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        out = ""
    if not out:
        return f"The dictionary on this Mac has no entry for {word}."
    # ponytail: first sense only, the word's history (ORIGIN) and phrases dropped; a --full flag if people ask
    return " ".join(out.split(" ORIGIN ")[0].split(" PHRASES ")[0].split())[:400]


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


_COMMON = {"the", "and", "you", "are", "was", "what", "who", "when", "where", "why", "how", "does", "did", "can", "could", "would", "should",
           "with", "for", "this", "that", "have", "has", "had", "not", "but", "his", "her", "its", "your", "our", "from", "about", "tell", "please"}


def memory_context(question):
    """The remembered facts that bear on a question, to read back into her answer: up to three that share a real word with it
    (not "the" or "what"), best first. Nothing when she remembers nothing relevant. In headless mode (tests, evals, CI) it reads
    nothing unless SAMANTHA_MEMORY names a file, so no run ever pulls in the real memory file by accident."""
    if os.environ.get("SAMANTHA_HEADLESS") and not os.environ.get("SAMANTHA_MEMORY"):
        return []
    want = _words(question) - _COMMON
    scored = sorted(((len(want & (_words(f) - _COMMON)), i, f) for i, f in enumerate(_facts())), key=lambda t: (-t[0], -t[1]))
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
