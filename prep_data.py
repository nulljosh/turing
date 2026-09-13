"""Samantha training data: Obsidian wiki + project READMEs/WHITEPAPERs + small wikitext sample.

Chat-formatted, not raw text. mlx_lm.generate queries the model through its
chat template at inference; training on raw {"text": ...} continuations
(the old format) never puts the LoRA weights inside that same chat-turn
structure, so the fine-tune barely touches how the model answers a real
prompt. Wrapping each chunk as a user/assistant turn trains it in the
actual format it's used in.
"""
import json, glob, os

OUT = os.path.expanduser("~/Documents/Code/turing/data/train.jsonl")
VAULT = os.path.expanduser("~/Library/Mobile Documents/iCloud~md~obsidian/Documents/Code")
CODE = os.path.expanduser("~/Documents/Code")

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

def collect():
    paths = []
    paths += glob.glob(f"{VAULT}/**/*.md", recursive=True)
    paths += glob.glob(f"{CODE}/**/README.md", recursive=True)
    paths += glob.glob(f"{CODE}/**/WHITEPAPER.md", recursive=True)
    paths += glob.glob(f"{CODE}/**/roadmap.md", recursive=True)
    paths += glob.glob(f"{CODE}/**/CLAUDE.md", recursive=True)
    seen = set()
    with open(OUT, "w") as f:
        for p in paths:
            if p in seen or "/node_modules/" in p or "/.git/" in p:
                continue
            seen.add(p)
            try:
                text = open(p, errors="ignore").read().strip()
            except Exception:
                continue
            if len(text) < 100:
                continue
            topic = os.path.splitext(os.path.basename(p))[0].replace("-", " ").replace("_", " ")
            for c in chunks(text):
                if len(c.strip()) < 100:
                    continue
                f.write(json.dumps(to_chat(topic, c)) + "\n")
    print(f"wrote {OUT} from {len(seen)} files")

if __name__ == "__main__":
    collect()
