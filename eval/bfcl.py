"""Does her tool-picker model make function calls the way the Berkeley Function Calling Leaderboard grades them?

Outside benchmark: the BFCL v3 `simple` split, 400 cases. Each case is one user question and one function schema
(sometimes several to pick from, always one right answer). The model gets the schema, answers with one JSON object
{"name": ..., "arguments": {...}}, and is scored the BFCL "AST" way: the function name must match, every required
argument must be present with a value in the possible-answer set, and no argument outside the answer may appear.
Values compare loosely: numbers as floats, strings case-insensitive and stripped.

The data (about 340 KB for both files) is cached under eval/data/bfcl/ and fetched once from Hugging Face.
Model calls go to the oMLX OpenAI-style endpoint on localhost:8000. --dry scores the possible answers themselves,
which must give 100 percent, so the harness can be checked without a model.

Run: python3 eval/bfcl.py [--model ID] [--limit N] [--dry]
"""
import argparse
import json
import os
import re
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "eval", "data", "bfcl")
HF_BASE = "https://huggingface.co/datasets/gorilla-llm/Berkeley-Function-Calling-Leaderboard/resolve/main/"
QUESTIONS = "BFCL_v3_simple.json"
ANSWERS = os.path.join("possible_answer", "BFCL_v3_simple.json")
ENDPOINT = "http://localhost:8000/v1/chat/completions"
DEFAULT_MODEL = "trommatic--samantha-hands-1.5b-mlx"

SYSTEM = (
    "You are a function-calling assistant. You are given functions as JSON schemas. Pick the one function "
    "that answers the user and fill its arguments from the request. Reply with exactly one JSON object and "
    'nothing else, in the form {"name": "<function name>", "arguments": {"<argument>": <value>}}.'
)


def ensure_data():
    """Make sure both BFCL files are cached locally, downloading any that are missing."""
    for name in (QUESTIONS, ANSWERS):
        path = os.path.join(DATA_DIR, name)
        if os.path.exists(path):
            continue
        os.makedirs(os.path.dirname(path), exist_ok=True)
        print(f"fetching {name} ...", file=sys.stderr)
        urllib.request.urlretrieve(HF_BASE + name, path)
    return DATA_DIR


def read_jsonl(path):
    """Read a JSON-lines file into a list of dicts, skipping blank lines."""
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load_cases():
    """Join each BFCL question with its possible answer by id, in file order."""
    ensure_data()
    questions = read_jsonl(os.path.join(DATA_DIR, QUESTIONS))
    answers = {row["id"]: row["ground_truth"] for row in read_jsonl(os.path.join(DATA_DIR, ANSWERS))}
    cases = []
    for q in questions:
        cases.append({
            "id": q["id"],
            "question": question_text(q["question"]),
            "functions": q["function"],
            "truth": answers[q["id"]],
        })
    return cases


def question_text(turns):
    """Flatten BFCL's nested message list into the user's words, joined in order."""
    messages = [m for turn in turns for m in (turn if isinstance(turn, list) else [turn])]
    return "\n".join(str(m.get("content", "")) for m in messages if m.get("role", "user") == "user")


def build_messages(question, functions):
    """Build the chat messages: the function schemas in the system turn, the user's question in the user turn."""
    schemas = "\n".join(json.dumps(fn, ensure_ascii=False) for fn in functions)
    return [
        {"role": "system", "content": SYSTEM + "\n\nFunctions:\n" + schemas},
        {"role": "user", "content": question},
    ]


def parse_call(text):
    """Pull the first JSON object out of a model reply, tolerating code fences and surrounding prose."""
    text = (text or "").strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        return None
    try:
        obj = json.loads(text[start:end + 1])
    except ValueError:
        return None
    return obj if isinstance(obj, dict) else None


def number(x):
    """Return x as a float when it is a number or a numeric string, else None. Booleans are not numbers here."""
    if isinstance(x, bool):
        return None
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, str):
        try:
            return float(x.strip())
        except ValueError:
            return None
    return None


