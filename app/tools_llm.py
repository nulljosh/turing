"""Samantha asks another LLM: for the questions a 0.5B model cannot think through, she hands them to a bigger model
running on this Mac. Name one ("ask qwen ...", "ask llama ...", "ask gemma ...") and she finds it on oMLX (:8000) or
Ollama (:11434); say "ask claude", "ask gpt" or "ask an llm" and she uses the biggest one, oMLX's Qwen3.5-9B first,
then Ollama's qwen3:8b. Nothing leaves the Mac and no API key is needed. Only by name, and every answer names the model.

SAMANTHA_BIG_MODEL and SAMANTHA_OLLAMA_MODEL pick the default models.
"""
import json
import os
import re
import urllib.error
import urllib.request

OMLX = "http://localhost:8000"
OLLAMA = "http://localhost:11434"
OMLX_CHAT = OMLX + "/v1/chat/completions"
OLLAMA_CHAT = OLLAMA + "/api/chat"
MODEL = os.environ.get("SAMANTHA_BIG_MODEL", "Qwen3.5-9B-OptiQ-4bit")
OLLAMA_MODEL = os.environ.get("SAMANTHA_OLLAMA_MODEL", "qwen3:8b")
LIMIT = 20000  # characters; a longer question is refused, never silently cut
# names that mean "whichever big model you have": frontier names she cannot reach, so the biggest local one answers
ANY = re.compile(r"^(?:claude|chatgpt|gpt[\w.-]*|gemini|(?:an? |the )?(?:llm|ai|(?:bigger|big) model))$", re.I)
# every name the route takes, shared with the empty-ask route in tools.py and mirrored in web/samantha.js
NAMES = (r"claude|chatgpt|gpt(?:-?\d[\w.]*)?|gemini|(?:an? |the )?(?:llm|(?:bigger|big) model)"
         r"|qwen[\w.:-]*|llama[\w.:-]*|mistral[\w.:-]*|gemma[\w.:-]*|phi[\w.:-]*|deepseek[\w.:-]*")
SYSTEM = ("You are answering one question for Samantha, a small assistant that runs on her user's Mac and asked you because "
          "the question needs more than she can do. Answer in plain language and briefly: a few sentences unless the question "
          "truly needs more. No markdown headers. If you are not sure, say so instead of guessing.")


def _post(url, body):
    """POST JSON to a local server and return the parsed reply. A cold model can take minutes to load."""
    req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.load(r)


def _get(url):
    """GET JSON from a local server, or None when it is not running."""
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            return json.load(r)
    except (urllib.error.URLError, OSError, ValueError):
        return None


def _ask_omlx(messages, model):
    """oMLX's OpenAI-style chat: (text, cut)."""
    reply = _post(OMLX_CHAT, {"model": model, "max_tokens": 2000, "messages": messages,
                              "chat_template_kwargs": {"enable_thinking": False}})
    choice = reply["choices"][0]
    return choice["message"].get("content") or "", choice.get("finish_reason") == "length"


def _ask_ollama(messages, model):
    """Ollama's chat: (text, cut)."""
    reply = _post(OLLAMA_CHAT, {"model": model, "stream": False, "think": False, "messages": messages})
    return reply.get("message", {}).get("content", ""), reply.get("done_reason") == "length"


def installed():
    """Every model the local servers offer, as (ask function, model id), oMLX first."""
    omlx = (_get(OMLX + "/v1/models") or {}).get("data") or []
    ollama = (_get(OLLAMA + "/api/tags") or {}).get("models") or []
    return [(_ask_omlx, m["id"]) for m in omlx if "id" in m] + [(_ask_ollama, m["name"]) for m in ollama if "name" in m]


def ask_llm(request):
    """Ask another LLM on this Mac a question too hard for her. Takes 'name<TAB>question' (or just a question) and
    returns the answer marked with the model that gave it. A named model (qwen, llama, gemma...) is found on oMLX or
    Ollama; claude, gpt or "an llm" means the biggest one here. Nothing leaves the Mac."""
    name, _, q = request.partition("\t") if "\t" in request else ("", "", request)
    name, q = name.strip(), q.strip()
    if not q:
        return 'Ask what? Say it like "ask qwen why the sky is blue".'
    if len(q) > LIMIT:
        return f"That is too long to send in one go: {len(q):,} characters, and the limit is {LIMIT:,}. Ask about one part at a time."
    if not name or ANY.match(name):
        tries = [(_ask_omlx, MODEL), (_ask_ollama, OLLAMA_MODEL)]
    else:
        models = installed()
        tries = [(ask, m) for ask, m in models if name.lower() in m.lower()]
        if not tries:
            here = ", ".join(sorted({m for _, m in models if "embed" not in m.lower()}))
            return f"I do not have a {name} model on this Mac." + (f" Running here: {here}." if here else " Start oMLX or Ollama first.")
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": q}]
    why = "I could not reach a local model. Start oMLX or Ollama, then ask again."
    for ask, model in tries:
        try:
            text, cut = ask(messages, model)
        except urllib.error.HTTPError as e:
            why = f"The local model could not answer just now (error {e.code}). Try again later."
            if e.code == 404 and ask is _ask_ollama:
                why = f"The model {model} is not on this Mac yet: run ollama pull {model}, then ask again."
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
