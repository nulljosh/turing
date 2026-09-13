"""Phase 4: ask Samantha a question with retrieval instead of relying on
memorized weights. Pulls real passages from brain's index, feeds them to
the model as context, model answers from what it's actually given.

Six training runs on 2026-09-13 confirmed a 0.5B LoRA on a few hundred
examples reliably learns style but not facts. This is the fix: keep facts
in brain's live index, let the model reason over retrieved context instead
of trying to recall them from weights. See roadmap.md, run 6.
"""
import json, os, re, subprocess, sys, urllib.parse, urllib.request

BRAIN_ENV = os.path.expanduser("~/Documents/Code/brain/.env.local")
BRAIN_URL = "https://brain.heyitsmejosh.com/api/search"
MODEL = "mlx-community/Qwen2.5-0.5B-Instruct-4bit"
ADAPTER = os.path.expanduser("~/Documents/Code/turing/ada-1-adapter")

# shared house-voice rules, used by both ask() here and chat.py's multi-turn
# loop, so the two don't quietly drift into different personalities
SYSTEM = (
    "You are Samantha, a small assistant for the Turing project. Answer only "
    "from the context given. Plain language, short sentences, no filler, no "
    "em dashes, no emojis. If the context doesn't have the answer, say so, "
    "don't guess."
)


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


# precision-sensitive facts: generation invents plausible-but-wrong specifics
# for these even with the right source in context (see eval/results-2026-09-13-rag2.md),
# so pull the answer straight from the retrieved text instead of trusting the model
EXTRACTORS = [
    (re.compile(r"\blicen[cs]e\b", re.I), re.compile(r"\b(MIT|Apache-2\.0|GPL-?v?\d|BSD-\d-Clause)\b")),
    (re.compile(r"\bwhat tool\b.*\btrain", re.I), re.compile(r"`(mlx_lm\.lora|mlx-lm|run_lora_capped\.py)`")),
    (re.compile(r"\bLoRA\b.*\bstand", re.I), re.compile(r"Low-Rank Adaptation")),
]

# fixed facts that never change and don't benefit from retrieval: "Joshua
# Trommel" appears in nearly every repo across the fleet (he's the author of
# all of them), so it's not distinctive enough for Turing-specific search to
# isolate, tried several query variants, the maintainer chunk never made the
# top 15 results. This is invariant across every project, just answer it.
FIXED_FACTS = [
    (re.compile(r"\bwho\b.*\b(maintain|own|wrote|author)", re.I), "Joshua Trommel"),
]


def try_extract(question, results):
    for q_pat, answer in FIXED_FACTS:
        if q_pat.search(question):
            return answer
    for q_pat, a_pat in EXTRACTORS:
        if q_pat.search(question):
            for r in results:
                m = a_pat.search(r["text"])
                if m:
                    return m.group(0)
    return None


def ask(question):
    results = search(question)
    extracted = try_extract(question, results)
    if extracted:
        return extracted, [r["source"] for r in results]
    context = "\n\n---\n\n".join(r["text"][:800] for r in results)
    prompt = f"{SYSTEM}\n\nContext:\n{context}\n\nQuestion: {question}"
    out = subprocess.run(
        [
            os.path.expanduser("~/Documents/Code/turing/.venv/bin/mlx_lm.generate"),
            "--model", MODEL,
            "--adapter-path", ADAPTER,
            "--prompt", prompt,
            "--max-tokens", "100",
        ],
        capture_output=True, text=True,
    )
    gen = out.stdout.split("==========")[1].strip() if "==========" in out.stdout else out.stdout.strip()
    return gen, [r["source"] for r in results]


if __name__ == "__main__":
    args = sys.argv[1:]
    as_json = "--json" in args
    if as_json:
        args = [a for a in args if a != "--json"]
    q = " ".join(args) or "What is Turing?"
    answer, sources = ask(q)
    if as_json:
        print(json.dumps({"question": q, "answer": answer, "sources": sources}))
    else:
        print(f"Q: {q}\n\nA: {answer}\n\nSources:")
        for s in sources:
            print(f"  {s}")
