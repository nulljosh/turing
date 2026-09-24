"""Can a small model pick Samantha's tool on its own?

Scores a tool-picker on two sets. hands-data/test.jsonl is phrasings, names
and polite wrappers that never appear in training. eval/actions.py CASES were
written by hand before any of this existed. A right answer is the right tool
and the right argument. A command sent to the wrong tool is the dangerous
kind of wrong, so it is counted apart from a command that was declined.

Run: ./.venv/bin/python eval/hands.py [--adapter hands-adapter] [--model ID] [--verbose] [--min N]
     --model takes any MLX model. Without an adapter the tool list rides in the prompt.
"""
import json
import os
import re
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "eval"))
sys.path.insert(0, os.path.join(REPO, "training"))
os.environ["SAMANTHA_HEADLESS"] = "1"
import tools
from gen_hands_data import SYSTEM

BASE = "mlx-community/Qwen2.5-0.5B-Instruct-4bit"


def _flag(name, default=None):
    """Extract a command-line flag value from sys.argv."""
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def untrained_system():
    """A model that was never trained on the format needs the tools spelled out."""
    lines = [f"- {n}: {f.__doc__}" for n, f in tools.TOOLS.items() if n != "read_page"]
    return ("You pick one tool for a command on Joshua's Mac. Tools:\n" + "\n".join(lines) +
            "\n- agent: the request needs more than one step, or needs a web page read and explained\n"
            'Reply with JSON only: {"tool": "<name>", "arg": "<one string, words copied from the command, or empty>"}. '
            'set_volume takes a number, "up" or "down". timer takes the duration as spoken. '
            'A question or small talk is not a command: reply {"tool": null, "arg": ""}.')


def cases():
    """Gather test cases from hands-data, actions, and questions."""
    out = []
    for line in open(os.path.join(REPO, "hands-data", "test.jsonl")):
        m = json.loads(line)["messages"]
        want = json.loads(m[2]["content"])
        out.append(("unseen", m[1]["content"], want["tool"], want["arg"], True))
    from actions import CASES
    for cmd, tool, arg in CASES:
        # actions.py says None for multi-step too, because act() leaves those to agent()
        if tool is None and (tools._MULTISTEP.search(cmd) or " then " in cmd):
            tool = "agent"
        out.append(("actions", cmd, tool, arg, False))
    # do() shows her every message, so every real question and every writing task must come back "not a command"
    from basic_questions import CASES as QUESTIONS
    for q, _ in QUESTIONS:
        out.append(("questions", q, None, "", True))
    for line in open(os.path.join(REPO, "eval", "prompts.jsonl")):
        prompt = json.loads(line).get("prompt")
        if prompt:
            out.append(("questions", prompt, None, "", True))
    return out


PREFILL = '{"tool": '


def main():
    """Evaluate the model's tool-picking accuracy against test cases."""
    from mlx_lm import load, generate
    adapter, model_id = _flag("--adapter"), _flag("--model", BASE)
    model, tok = load(model_id, adapter_path=os.path.join(REPO, adapter) if adapter else None)
    system = SYSTEM if adapter else untrained_system()
    constrain = "--constrain" in sys.argv
    tool_names = list(tools.TOOLS.keys()) if constrain else None
    verbose, score, wrong_tool, fired, blocked, t0 = "--verbose" in sys.argv, {}, 0, 0, 0, time.time()
    for group, text, tool, arg, exact in cases():
        prompt = tok.apply_chat_template([{"role": "system", "content": system}, {"role": "user", "content": text}],
                                         add_generation_prompt=True, tokenize=False, enable_thinking=False)
        if constrain:
            from constrain import ToolNameConstraint
            proc = ToolNameConstraint(tok, tool_names)
            raw = PREFILL + generate(model, tok, prompt=prompt + PREFILL, max_tokens=48, verbose=False,
                                      logits_processors=[proc])
        else:
            raw = generate(model, tok, prompt=prompt, max_tokens=48, verbose=False)
        found = re.search(r"\{.*?\}", re.sub(r"(?s)<think>.*?</think>", "", raw), re.S)
        try:
            got = json.loads(found.group(0)) if found else {}
        except ValueError:
            got = {}
        got_arg = str(got.get("arg") or "").lower().strip()
        if tool == "timer" and got.get("tool") == "timer":
            got_arg, arg = str(tools.duration(got_arg)), str(tools.duration(arg))
        ok = got.get("tool", "?") == tool and (got_arg == (arg or "").lower() if exact else (arg or "").lower() in got_arg)
        n = score.setdefault(group, [0, 0])
        n[0] += ok
        n[1] += 1
        # The other half of the guard's job: a RIGHT pick it refuses is a command she cannot do.
        if ok and tool and tool != "agent" and not tools._sound(tool, str(got.get("arg") or "").strip(), text):
            blocked += 1
            if verbose:
                print(f"  BLOCKED [{group}] {text!r}: right pick {tool}({got.get('arg')!r}) refused by the guard")
        if not ok:
            wrong_tool += bool(got.get("tool")) and got.get("tool") != tool
            # what tools.do() would really run: a wrong pick that is also unsound never fires
            fired += bool(got.get("tool")) and got.get("tool") not in (tool, "agent") and tools._sound(got["tool"], str(got.get("arg") or "").strip(), text)
            if verbose:
                print(f"  MISS [{group}] {text!r}: want {tool}({arg!r}) got {raw.strip()[:70]!r}")
    total = sum(n[0] for n in score.values())
    for group, (p, n) in score.items():
        print(f"{group}: {p}/{n}")
    tag = (adapter or model_id) + (" constrained" if constrain else "")
    print(f"{total}/{sum(n[1] for n in score.values())} passed, {wrong_tool} picked the wrong tool, {fired} of those get past the guard in tools.do(), {blocked} right picks refused by the guard, {time.time() - t0:.0f}s, {tag}")
    minimum = _flag("--min")
    if minimum and total < int(minimum):
        sys.exit(1)


if __name__ == "__main__":
    main()
