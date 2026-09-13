"""Multi-turn chat on top of ask.py's retrieval. Not a fundamentally new
model, same retrieval-augmented Samantha, but with short-term memory across
turns so it feels like a conversation instead of one-shot Q&A every time.

Honest scope: this makes Samantha feel more like a real assistant to use.
It does not and cannot make a 0.5B model "as good as Claude/GPT", see
roadmap.md's "What we will never do on this budget."
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ask import search, try_extract, faq_match, general_knowledge, is_project_question, current_officeholder, _WHO_PREFIX, MODEL, ADAPTER, SYSTEM
import subprocess

HISTORY_TURNS = 3  # how many prior exchanges to keep as short-term memory


def clean(answer, question):
    # the model sometimes echoes the prompt scaffold ("User: ...\nSamantha:")
    # back into its own answer, especially near the max-token cutoff
    for marker in ("\nUser:", "\nSamantha:", "User:", "Samantha:"):
        idx = answer.find(marker)
        if idx > 0:
            answer = answer[:idx]
    return answer.strip()


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
        holder_answer = None
        if not is_project_question(question) and _WHO_PREFIX.match(question.strip()):
            holder_answer = current_officeholder(question)[0]

        faq_answer = None if holder_answer else faq_match(question)
        gk_answer = None
        if not holder_answer and not faq_answer and not is_project_question(question):
            gk_answer = general_knowledge(question)[0]

        if holder_answer:
            answer = holder_answer
        elif faq_answer:
            answer = faq_answer
        elif gk_answer:
            answer = gk_answer
        else:
            results = search(question)
            extracted = try_extract(question, results)
            if extracted:
                answer = extracted
            else:
                context = "\n\n---\n\n".join(r["text"][:800] for r in results)
                prompt = build_prompt(history, context, question)
                answer = clean(generate(prompt), question)
        print(f"Samantha: {answer}\n")
        history.append((question, answer))


if __name__ == "__main__":
    chat()
