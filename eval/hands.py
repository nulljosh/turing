"""Can a small model pick Samantha's tool on its own?

Scores a tool-picker on two sets. hands-data/test.jsonl is phrasings, names
and polite wrappers that never appear in training. eval/actions.py CASES were
written by hand before any of this existed. A right answer is the right tool
and the right argument. A command sent to the wrong tool is the dangerous
kind of wrong, so it is counted apart from a command that was declined.

Run: ./.venv/bin/python eval/hands.py [--adapter hands-adapter] [--model ID] [--verbose] [--min N]
     [--dump PATH] [--rescore PATH...]
     --model takes any MLX model. Without an adapter the tool list rides in the prompt, unless --trained says the model already learned the short prompt (a merged model from training/kaggle_train.py).
     --test PATH scores a held-out jsonl of {"text", "tool", "arg_hint"} rows instead of the
     usual hands-data/actions/questions mix, as a single "heldout" group. Matching is loose
     (arg_hint just has to appear in what the model said), since these phrasings were written
     by hand and were never fitted to any tool's exact argument format.
     --dump PATH: append one JSONL line per case with: group, text, wanted tool, wanted arg, exact, picked tool, picked arg (before repair).
     --rescore PATH...: skip model loading, read cached picks from PATH(s), and re-score against current guard rules.
"""
import json
import os
import re
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "app"))
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


def test_file_cases(path):
    """Gather test cases from an external held-out jsonl of {text, tool, arg_hint} rows."""
    out = []
    for line in open(path):
        row = json.loads(line)
        out.append(("heldout", row["text"], row.get("tool"), row.get("arg_hint", ""), False))
    return out


PREFILL = '{"tool": '
_POINTS = re.compile(r"\b(?:this|that|these|those)\b")


def score_picks(picks, verbose=False):
    """Score a list of picks (from model or cached) against guard rules.
    Returns: score dict, wrong_tool count, fired count, blocked count, asked count, and a dict of the v5 bar's
    counts: right (right tool picks), named_asked (asked although the sentence names the target) and wrong_asked
    (a wrong pick that draws a question).
    A pick is (group, text, wanted_tool, wanted_arg, exact, picked_tool, picked_arg_before_repair).
    """
    score, wrong_tool, fired, blocked, asked = {}, 0, 0, 0, 0
    bar = {"right": 0, "named_asked": 0, "points_asked": 0, "points_refused": 0, "wrong_asked": 0}
    for group, text, tool, arg, exact, picked_tool, picked_arg_raw, *rest in picks:
        sure = rest[0] if rest else None  # how sure she was of the tool name; dumps carry it, the 0.5B and GGUF have none
        hint = (arg or "").lower()
        # Repair the argument (same as the model evaluation does)
        picked_arg = tools.repair(picked_tool, picked_arg_raw, text) if picked_tool else ""
        picked_arg_cmp = str(picked_arg or "").lower().strip()
        if tool == "timer" and picked_tool == "timer":
            picked_arg_cmp, arg = str(tools.duration(picked_arg_cmp)), str(tools.duration(arg))
        ok = picked_tool == tool and (picked_arg_cmp == (arg or "").lower() if exact else (arg or "").lower() in picked_arg_cmp)
        n = score.setdefault(group, [0, 0])
        n[0] += ok
        n[1] += 1
        # The other half of the guard's job: a RIGHT pick it refuses is a command she cannot do.
        bar["right"] += bool(ok and tool and tool != "agent")
        if ok and tool and tool != "agent" and not tools._sound(picked_tool, picked_arg, text, sure):  # the repaired argument, as the live picker checks it
            if tools.needs_target(picked_tool, picked_arg, text):
                asked += 1
                if hint and hint in text.lower():  # the bar: a question counts when the sentence names its target, never when it only points
                    bar["points_asked" if points(text) else "named_asked"] += 1
                continue
            blocked += 1
            bar["points_refused"] += points(text)
            if verbose:
                print(f"  BLOCKED [{group}] {text[:80]!r}: right pick {tool}({picked_arg!r}) refused by the guard")
        if not ok:
            wrong_tool += bool(picked_tool) and picked_tool != tool
            # what tools.do() would really run: a wrong pick that is also unsound never fires
            fired += bool(picked_tool) and picked_tool not in (tool, "agent") and tools._sound(picked_tool, picked_arg, text, sure)
            bar["wrong_asked"] += bool(picked_tool) and picked_tool not in (tool, "agent") and bool(tools.needs_target(picked_tool, picked_arg, text))
            if verbose and picked_tool != tool:
                print(f"  PAST [{group}] {text[:80]!r}: picked {picked_tool}({picked_arg_raw!r}), want {tool}({arg!r})")
    return score, wrong_tool, fired, blocked, asked, bar


def points(text):
    """True when the sentence only points at its target: it says this, that, these or those outside quotes
    ("convert this to jpg"). Kept here, apart from the guard's own rules, so a guard edit cannot move the count."""
    t = text.lower()
    if re.search(r"~/|/\w|\b[\w-]+\.[a-z0-9]{2,4}\b", t):
        return False  # a path or a file name names the target, whatever else the sentence points at (the guard's own test)
    return bool(_POINTS.search(re.sub(r"\"[^\"]*\"|(?<!\w)'[^']*'(?!\w)|\u201c[^\u201d]*\u201d|\u2018[^\u2019]*\u2019", " ", t)))


