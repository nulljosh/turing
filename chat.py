"""Multi-turn chat on top of ask.py's retrieval. Not a fundamentally new
model, same retrieval-augmented Samantha, but with short-term memory across
turns so it feels like a conversation instead of one-shot Q&A every time.

Honest scope: this makes Samantha feel more like a real assistant to use.
It does not and cannot make a 0.5B model "as good as Claude/GPT", see
roadmap.md's "What we will never do on this budget."
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ask import search, MODEL, ADAPTER
import subprocess

HISTORY_TURNS = 3  # how many prior exchanges to keep as short-term memory

SYSTEM = (
    "You are Samantha, a small assistant for the Turing project. Answer only "
    "from the context given. Plain language, 1-3 sentences, no filler, no "
    "em dashes. If the context doesn't have the answer, say so, don't guess."
)


def generate(prompt, max_tokens=80):
    out = subprocess.run(
        [
            os.path.expanduser("~/Documents/Code/turing/.venv/bin/mlx_lm.generate"),
            "--model", MODEL,
            "--adapter-path", ADAPTER,
            "--prompt", prompt,
            "--max-tokens", str(max_tokens),
        ],
        capture_output=True, text=True,
    )
    return out.stdout.split("==========")[1].strip() if "==========" in out.stdout else out.stdout.strip()


def build_prompt(history, context, question):
    parts = [SYSTEM, ""]
    if history:
        parts.append("Recent conversation:")
        for q, a in history[-HISTORY_TURNS:]:
            parts.append(f"User: {q}\nSamantha: {a}")
        parts.append("")
    parts.append(f"Context:\n{context}")
    parts.append(f"\nUser: {question}\nSamantha:")
    return "\n".join(parts)


def chat():
    history = []
    print("Samantha (Turing project assistant). Ctrl+C or 'exit' to quit.\n")
    while True:
        try:
            question = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not question or question.lower() in ("exit", "quit"):
            break
        results = search(question)
        context = "\n\n---\n\n".join(r["text"][:800] for r in results)
        prompt = build_prompt(history, context, question)
        answer = generate(prompt)
        print(f"Samantha: {answer}\n")
        history.append((question, answer))


if __name__ == "__main__":
    chat()
