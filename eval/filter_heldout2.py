"""Blind filter: drop heldout2 rows that overlap eval/heldout.jsonl, hands-data/*.jsonl,
or eval/actions.py's CASES, without ever printing any text content (only a count)."""
import glob
import json
import re
import importlib.util


def norm(s):
    """Lowercase and collapse a string to bare words, for loose duplicate matching."""
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


existing = set()

# eval/heldout.jsonl
try:
    with open("eval/heldout.jsonl") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            existing.add(norm(row.get("text", "")))
except FileNotFoundError:
    pass

# hands-data/*.jsonl (chat-format {"messages":[...]})
for path in glob.glob("hands-data/*.jsonl"):
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            msgs = row.get("messages")
            if msgs and len(msgs) > 1:
                existing.add(norm(msgs[1].get("content", "")))
            elif "text" in row:
                existing.add(norm(row["text"]))
            elif "prompt" in row:
                existing.add(norm(row["prompt"]))

# eval/actions.py's CASES, loaded in memory only
spec = importlib.util.spec_from_file_location("actions_mod", "eval/actions.py")
actions_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(actions_mod)
CASES = getattr(actions_mod, "CASES", [])
for case in CASES:
    # CASES rows are tuples/lists/dicts; grab any string field that looks like the utterance
    if isinstance(case, dict):
        for v in case.values():
            if isinstance(v, str):
                existing.add(norm(v))
    elif isinstance(case, (list, tuple)):
        for v in case:
            if isinstance(v, str):
                existing.add(norm(v))

# now filter heldout2
kept = []
dropped = 0
with open("eval/heldout2.jsonl") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        if norm(row.get("text", "")) in existing:
            dropped += 1
            continue
        kept.append(row)

with open("eval/heldout2.jsonl", "w") as f:
    for row in kept:
        f.write(json.dumps(row) + "\n")

print(f"dropped: {dropped}")
print(f"kept: {len(kept)}")
