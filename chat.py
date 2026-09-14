"""Multi-turn chat on top of ask.py's retrieval. Not a fundamentally new
model, same retrieval-augmented Samantha, but with short-term memory across
turns so it feels like a conversation instead of one-shot Q&A every time.

Honest scope: this makes Samantha feel more like a real assistant to use.
It does not and cannot make a 0.5B model "as good as Claude/GPT", see
roadmap.md's "What we will never do on this budget."
"""
import os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ask import search, try_extract, faq_match, general_knowledge, is_project_question, is_question, current_officeholder, _WHO_PREFIX, MODEL, ADAPTER, SYSTEM
import subprocess

HISTORY_TURNS = 3  # how many prior exchanges to keep as short-term memory

_PRONOUN_FOLLOWUP = re.compile(r"\b(it|its|it's|this|that|these|those)\b", re.I)


def _is_project_followup(question, history):
    """is_project_question() only looks at the current question's own
    words, so a natural pronoun follow-up in a live conversation ("What is
    its first model called?" right after "What is Turing?") has no project
    keyword of its own and gets misrouted to general_knowledge(). Confirmed
    live: that exact follow-up got answered with a generic Wikipedia-style
    "what is an LLM" definition, no memory of the prior turn at all, the
    one thing this file exists to add over ask.py's single-shot ask().
    If the previous turn was already about the project and this one refers
    back to it, treat it as a continuation instead of a fresh topic.
    """
    if not history:
        return False
    return is_project_question(history[-1][0]) and bool(_PRONOUN_FOLLOWUP.search(question))


def clean(answer, question):
    # the model sometimes echoes the prompt scaffold ("User: ...\nSamantha:")
    # back into its own answer, especially near the max-token cutoff
    for marker in ("\nUser:", "\nSamantha:", "User:", "Samantha:"):
        idx = answer.find(marker)
        # idx == 0 means the entire output IS the echoed scaffold with no
        # leading newline. The old "idx > 0" guard skipped that case, so
        # the raw "User: ...\nSamantha: ..." text leaked straight to the
        # user as if it were the real answer. Confirmed: clean("User: what
        # else?\nSamantha: x", "q") returned the untouched echo. An empty
        # string here is a truthful "nothing usable," strictly better than
        # showing the scaffold as if it were Samantha's answer.
        if idx >= 0:
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
        project_scoped = is_project_question(question) or _is_project_followup(question, history)
        holder_answer = None
        if not project_scoped and _WHO_PREFIX.match(question.strip()):
            holder_answer = current_officeholder(question)[0]

        faq_answer = None if holder_answer else faq_match(question)
        gk_answer = None
        if not holder_answer and not faq_answer and not project_scoped and is_question(question):
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
