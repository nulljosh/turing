"""Blind scoring detail: group wrong-past-guard and refused heldout2 cases by
(expected tool, picked tool) with counts only, never texts."""
import json
import os
import re
import sys
import time
from collections import Counter

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "eval"))
sys.path.insert(0, os.path.join(REPO, "training"))
os.environ["SAMANTHA_HEADLESS"] = "1"
import tools
from gen_hands_data import SYSTEM
from mlx_lm import load, generate

BASE = "mlx-community/Qwen2.5-0.5B-Instruct-4bit"
ADAPTER = "hands-adapter"

model, tok = load(BASE, adapter_path=os.path.join(REPO, ADAPTER))

fired_groups = Counter()
blocked_groups = Counter()
score = [0, 0]
t0 = time.time()

rows = [json.loads(l) for l in open(os.path.join(REPO, "eval", "heldout2.jsonl")) if l.strip()]

for row in rows:
    text, tool, arg = row["text"], row.get("tool"), row.get("arg_hint", "")
    prompt = tok.apply_chat_template([{"role": "system", "content": SYSTEM}, {"role": "user", "content": text}],
                                     add_generation_prompt=True, tokenize=False, enable_thinking=False)
    raw = generate(model, tok, prompt=prompt, max_tokens=48, verbose=False)
    found = re.search(r"\{.*?\}", re.sub(r"(?s)<think>.*?</think>", "", raw), re.S)
    try:
        got = json.loads(found.group(0)) if found else {}
    except ValueError:
        got = {}
    got_arg = str(got.get("arg") or "").lower().strip()
    ok = got.get("tool", "?") == tool and ((arg or "").lower() in got_arg)
    score[0] += ok
    score[1] += 1
    if ok and tool and tool != "agent" and not tools._sound(tool, str(got.get("arg") or "").strip(), text):
        blocked_groups[(tool, got.get("tool"))] += 1
    if not ok:
        picked = got.get("tool")
        if picked and picked not in (tool, "agent") and tools._sound(picked, str(got.get("arg") or "").strip(), text):
            fired_groups[(tool, picked)] += 1

print(f"heldout2: {score[0]}/{score[1]} passed, {time.time()-t0:.0f}s")
print("\nwrong-past-guard groups (expected -> picked): count")
for (exp, got), c in fired_groups.most_common():
    print(f"  {exp} -> {got}: {c}")
print(f"  TOTAL wrong-past-guard: {sum(fired_groups.values())}")

print("\nrefused (right pick, guard blocked) groups (expected -> picked): count")
for (exp, got), c in blocked_groups.most_common():
    print(f"  {exp} -> {got}: {c}")
print(f"  TOTAL refused: {sum(blocked_groups.values())}")
