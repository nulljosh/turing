"""Samantha asks a bigger model: for the questions a 0.5B model cannot think through, she hands them to the largest model
Ollama has on this Mac (qwen3:8b by default). Nothing leaves the Mac and no API key is needed. It still answers to
"ask claude ..." so old habits and the picker keep working, it runs only when named, and every answer says who gave it.

Needs Ollama running with the model pulled: `ollama pull qwen3:8b`. SAMANTHA_BIG_MODEL picks another one.
"""
import json
import os
import re
import urllib.error
import urllib.request

OLLAMA_CHAT = "http://localhost:11434/api/chat"
MODEL = os.environ.get("SAMANTHA_BIG_MODEL", "qwen3:8b")
LIMIT = 20000  # characters; a longer question is refused, never silently cut
SYSTEM = ("You are answering one question for Samantha, a small assistant that runs on her user's Mac and asked you because "
          "the question needs more than she can do. Answer in plain language and briefly: a few sentences unless the question "
          "truly needs more. No markdown headers. If you are not sure, say so instead of guessing.")


def ask_claude(question):
    """Ask the biggest local model a question too hard for her and return its answer, marked as its own.
    Stays on this Mac. Answers to "ask claude ..." by name; needs Ollama running with the model pulled."""
    q = question.strip()
    if not q:
        return 'Ask what? Say it like "ask claude why the sky is blue".'
    if len(q) > LIMIT:
        return f"That is too long to send in one go: {len(q):,} characters, and the limit is {LIMIT:,}. Ask about one part at a time."
    body = json.dumps({"model": MODEL, "stream": False, "think": False, "messages": [
        {"role": "system", "content": SYSTEM}, {"role": "user", "content": q}]}).encode()
    try:
        req = urllib.request.Request(OLLAMA_CHAT, body, {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=300) as r:
            reply = json.load(r)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return f"The model {MODEL} is not on this Mac yet: run ollama pull {MODEL}, then ask again."
        return f"The local model could not answer just now (error {e.code}). Try again later."
    except (urllib.error.URLError, TimeoutError, OSError):
        return "I could not reach Ollama. Start it (open the Ollama app or run ollama serve), then ask again."
    text = re.sub(r"(?s)<think>.*?</think>", "", reply.get("message", {}).get("content", "")).strip()
    if not text:
        return f"{MODEL} sent back no answer."
    cut = " (It hit its length limit, so this is cut short.)" if reply.get("done_reason") == "length" else ""
    return f"{text}{cut}\n(Answered by {MODEL} on this Mac, not by me.)"
