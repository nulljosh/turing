"""Samantha asks a bigger model: for the questions a 0.5B model cannot think through, she hands them to the biggest
model running on this Mac. First oMLX (OpenAI-style server on :8000, Qwen3.5-9B by default), then Ollama (qwen3:8b).
Nothing leaves the Mac and no API key is needed. It still answers to "ask claude ..." so old habits and the picker keep
working, it runs only when named, and every answer says which model gave it.

SAMANTHA_BIG_MODEL and SAMANTHA_OLLAMA_MODEL pick other models.
"""
import json
import os
import re
import urllib.error
import urllib.request

OMLX_CHAT = "http://localhost:8000/v1/chat/completions"
OLLAMA_CHAT = "http://localhost:11434/api/chat"
MODEL = os.environ.get("SAMANTHA_BIG_MODEL", "Qwen3.5-9B-OptiQ-4bit")
OLLAMA_MODEL = os.environ.get("SAMANTHA_OLLAMA_MODEL", "qwen3:8b")
LIMIT = 20000  # characters; a longer question is refused, never silently cut
SYSTEM = ("You are answering one question for Samantha, a small assistant that runs on her user's Mac and asked you because "
          "the question needs more than she can do. Answer in plain language and briefly: a few sentences unless the question "
          "truly needs more. No markdown headers. If you are not sure, say so instead of guessing.")


def _post(url, body):
    """POST JSON to a local server and return the parsed reply. A cold model can take minutes to load."""
    req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.load(r)


def _ask_omlx(messages):
    """oMLX's OpenAI-style chat: (text, cut, model)."""
    reply = _post(OMLX_CHAT, {"model": MODEL, "max_tokens": 2000, "messages": messages,
                              "chat_template_kwargs": {"enable_thinking": False}})
    choice = reply["choices"][0]
    return choice["message"].get("content") or "", choice.get("finish_reason") == "length", MODEL


def _ask_ollama(messages):
    """Ollama's chat: (text, cut, model)."""
    reply = _post(OLLAMA_CHAT, {"model": OLLAMA_MODEL, "stream": False, "think": False, "messages": messages})
    return reply.get("message", {}).get("content", ""), reply.get("done_reason") == "length", OLLAMA_MODEL


def ask_claude(question):
    """Ask the biggest local model a question too hard for her and return its answer, marked as its own.
    Stays on this Mac: oMLX first, then Ollama. Answers to "ask claude ..." by name."""
    q = question.strip()
    if not q:
        return 'Ask what? Say it like "ask claude why the sky is blue".'
    if len(q) > LIMIT:
        return f"That is too long to send in one go: {len(q):,} characters, and the limit is {LIMIT:,}. Ask about one part at a time."
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": q}]
    why = "I could not reach a local model. Start oMLX or Ollama, then ask again."
    for ask in (_ask_omlx, _ask_ollama):
        try:
            text, cut, model = ask(messages)
        except urllib.error.HTTPError as e:
            why = f"The local model could not answer just now (error {e.code}). Try again later."
            if e.code == 404 and ask is _ask_ollama:
                why = f"The model {OLLAMA_MODEL} is not on this Mac yet: run ollama pull {OLLAMA_MODEL}, then ask again."
            continue
        except TimeoutError:  # a cold model can take minutes to load; the next ask finds it warm
            return "The local model is still loading (the first ask after a while can take minutes). Ask again in a minute."
        except (urllib.error.URLError, OSError, KeyError, IndexError, ValueError):
            continue
        text = re.sub(r"(?s)<think>.*?</think>", "", text).strip()
        if not text:
            return f"{model} sent back no answer."
        return f"{text}{' (It hit its length limit, so this is cut short.)' if cut else ''}\n(Answered by {model} on this Mac, not by me.)"
    return why
