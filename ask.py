"""Phase 4: ask Samantha a question with retrieval instead of relying on
memorized weights. Pulls real passages from brain's index, feeds them to
the model as context, model answers from what it's actually given.

Six training runs on 2026-09-13 confirmed a 0.5B LoRA on a few hundred
examples reliably learns style but not facts. This is the fix: keep facts
in brain's live index, let the model reason over retrieved context instead
of trying to recall them from weights. See roadmap.md, run 6.
"""
import json, os, subprocess, sys, urllib.parse, urllib.request

BRAIN_ENV = os.path.expanduser("~/Documents/Code/brain/.env.local")
BRAIN_URL = "https://brain.heyitsmejosh.com/api/search"
MODEL = "mlx-community/Qwen2.5-0.5B-Instruct-4bit"
ADAPTER = os.path.expanduser("~/Documents/Code/turing/ada-1-adapter")


def brain_token():
    for line in open(BRAIN_ENV):
        if line.strip().startswith("BRAIN_TOKEN"):
            return line.strip().split("=", 1)[1].strip().strip('"')
    raise RuntimeError("BRAIN_TOKEN not found in brain/.env.local")


def search(query, limit=3):
    token = brain_token()
    # bias the embedding itself toward this project, brain's index spans
    # ~50 other repos and a generic question often matches them just as
    # well as it matches Turing's own docs
    biased_query = f"Turing Samantha LoRA project: {query}"
    url = f"{BRAIN_URL}?q={urllib.parse.quote(biased_query)}&limit={max(limit * 3, 10)}"
    req = urllib.request.Request(url, headers={
        "authorization": f"Bearer {token}",
        "user-agent": "turing-ask/1.0",
    })
    with urllib.request.urlopen(req, timeout=15) as r:
        results = json.load(r)["results"]
    own = [r for r in results if "/turing/" in r["source"]]
    other = [r for r in results if "/turing/" not in r["source"]]
    return (own + other)[:limit]


def ask(question):
    results = search(question)
    context = "\n\n---\n\n".join(r["text"][:800] for r in results)
    prompt = (
        "Answer the question using only the context below. "
        "If the context doesn't contain the answer, say so, don't guess.\n\n"
        f"Context:\n{context}\n\nQuestion: {question}"
    )
    out = subprocess.run(
        [
            os.path.expanduser("~/Documents/Code/turing/.venv/bin/mlx_lm.generate"),
            "--model", MODEL,
            "--adapter-path", ADAPTER,
            "--prompt", prompt,
            "--max-tokens", "150",
        ],
        capture_output=True, text=True,
    )
    gen = out.stdout.split("==========")[1].strip() if "==========" in out.stdout else out.stdout.strip()
    return gen, [r["source"] for r in results]


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "What is Turing?"
    answer, sources = ask(q)
    print(f"Q: {q}\n\nA: {answer}\n\nSources:")
    for s in sources:
        print(f"  {s}")