def loose(got, want):
    """Compare two argument values the way the scorer does: numbers as floats, strings case-insensitive and stripped."""
    if isinstance(got, bool) or isinstance(want, bool):
        return got is want
    a, b = number(got), number(want)
    if a is not None and b is not None:
        return a == b
    if isinstance(got, str) and isinstance(want, str):
        return got.strip().lower() == want.strip().lower()
    if isinstance(got, list) and isinstance(want, list):
        return len(got) == len(want) and all(loose(g, w) for g, w in zip(got, want))
    if isinstance(got, dict) and isinstance(want, dict):
        return got.keys() == want.keys() and all(loose(got[k], want[k]) for k in got)
    return got == want


def score(call, truth):
    """True when a parsed call matches one of the possible answers the BFCL AST way.

    `truth` is BFCL's ground_truth list. The name must match. A parameter listed with "" among its accepted values
    is optional, so the model may leave it out; every other parameter must be present and match one of its accepted
    values. A parameter the answer never lists is a fail, as BFCL counts it.
    """
    if not isinstance(call, dict):
        return False
    args = call.get("arguments", {})
    if args is None:
        args = {}
    if not isinstance(args, dict):
        return False
    return any(match_one(call.get("name"), args, answer) for answer in truth)


def match_one(name, args, answer):
    """Check one call against one possible answer: {function name: {parameter: accepted values}}."""
    want_name, params = next(iter(answer.items()))
    if name != want_name:
        return False
    for key, accepted in params.items():
        if key not in args:
            if "" in accepted:
                continue
            return False
        if not any(loose(args[key], value) for value in accepted):
            return False
    return all(key in params for key in args)


def dry_reply(truth):
    """The first possible answer as a model reply: each parameter set to its first non-empty accepted value."""
    name, params = next(iter(truth[0].items()))
    args = {}
    for key, accepted in params.items():
        values = [v for v in accepted if v != ""]
        if values:
            args[key] = values[0]
    return json.dumps({"name": name, "arguments": args})


def call_model(model, messages, url=ENDPOINT, timeout=120):
    """POST the chat to the OpenAI-style endpoint and return the reply text. Greedy decoding, so runs repeat."""
    body = json.dumps({"model": model, "messages": messages, "temperature": 0, "max_tokens": 512}).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"] or ""


def run(model=DEFAULT_MODEL, limit=None, dry=False, caller=None, out=print):
    """Score the first `limit` cases (all when None) and return (correct, total).

    dry=True answers each case with its own possible answer instead of asking a model. `caller` is the chat function,
    call_model by default, so tests can stand in for the model.
    """
    cases = load_cases()
    if limit:
        cases = cases[:limit]
    caller = caller or call_model
    correct = 0
    for case in cases:
        if dry:
            reply = dry_reply(case["truth"])
        else:
            reply = caller(model, build_messages(case["question"], case["functions"]))
        if score(parse_call(reply), case["truth"]):
            correct += 1
        else:
            out(f"[FAIL] {case['id']}: {(reply or '').strip()[:160]!r}")
    total = len(cases)
    return correct, total


def main(argv=None):
    """Parse the flags, run the benchmark, and print correct/total as the last line."""
    parser = argparse.ArgumentParser(description="BFCL v3 simple, AST-scored, against the oMLX endpoint.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="model id the endpoint serves")
    parser.add_argument("--limit", type=int, default=None, help="run only the first N cases")
    parser.add_argument("--dry", action="store_true", help="score the possible answers themselves, no model call")
    args = parser.parse_args(argv)
    try:
        correct, total = run(model=args.model, limit=args.limit, dry=args.dry)
    except OSError as e:
        print(f"model endpoint not reachable at {ENDPOINT}: {e}", file=sys.stderr)
        return 1
    print(f"\n{correct}/{total} passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
