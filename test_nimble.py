"""Prove Samantha still works as a pluggable engine for other apps.

Joshua's ask: re-test this every few versions, so it has to be one command,
not a manual ritual with a browser.

This fires the *exact* request Nimble builds in Sources/Models/AIEngine.swift
for a local engine (same URL, same body shape, same system+user message
pair) and parses the response the way Nimble's `parse()` does, pulling
choices[0].message.content. If this passes, Nimble can talk to Samantha.
If it fails, the pipe is broken regardless of what the other suites say.

Starts and stops serve.py itself, on a port unlikely to collide, so there
is nothing to set up first.

Usage: ./.venv/bin/python test_nimble.py
"""
import json, os, subprocess, sys, time, urllib.error, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = 8131
BASE = f"http://localhost:{PORT}"

# copied from Nimble's AIEngine.swift so a drift in either shows up here
NIMBLE_SYSTEM = "Answer in one short factual sentence. No preamble, no markdown. If you do not know, reply exactly UNKNOWN."


def nimble_request(question):
    """Byte-for-byte the body Nimble sends for .openai/.ollama engines."""
    body = json.dumps({
        "model": "samantha",
        "max_tokens": 256,
        "messages": [
            {"role": "system", "content": NIMBLE_SYSTEM},
            {"role": "user", "content": question},
        ],
    }).encode()
    req = urllib.request.Request(
        BASE + "/v1/chat/completions", data=body,
        headers={"content-type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def nimble_parse(payload):
    """What Nimble's parse() does: choices[0].message.content, and treat
    UNKNOWN as 'this engine had nothing' rather than as an answer."""
    choices = payload.get("choices") or []
    text = ((choices[0].get("message") or {}).get("content") or "").strip() if choices else ""
    if not text or text.upper() == "UNKNOWN":
        return None
    return text


def wait_for_server(proc, timeout=30):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            raise SystemExit(f"serve.py exited early: {proc.stderr.read().decode()[:400]}")
        try:
            with urllib.request.urlopen(BASE + "/v1/models", timeout=2) as r:
                json.load(r)
            return
        except Exception:
            time.sleep(0.4)
    raise SystemExit("serve.py never became reachable")


def main():
    proc = subprocess.Popen(
        [os.path.join(HERE, ".venv/bin/python"), os.path.join(HERE, "serve.py"), "--port", str(PORT)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    failures = []
    try:
        wait_for_server(proc)

        models = json.load(urllib.request.urlopen(BASE + "/v1/models", timeout=5))
        ids = [m.get("id") for m in models.get("data", [])]
        if "samantha" not in ids:
            failures.append(f"/v1/models did not advertise samantha, got {ids}")

        # a project question, the thing Samantha is actually for
        answer = nimble_parse(nimble_request("what is samantha"))
        if not answer or "LoRA" not in answer:
            failures.append(f"project question did not come back usable: {answer!r}")

        # general knowledge, proving the whole chain is reachable through HTTP
        answer = nimble_parse(nimble_request("who is steve jobs"))
        if not answer or "Apple" not in answer:
            failures.append(f"general-knowledge question failed: {answer!r}")

        # arithmetic, the local exact path
        answer = nimble_parse(nimble_request("what is 2+2"))
        if not answer or "4" not in answer:
            failures.append(f"arithmetic failed: {answer!r}")

        # the contract that matters for a pluggable engine: a decline must
        # read as UNKNOWN so Nimble falls through instead of rendering a
        # refusal sentence as though it were the answer
        if nimble_parse(nimble_request("asdkjfhaskdjfh")) is not None:
            failures.append("a decline did not surface as UNKNOWN")
    finally:
        proc.terminate()
        proc.wait(timeout=10)

    for f in failures:
        print(f"[FAIL] {f}")
    if failures:
        print(f"\n{len(failures)} Nimble integration check(s) failed")
        return 1
    print("Nimble integration OK: models, project Q, general Q, arithmetic, UNKNOWN fallback")
    return 0


if __name__ == "__main__":
    sys.exit(main())
