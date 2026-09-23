#!/usr/bin/env python3
"""Does /api/chat actually work for someone typing into Joshua Tree's Chat window?

Real prompts a person would type there: what the OS is, who made it, its license,
how to open an app, whether it has Wi-Fi, what version it's running, small talk,
and two plain general-knowledge questions (the same pipeline /api/ask uses, so a
kernel Chat conversation that wanders off-topic still gets a real answer).

Hits the Ollama-compatible request/response shape kernel/chat.h's chat_send sends:
{"model": "...", "messages": [{"role": "user", "content": "..."}], "stream": false},
expecting {"model": "samantha", "message": {"role": "assistant", "content": "..."},
"done": true} back.

Run against a local `npx wrangler dev --port 8799`, or the live Worker:
eval/jt_chat.py [url=http://localhost:8799]
"""
import json
import sys
import time
import urllib.error
import urllib.request

URL = next((a for a in sys.argv[1:] if a.startswith("http")), "http://localhost:8799")
DECLINE = "couldn't find anything"

# (what a visitor types, a lowercase substring her reply must contain)
PROMPTS = [
    ("what is joshua tree", "operating system"),
    ("who made joshua tree", "trommel"),
    ("what license is joshua tree under", "apache"),
    ("how do I open Notes", "notes"),
    ("what does the Files app do", "filesystem"),
    ("what version is this", "1.0"),
    ("what is the lock screen", "lock screen"),
    ("hi", "ask me"),
    ("thanks", "any time"),
    ("tell me a joke", "programmers"),
    ("how are you", "running fine"),
    ("what can you do", "samantha"),
    ("how do I open the terminal", "terminal"),
    ("what does the weather app do", "weather"),
    ("what is curbfind", "craigslist"),
    ("what languages does joshua tree support", "english"),
    ("what is the calculator app", "calculator"),
    ("what is keyrate", "typing"),
    ("who made this", "trommel"),
    ("is there wi-fi", DECLINE),  # honest decline: the reader doesn't yet ground a negative fact reliably, see docs/ARCHITECTURE.md
    ("what is the capital of france", "paris"),
    ("who painted the mona lisa", "leonardo"),
]


def chat(question):
    """POST one /api/chat turn and return (status, reply text or "")."""
    body = {"model": "qwen3:8b", "stream": False, "think": False,
             "messages": [{"role": "user", "content": question}]}
    req = urllib.request.Request(URL + "/api/chat", json.dumps(body).encode(),
                                  {"Content-Type": "application/json", "User-Agent": "samantha-qa"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read() or b"{}")
            return r.status, data.get("message", {}).get("content", "")
    except urllib.error.HTTPError as e:
        return e.code, ""
    finally:
        time.sleep(2.5)  # 20 calls/60s shared per-IP limit; paced so a full run never trips its own rate limit


def post_chat(messages, origin=None):
    """POST a full /api/chat body (real messages array) and return (status, parsed json or {})."""
    body = {"model": "qwen3:8b", "stream": False, "think": False, "messages": messages}
    headers = {"Content-Type": "application/json", "User-Agent": "samantha-qa"}
    if origin:
        headers["Origin"] = origin
    req = urllib.request.Request(URL + "/api/chat", json.dumps(body).encode(), headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"{}")
        except Exception:
            return e.code, {}
    finally:
        time.sleep(2.5)  # same shared rate limit chat() paces against


def contract_checks():
    """The shape the kernel actually parses for, not just a working answer."""
    status, data = post_chat([{"role": "user", "content": "what is joshua tree"}])
    checks = [
        ("status 200", status == 200),
        ("reply is non-empty", bool(data.get("message", {}).get("content"))),
        ('"model" field present', "model" in data),
        ('"message"."role" is "assistant"', data.get("message", {}).get("role") == "assistant"),
        ('"done" is true', data.get("done") is True),
    ]

    # context turns never leak into what gets answered: only the newest user message counts
    _, multi = post_chat([
        {"role": "user", "content": "what is the capital of france"},
        {"role": "assistant", "content": "Paris."},
        {"role": "user", "content": "thanks"}])
    checks.append(("only the last user message is answered",
                    "any time" in multi.get("message", {}).get("content", "").lower()))

    # origin allow: joshuatree.heyitsmejosh.com and no Origin both work, a stranger site does not
    hi = [{"role": "user", "content": "hi"}]
    checks.append(("joshuatree.heyitsmejosh.com origin allowed", post_chat(hi, "https://joshuatree.heyitsmejosh.com")[0] == 200))
    checks.append(("no Origin header allowed", post_chat(hi)[0] == 200))
    checks.append(("a stranger origin is refused", post_chat(hi, "https://evil.example")[0] == 403))

    bad = 0
    for name, ok in checks:
        bad += not ok
        print(f"[{'PASS' if ok else 'FAIL'}] contract: {name}")
    return bad


def main():
    """Score every prompt, print the contract checks, and exit non-zero on any failure."""
    prompt_failed = 0
    for question, want in PROMPTS:
        status, reply = chat(question)
        ok = status == 200 and want in reply.lower()
        prompt_failed += not ok
        print(f"[{'PASS' if ok else 'FAIL'}] {question!r} -> {reply[:90]!r}")
    contract_failed = contract_checks()
    total = len(PROMPTS)
    print(f"{'ok' if not (prompt_failed or contract_failed) else 'BROKEN'}: "
          f"{total - prompt_failed}/{total} prompts, {contract_failed} contract checks failed")
    sys.exit(1 if prompt_failed or contract_failed else 0)


if __name__ == "__main__":
    main()
