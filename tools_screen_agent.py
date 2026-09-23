"""Multi-step screen work: "log me into X", "walk me through checkout" plan a sequence of clicks, typed text and key
presses through a local model. This is deliberately its own agent, not tools_agent.agent(): those tools (click_text,
type_text, press_key, see_screen) are in NOT_FOR_MODELS on purpose, so no model reaches them just because it thinks a
task calls for it. This one only starts when the sentence names a screen job explicitly, and unlike the general
agent, EVERY step is confirmed before it runs, even a read (see_screen), not just the writes: a plan she cannot
show you first is not a plan you can trust. Her eyes (see_screen) let her find icons that have no text to click.
"""
import json
import re
import urllib.error
import urllib.request

MODEL = "qwen3:1.7b"  # same as tools.agent: fast enough to plan a few clicks, no need for the 8B here
OLLAMA_CHAT = "http://localhost:11434/api/chat"
MAX_STEPS = 10
SYSTEM = ("You control the screen for one job the user asked for by name, step by step. Use see_screen first if you "
          "are not sure what is on screen. Use click_text to click words you can read, type_text to type, press_key "
          "for return/tab/escape/arrows. One tool call at a time. Stop and answer in plain words once the job is "
          "done, blocked (say what you see and why), or you are repeating yourself.")


def _tools():
    """Her screen tools, by name: only what this agent may ever touch, never the general model_tools() list."""
    import tools
    import tools_gui
    import tools_see
    return {"click_text": tools_gui.click_text, "type_text": tools_gui.type_text,
            "press_key": tools_gui.press_key, "see_screen": tools_see.see_screen}


def _schema(fn):
    """OpenAI-style tool schema from a function's signature and docstring, same shape as tools._schema."""
    args = fn.__code__.co_varnames[:fn.__code__.co_argcount]
    return {"type": "function", "function": {"name": fn.__name__, "description": fn.__doc__,
            "parameters": {"type": "object", "properties": {a: {"type": "string"} for a in args}, "required": list(args)}}}


def screen_task(task, max_steps=MAX_STEPS, log=None, confirm=None):
    """Plan and run a multi-step screen job ("log me into X") with a local model. Every step, even a look at the
    screen, is confirmed before it runs: confirm(name, args) -> bool. A no ends the job at once. Returns what
    happened, in plain words, or why it stopped early."""
    tools_by_name = _tools()
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": task}]
    for _ in range(max_steps):
        body = json.dumps({"model": MODEL, "messages": messages, "stream": False, "think": False,
                           "tools": [_schema(f) for f in tools_by_name.values()]}).encode()
        req = urllib.request.Request(OLLAMA_CHAT, body, {"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                msg = json.load(r)["message"]
        except (urllib.error.URLError, OSError) as e:
            return f"My hands need Ollama running with {MODEL}, and it didn't answer: {e}"
        messages.append(msg)
        calls = msg.get("tool_calls") or []
        if not calls:
            return re.sub(r"(?s)<think>.*?</think>", "", msg.get("content", "")).strip() or "I stopped there."
        for c in calls:
            name, args = c["function"]["name"], c["function"].get("arguments") or {}
            fn = tools_by_name.get(name)
            if not fn:
                result = f"No tool named {name}."
            elif confirm and not confirm(name, tuple(map(str, args.values()))):
                return "Okay, I stopped there."  # a no ends the whole job, not just that step
            else:
                takes = fn.__code__.co_varnames[:fn.__code__.co_argcount]
                try:
                    result = fn(**{k: v for k, v in args.items() if k in takes})
                except Exception as e:
                    result = f"{name} failed: {e}"
            if log:
                log(f"  [{name}({', '.join(map(str, args.values()))})]")
            messages.append({"role": "tool", "tool_name": name, "content": str(result)})
    return "I ran out of steps before finishing that. Here is where things stand: " + (messages[-1].get("content") or "")
