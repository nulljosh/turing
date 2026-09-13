"""Samantha training data: this repo's own docs (oversampled, primary subject)
plus a capped sample of the wider fleet (for house voice, not volume).

Chat-formatted, not raw text. mlx_lm.generate queries the model through its
chat template at inference; training on raw {"text": ...} continuations
never puts the LoRA weights inside that same chat-turn structure, so the
fine-tune barely touches how the model answers a real prompt.

Run 2 (2026-09-13) used chat format but globbed every README/roadmap/CLAUDE.md
across the whole ~50-repo fleet with no weighting, so Turing's own facts were
a tiny fraction of the data and the model learned "fleet README voice" instead
of actual Turing/Samantha facts. This version fixes that: own docs repeated
(oversampled) so they dominate, fleet docs capped to a small fixed sample.
"""
import json, glob, os, random, subprocess

OUT = os.path.expanduser("~/Documents/Code/turing/data/train.jsonl")
VAULT = os.path.expanduser("~/Library/Mobile Documents/iCloud~md~obsidian/Documents/Code")
CODE = os.path.expanduser("~/Documents/Code")
TURING = os.path.expanduser("~/Documents/Code/turing")

OWN_REPEATS = 3        # how many times to repeat this repo's own docs (10x caused overfitting/collapse, see eval run 3)
FLEET_CAP = 100         # max chunks pulled from the rest of the fleet + wiki

def chunks(text, n=1500):
    for i in range(0, len(text), n):
        yield text[i:i+n]

def to_chat(topic, content):
    return {
        "messages": [
            {"role": "user", "content": f"Tell me about {topic}."},
            {"role": "assistant", "content": content},
        ]
    }

def read_chunks(path, topic):
    # VAULT is a live iCloud folder, an evicted (not locally downloaded)
    # file can block a read for a long time waiting on a fetch, and it's
    # blocked deep enough (iCloud file provider IPC) that an in-process
    # signal.alarm() doesn't actually interrupt it, confirmed by watching
    # one stay stuck 140s+ past a 5s alarm. A subprocess can be killed
    # outright regardless of what it's blocked on, so shell out to `cat`
    # with a hard timeout instead of reading in-process.
    try:
        out = subprocess.run(["cat", path], capture_output=True, timeout=5)
        text = out.stdout.decode(errors="ignore").strip()
    except Exception:
        return []
    if len(text) < 100:
        return []
    return [to_chat(topic, c) for c in chunks(text) if len(c.strip()) >= 100]

def collect():
    own_paths = glob.glob(f"{TURING}/*.md") + glob.glob(f"{TURING}/eval/*.md")
    own_examples = []
    for p in own_paths:
        topic = "Samantha" if "WHITEPAPER" in p or "README" in p else "Turing"
        own_examples += read_chunks(p, topic)

    fleet_paths = []
    fleet_paths += glob.glob(f"{VAULT}/**/*.md", recursive=True)
    fleet_paths += glob.glob(f"{CODE}/**/README.md", recursive=True)
    fleet_paths += glob.glob(f"{CODE}/**/WHITEPAPER.md", recursive=True)
    fleet_paths += glob.glob(f"{CODE}/**/roadmap.md", recursive=True)
    fleet_paths += glob.glob(f"{CODE}/**/CLAUDE.md", recursive=True)
    fleet_paths = [p for p in fleet_paths if not p.startswith(TURING) and "/node_modules/" not in p and "/.git/" not in p]
    seen = set()
    fleet_examples = []
    for p in fleet_paths:
        if p in seen:
            continue
        seen.add(p)
        topic = os.path.splitext(os.path.basename(p))[0].replace("-", " ").replace("_", " ")
        fleet_examples += read_chunks(p, topic)

    random.seed(0)
    random.shuffle(fleet_examples)
    fleet_examples = fleet_examples[:FLEET_CAP]

    all_examples = own_examples * OWN_REPEATS + fleet_examples
    random.shuffle(all_examples)

    with open(OUT, "w") as f:
        for ex in all_examples:
            f.write(json.dumps(ex) + "\n")
    print(f"wrote {OUT}: {len(own_examples)} own chunks x{OWN_REPEATS}, {len(fleet_examples)} fleet chunks, {len(all_examples)} total")

if __name__ == "__main__":
    collect()
