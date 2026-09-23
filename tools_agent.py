"""Her hands' choices: pick() is her own 0.5B tool picker, _faq_knows() keeps questions about her away from it, and
agent() lets a local model drive her tools one call at a time for multi-step work. Split out of tools.py (law 8, file
size); tools.py re-exports all of it, so nothing that imports it changes."""
import json
import os
import re
import urllib.request

HANDS_ADAPTER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hands-adapter")
HANDS_SYSTEM = 'You are Samantha\'s hands. Reply with one JSON tool call. If this is not a command, reply {"tool": null, "arg": ""}.'
_hands = None



def agent(task, max_steps=6, log=None, confirm=None):
    """Multi-step: let qwen3:8b drive TOOLS until it has an answer. None when it answers without using a tool."""
    import tools  # here, not at the top: tools.py imports this module as it loads
    messages = [
        {"role": "system", "content": "You are Samantha, acting on Joshua's Mac through tools. Do what is asked in as few tool calls as possible, then answer in two or three plain sentences. Never invent page contents, read the page first."},
        {"role": "user", "content": task},
    ]
    # A small model asked to "poke around hacker news" opens a search and then
    # invents three stories. Same lesson as the rest of this project: the
    # harness retrieves, the model only reads. If the task names a page, it is
    # already fetched before the model says a word.
    named = tools._named_page(task)
    if named:
        if log:
            log(f"  [tools.read_page({named})]")
        messages[1]["content"] += f"\n\nI already fetched {named} for you. Its text:\n{tools.read_page(named)}"
    acted = bool(named)
    for _ in range(max_steps):
        body = json.dumps({"model": tools.AGENT_MODEL, "messages": messages, "stream": False, "think": False,
                           "tools": [tools._schema(f) for f in tools.model_tools().values()]}).encode()
        req = urllib.request.Request(tools.OLLAMA_CHAT, body, {"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                msg = json.load(r)["message"]
        except Exception as e:
            return f"My hands need Ollama running with {tools.AGENT_MODEL}, and it didn't answer: {e}"
        messages.append(msg)
        calls = msg.get("tool_calls") or []
        if not calls:
            # An answer with no tool and no page behind it is the model guessing: score.py caught it inventing
            # where the loss chart's data comes from and printing a half-written tool call as the reply. None
            # hands the question back to the answer chain, which looks things up instead.
            return re.sub(r"(?s)<think>.*?</think>", "", msg.get("content", "")).strip() if acted else None
        acted = True
        for c in calls:
            name, args = c["function"]["name"], c["function"].get("arguments") or {}
            fn = tools.model_tools().get(name)
            try:
                if not fn:
                    result = f"No tool named {name}."
                elif confirm and name in tools.WRITES and not confirm(name, tuple(map(str, args.values()))):
                    result = "The user said no."
                else:
                    takes = fn.__code__.co_varnames[:fn.__code__.co_argcount]
                    args = {k: v for k, v in args.items() if k in takes}
                    result = fn(**args)
            except Exception as e:
                result = f"{name} failed: {e}"
            if log:
                log(f"  [{name}({', '.join(map(str, args.values()))})]")
            messages.append({"role": "tool", "tool_name": name, "content": str(result)})
    return "I ran out of steps before finishing that."


def pick(query):
    """Her own head for tool picking: the 0.5B with hands-adapter, trained by
    gen_hands_data.py, scored by eval/hands.py. Returns (tool, arg), ("agent",
    ""), or None when it is not a command, the pick is unsound, or the adapter
    or MLX is not here. None always means: carry on as if she had not looked."""
    global _hands
    import tools  # here, not at the top: tools.py imports this module as it loads
    if _hands is None:
        try:
            from mlx_lm import load
            _hands = load("mlx-community/Qwen2.5-0.5B-Instruct-4bit", adapter_path=HANDS_ADAPTER) if os.path.isdir(HANDS_ADAPTER) else False
        except Exception:
            _hands = False
    if not _hands:
        return None
    from mlx_lm import generate
    model, tok = _hands
    prompt = tok.apply_chat_template([{"role": "system", "content": HANDS_SYSTEM}, {"role": "user", "content": query}],
                                     add_generation_prompt=True, tokenize=False)
    try:
        got = json.loads(re.search(r"\{.*?\}", generate(model, tok, prompt=prompt, max_tokens=48, verbose=False), re.S).group(0))
        tool, arg = got.get("tool"), str(got.get("arg") or "").strip()
    except Exception:
        return None
    if tool == "agent":
        return "agent", ""
    return (tool, arg) if tool and tools._sound(tool, arg, query) else None


def _faq_knows(query):
    """True when her FAQ answers this: "how much memory does it use" is about her, and the picker once handed it to
    memory_usage, which reported the Mac's RAM. Exact routes run before this; only the picker and agent yield."""
    try:
        import ask
        return bool(ask.faq_match(query))
    except Exception:
        return False
