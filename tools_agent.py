"""Her hands for multi-step work: a local model drives her tools, one call at a time, until it can answer.
Split out of tools.py (law 8, file size); tools.py re-exports agent, so nothing that imports it changes."""
import json
import re
import urllib.request


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