def print_bar(blocked, bar):
    """The v5 bar on its own line, ahead of the summary line that gate.sh and picker_round.sh read with tail -1.
    Not done is refused, or asked although the sentence names its target. A question on a sentence that only
    points is the right answer; it is printed beside the count and never hidden."""
    done = blocked + bar["named_asked"]
    pct = 100 * done / bar["right"] if bar["right"] else 0
    loose = 100 * (done + bar["points_asked"]) / bar["right"] if bar["right"] else 0
    print(f"not done: {done} of {bar['right']} right tool picks ({pct:.1f} percent): {blocked} refused "
          f"({bar['points_refused']} on a sentence that only points), {bar['named_asked']} asked though the sentence names it. "
          f"{bar['points_asked']} more asked on a sentence that only points ({loose:.1f} percent with those). "
          f"{bar['wrong_asked']} wrong picks drew a question")


def main():
    """Evaluate the model's tool-picking accuracy against test cases."""
    # Check if we're rescoring cached picks instead of running the model
    rescore_paths = []
    for i, arg in enumerate(sys.argv[1:]):
        if arg == "--rescore":
            rescore_paths = sys.argv[i + 2:]
            break

    if rescore_paths:
        # Rescore mode: read cached picks and re-score
        all_picks = []
        for path in rescore_paths:
            with open(path) as f:
                for line in f:
                    row = json.loads(line)
                    all_picks.append((row["group"], row["text"], row["wanted_tool"], row["wanted_arg"],
                                      row["exact"], row["picked_tool"], row["picked_arg_raw"], row.get("sure")))
        verbose = "--verbose" in sys.argv
        score, wrong_tool, fired, blocked, asked, bar = score_picks(all_picks, verbose=verbose)
        total = sum(n[0] for n in score.values())
        for group, (p, n) in score.items():
            print(f"{group}: {p}/{n}")
        print_bar(blocked, bar)
        print(f"{total}/{sum(n[1] for n in score.values())} passed, {wrong_tool} picked the wrong tool, {fired} of those get past the guard in tools.do(), {blocked} right picks refused by the guard, {asked} asked which")
        return

    # Normal mode: run the model
    from mlx_lm import load, generate
    adapter, model_id = _flag("--adapter"), _flag("--model", BASE)
    model, tok = load(model_id, adapter_path=os.path.join(REPO, adapter) if adapter else None)
    system = SYSTEM if (adapter or "--trained" in sys.argv) else untrained_system()  # --trained: a fully merged model that learned the short prompt
    constrain = "--constrain" in sys.argv
    tool_names = list(tools.TOOLS.keys()) if constrain else None
    verbose = "--verbose" in sys.argv
    dump_path = _flag("--dump")
    dump_file = open(dump_path, "a") if dump_path else None

    test_path = _flag("--test")
    case_list = test_file_cases(os.path.join(REPO, test_path)) if test_path else cases()

    # Collect all picks first so we can dump them
    picks = []
    t0 = time.time()
    for group, text, tool, arg, exact in case_list:
        sure = 1.0
        prompt = tok.apply_chat_template([{"role": "system", "content": system}, {"role": "user", "content": text}],
                                         add_generation_prompt=True, tokenize=False, enable_thinking=False)
        if constrain:
            from constrain import ToolNameConstraint
            proc = ToolNameConstraint(tok, tool_names)
            raw = PREFILL + generate(model, tok, prompt=prompt + PREFILL, max_tokens=48, verbose=False,
                                      logits_processors=[proc])
        else:  # the same call the live picker makes, so the dump can carry how sure she was of the tool name
            import math
            import tools_agent
            from mlx_lm import stream_generate
            pieces = [(r.text, math.exp(float(r.logprobs[r.token]))) for r in stream_generate(model, tok, prompt=prompt, max_tokens=48)]
            raw, sure = "".join(p for p, _ in pieces), tools_agent._tool_confidence(pieces)
        found = re.search(r"\{.*?\}", re.sub(r"(?s)<think>.*?</think>", "", raw), re.S)
        try:
            got = json.loads(found.group(0)) if found else {}
        except ValueError:
            got = {}
        picked_tool = got.get("tool")
        picked_arg_raw = str(got.get("arg") or "").strip()
        picks.append((group, text, tool, arg, exact, picked_tool, picked_arg_raw, sure if "--trained" in sys.argv else None))

        if dump_file:
            dump_file.write(json.dumps({"group": group, "text": text, "wanted_tool": tool, "wanted_arg": arg,
                                        "exact": exact, "picked_tool": picked_tool, "picked_arg_raw": picked_arg_raw, "sure": round(sure, 4)}) + "\n")
            dump_file.flush()

    if dump_file:
        dump_file.close()

    # Now score all picks
    score, wrong_tool, fired, blocked, asked, bar = score_picks(picks, verbose=verbose)

    total = sum(n[0] for n in score.values())
    for group, (p, n) in score.items():
        print(f"{group}: {p}/{n}")
    print_bar(blocked, bar)
    tag = (adapter or model_id) + (" constrained" if constrain else "")
    print(f"{total}/{sum(n[1] for n in score.values())} passed, {wrong_tool} picked the wrong tool, {fired} of those get past the guard in tools.do(), {blocked} right picks refused by the guard, {asked} asked which, {time.time() - t0:.0f}s, {tag}")
    minimum = _flag("--min")
    if minimum and total < int(minimum):
        sys.exit(1)


if __name__ == "__main__":
    main()
