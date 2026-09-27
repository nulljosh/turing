"""How fast Samantha is, in numbers the landing page and WHITEPAPER can quote:
the regex router in microseconds, her tool picker per query, and her answer
model in tokens per second. Accuracy lives in eval/actions.py and eval/hands.py;
this is only speed. The two model rows skip with a reason when MLX or the
adapters are not here, so CI still runs the router row and stays green.

Run: python3 eval/bench.py [--json eval/bench.json] [--rounds N]
"""
import json
import os
import statistics
import sys
import time

os.environ["SAMANTHA_HEADLESS"] = "1"
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from actions import CASES  # the same commands the accuracy check uses, so the two numbers describe the same work

PICK_SAMPLE = 20  # ponytail: a fixed slice of CASES, the full set takes minutes on the picker
ANSWER_PROMPTS = ["What is Turing?", "Who is Samantha?", "How does the gate work?"]


def _timed(fn, rounds):
    """Median seconds per call of fn over rounds."""
    took = []
    for _ in range(rounds):
        t = time.perf_counter()
        fn()
        took.append(time.perf_counter() - t)
    return statistics.median(took)


def bench_router(rounds):
    """Median microseconds for act() to route one command, every tool mocked."""
    import tools
    originals = {n: getattr(tools, n) for n in tools.TOOLS}
    for n in tools.TOOLS:
        setattr(tools, n, lambda *a, **k: "")
    try:
        per = _timed(lambda: [tools.act(c) for c, _, _ in CASES], rounds) / len(CASES)
    finally:
        for n, fn in originals.items():
            setattr(tools, n, fn)
    return {"router_us": round(per * 1e6, 1), "router_cases": len(CASES)}


def bench_picker():
    """Median milliseconds for pick() on one query, first load excluded. None when no backend."""
    import tools_agent
    queries = [c for c, _, _ in CASES[:PICK_SAMPLE]]
    tools_agent.pick(queries[0])
    if not tools_agent._hands:
        return None
    ms = [_timed(lambda q=q: tools_agent.pick(q), 1) * 1e3 for q in queries]
    return {"pick_ms": round(statistics.median(ms), 1), "pick_backend": tools_agent._hands_backend, "pick_queries": len(queries)}


def bench_answer():
    """Her answer model: median tokens per second over ANSWER_PROMPTS, after a warm-up. None when MLX is not here."""
    import chat
    try:
        chat._model()
    except OSError:
        return None
    _, tok = chat._answerer
    chat.generate(ANSWER_PROMPTS[0], max_tokens=16)
    rates = []
    for p in ANSWER_PROMPTS:
        t = time.perf_counter()
        text = chat.generate(p, max_tokens=64)
        rates.append(len(tok.encode(text)) / (time.perf_counter() - t))
    return {"answer_tok_s": round(statistics.median(rates), 1), "answer_prompts": len(ANSWER_PROMPTS)}


def main(argv):
    """Run every row, print one line, optionally write it as JSON."""
    rounds = int(argv[argv.index("--rounds") + 1]) if "--rounds" in argv else 5
    out = {"machine": os.uname().machine, "python": sys.version.split()[0]}
    out.update(bench_router(rounds))
    for name, fn in (("picker", bench_picker), ("answer", bench_answer)):
        got = fn()
        if got:
            out.update(got)
        else:
            out[name + "_skipped"] = "no model on this machine"
    if "--json" in argv:
        with open(argv[argv.index("--json") + 1], "w") as f:
            json.dump(out, f, indent=2)
            f.write("\n")
    print(" · ".join(f"{k} {v}" for k, v in out.items()))
    return out


if __name__ == "__main__":
    got = main(sys.argv[1:])
    assert 0 < got["router_us"] < 5000, got  # the router is regex, sub-millisecond or something broke
