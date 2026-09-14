"""Multi-turn chat on top of ask.py's retrieval. Not a fundamentally new
model, same retrieval-augmented Samantha, but with short-term memory across
turns so it feels like a conversation instead of one-shot Q&A every time.

Honest scope: this makes Samantha feel more like a real assistant to use.
It does not and cannot make a 0.5B model "as good as Claude/GPT", see
roadmap.md's "What we will never do on this budget."
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ask import search, try_extract, faq_match, general_knowledge, is_project_question, is_question, current_officeholder, _WHO_PREFIX, UNREACHABLE, LOOKUP_FAILED, MODEL, ADAPTER, SYSTEM
import subprocess

HISTORY_TURNS = 3  # how many prior exchanges to keep as short-term memory

EXIT_WORDS = ("exit", "quit", "bye", "q")  # natural quit phrasings that should stop the loop, not get generated on


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
    # Same leak, different scaffold: FAQ.md is training data, so its own
    # "## Question" section-header voice sometimes bleeds into a real
    # answer near the token cutoff, live-confirmed asking about the sticky
    # topic flag: the model rambled into a spurious "## What is the honest
    # win condition for the user?" heading and kept going into unrelated
    # content. A real answer never legitimately contains a markdown header,
    # so cut at the first one exactly like the User:/Samantha: markers.
    idx = answer.find("\n##")
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


def answer_turn(question, history, topic_active):
    """One turn of the conversation: (question, history, topic_active) in,
    (answer, updated topic_active) out. Shared by the plain CLI and the TUI
    so the two never drift into different answer logic.
    """
    project_scoped, topic_active = project_scope(question, topic_active)
    holder_answer = None
    if not project_scoped and _WHO_PREFIX.match(question.strip()):
        holder_answer, holder_source = current_officeholder(question)
        # same rule as ask.py: a failed lookup must not fall through to an
        # FAQ entry describing the feature, but the encyclopedia can still
        # answer a "who is <person>" question, so only decline if it can't
        if not holder_answer and holder_source is UNREACHABLE:
            holder_answer = general_knowledge(question, skip_officeholder=True)[0] or LOOKUP_FAILED

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

    # topic_active is meant to track "has this conversation actually been
    # about the project so far", not just "did the current question's own
    # wording contain a project keyword". A question can be genuinely
    # project-scoped (it FAQ-matched, or retrieval/generation answered it
    # from project docs) without tripping is_project_question()'s keyword
    # list, e.g. "how do I boot into you". Before this fix, a follow-up to
    # exactly that kind of question ("what if I don't pass any flags") had
    # no keyword of its own either, topic_active was still False, and it
    # fell through to general_knowledge(), which returned an unrelated and
    # genuinely alarming Wikipedia result (ISIS flag history) for a
    # question that was actually about command-line flags. Latch
    # topic_active on however the answer actually got produced, not just
    # on re-deriving scope from the current question's words.
    if faq_answer or (not holder_answer and not gk_answer and answer):
        topic_active = True
    return answer, topic_active


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
        if not question or question.lower() in EXIT_WORDS:
            break
        answer, topic_active = answer_turn(question, history, topic_active)
        print(f"Samantha: {answer}\n")
        history.append((question, answer))


def tui():
    import curses

    def run(stdscr):
        curses.curs_set(1)
        stdscr.scrollok(True)
        history = []
        topic_active = False
        lines = ["Samantha (Turing project assistant). Ctrl+C or type 'exit' to quit.", ""]

        def redraw():
            stdscr.erase()
            h, w = stdscr.getmaxyx()
            for i, line in enumerate(lines[-(h - 2):]):
                stdscr.addstr(i, 0, line[: w - 1])
            stdscr.addstr(h - 1, 0, "You: ")
            stdscr.refresh()

        while True:
            redraw()
            curses.echo()
            h, _ = stdscr.getmaxyx()
            try:
                question = stdscr.getstr(h - 1, 5).decode().strip()
            except KeyboardInterrupt:
                break
            curses.noecho()
            if not question or question.lower() in EXIT_WORDS:
                break
            lines.append(f"You: {question}")
            stdscr.erase()
            stdscr.addstr(0, 0, "thinking...")
            stdscr.refresh()
            answer, topic_active = answer_turn(question, history, topic_active)
            history.append((question, answer))
            for l in (f"Samantha: {answer}", ""):
                lines.extend(l.split("\n"))

    curses.wrapper(run)


if __name__ == "__main__":
    if "--tui" in sys.argv:
        tui()
    else:
        chat()
