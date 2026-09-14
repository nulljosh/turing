"""Multi-turn chat on top of ask.py's retrieval. Not a fundamentally new
model, same retrieval-augmented Samantha, but with short-term memory across
turns so it feels like a conversation instead of one-shot Q&A every time.

Honest scope: this makes Samantha feel more like a real assistant to use.
It does not and cannot make a 0.5B model "as good as Claude/GPT", see
roadmap.md's "What we will never do on this budget."
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ask import search, try_extract, faq_match, general_knowledge, is_project_question, is_question, current_officeholder, _WHO_PREFIX, MODEL, ADAPTER, SYSTEM
import subprocess

HISTORY_TURNS = 3  # how many prior exchanges to keep as short-term memory


def project_scope(question, topic_active):
    """is_project_question() only looks at the current question's own
    words, so any natural follow-up that doesn't repeat a project keyword
    gets misrouted to general_knowledge(). A pronoun-only fix ("what is
    ITS first model called") caught the obvious case but missed the next
    one found live: "How confident does a match need to be?" right after
    "What is the FAQ matcher?" has no pronoun and no keyword either, and
    got answered with a Wikipedia article about an unrelated Chinese
    comedian (her "confident" catchphrase). No amount of pattern-matching
    the current question's words alone can catch every phrasing of "still
    talking about the same thing".

    Once the conversation has genuinely turned to project (this session
    is explicitly branded "Samantha, Turing project assistant" from its
    first line), stay there for follow-ups instead of re-deriving scope
    from each question in isolation, a plain sticky flag threaded through
    the loop, simpler than a growing pile of reference-detection regexes
    and more robust to phrasings none of them would catch. The one
    carve-out: a "who is/who's the current X" question always overrides,
    that's a real, tested, intentional live-lookup escape hatch, not
    something a resumed project topic should swallow.

    Returns (project_scoped, updated topic_active) for the caller to
    thread through the next turn.
    """
    is_current = is_project_question(question)
    active = topic_active or is_current
    who_query = bool(_WHO_PREFIX.match(question.strip()))
    return (is_current or (active and not who_query)), active


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
    topic_active = False
    print("Samantha (Turing project assistant). Ctrl+C or 'exit' to quit.\n")
    while True:
        try:
            question = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not question or question.lower() in ("exit", "quit"):
            break
        project_scoped, topic_active = project_scope(question, topic_active)
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
