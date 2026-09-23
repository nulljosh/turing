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
import json, glob, os, random, re, subprocess

OUT = os.path.expanduser("~/Documents/Code/turing/data/train.jsonl")
VAULT = os.path.expanduser("~/Library/Mobile Documents/iCloud~md~obsidian/Documents/Code")
CODE = os.path.expanduser("~/Documents/Code")
TURING = os.path.expanduser("~/Documents/Code/turing")
EXAMPLES = os.path.expanduser("~/Documents/Code/turing/TRAINING_EXAMPLES.md")

OWN_REPEATS = 3        # how many times to repeat this repo's own docs (10x caused overfitting/collapse, see eval run 3)
FLEET_CAP = None        # everything from the fleet + wiki + journal (was 100 until 2026-09-22: "train it on everything")

def chunks(text, n=1500):
    """Yield successive n-character chunks of text."""
    for i in range(0, len(text), n):
        yield text[i:i+n]

def to_chat(topic, content):
    """Convert a topic and content into a chat message pair."""
    return {
        "messages": [
            {"role": "user", "content": f"Tell me about {topic}."},
            {"role": "assistant", "content": content},
        ]
    }

def read_examples(path):
    """Parse instruction/response pairs from markdown file into chat format."""
    # Real instruction/response pairs (e.g. "write a commit message" ->
    # an actual past commit message), not "tell me about X" facts. The
    # generic to_chat() template can't represent a task instruction, so
    # this parses TRAINING_EXAMPLES.md's own "## instruction" / response
    # pairs directly into chat turns, same header style as FAQ.md.
    try:
        out = subprocess.run(["cat", path], capture_output=True, timeout=5)
        text = out.stdout.decode(errors="ignore")
    except Exception:
        return []
    parts = re.split(r"^## (.+)$", text, flags=re.M)[1:]
    examples = []
    for i in range(0, len(parts) - 1, 2):
        instruction, response = parts[i].strip(), parts[i + 1].strip()
        if instruction and response:
            examples.append({
                "messages": [
                    {"role": "user", "content": instruction},
                    {"role": "assistant", "content": response},
                ]
            })
    return examples


def read_chunks(path, topic):
    """Read markdown file and return chunked chat training examples for a topic."""
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
    """Gather and prepare training data from Turing docs and the fleet, write to JSONL."""
    own_paths = glob.glob(f"{TURING}/*.md") + glob.glob(f"{TURING}/eval/*.md") + glob.glob(f"{TURING}/docs/*.md")
    own_paths = [p for p in own_paths if p != EXAMPLES]
    own_examples = []
    for p in own_paths:
        topic = "Samantha" if "WHITEPAPER" in p or "README" in p else "Turing"
        own_examples += read_chunks(p, topic)
    own_examples += read_examples(EXAMPLES)
    # Harvested commit-message pairs (harvest_voice.py). Same format as
    # TRAINING_EXAMPLES.md, ~15x the volume, and every response is a real
    # line Joshua wrote. Optional: a fresh clone has no data/ until the
    # harvester runs, and training still works without it.
    own_examples += read_examples(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "voice.md"))

    fleet_paths = []
    fleet_paths += glob.glob(f"{VAULT}/**/*.md", recursive=True)
    fleet_paths += glob.glob(f"{CODE}/**/README.md", recursive=True)
    fleet_paths += glob.glob(f"{CODE}/**/WHITEPAPER.md", recursive=True)
    fleet_paths += glob.glob(f"{CODE}/**/roadmap.md", recursive=True)
    fleet_paths += glob.glob(f"{CODE}/**/CLAUDE.md", recursive=True)
    fleet_paths += glob.glob(f"{CODE}/*/docs/*.md")  # architecture notes, whitepaper drafts
    fleet_paths += glob.glob(f"{CODE}/journal/_posts/*.md")  # the journal, in his own words
    fleet_paths = [p for p in fleet_paths if not p.startswith(TURING) and not any(d in p for d in ("/node_modules/", "/.git/", "/_external/", "/.build/", "/Pods/", "/.venv/"))]
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
    fleet_examples = fleet_examples[:FLEET_CAP]  # [:None] keeps all

    all_examples = own_examples * OWN_REPEATS + fleet_examples
    random.shuffle(all_examples)

    with open(OUT, "w") as f:
        for ex in all_examples:
            f.write(json.dumps(ex) + "\n")
    print(f"wrote {OUT}: {len(own_examples)} own chunks x{OWN_REPEATS}, {len(fleet_examples)} fleet chunks, {len(all_examples)} total")

if __name__ == "__main__":
    collect()
