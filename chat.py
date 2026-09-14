"""Multi-turn chat on top of ask.py's retrieval. Not a fundamentally new
model, same retrieval-augmented Samantha, but with short-term memory across
turns so it feels like a conversation instead of one-shot Q&A every time.

Honest scope: this makes Samantha feel more like a real assistant to use.
It does not and cannot make a 0.5B model "as good as Claude/GPT", see
roadmap.md's "What we will never do on this budget."
"""
import os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ask import search, try_extract, faq_match, general_knowledge, is_project_question, is_question, current_officeholder, _WHO_PREFIX, _QUESTION_PREFIX, _keywords, project_vocabulary, clock, arithmetic, OUT_OF_SCOPE, UNREACHABLE, LOOKUP_FAILED, MODEL, ADAPTER, SYSTEM
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

    # Second carve-out, same spirit as the who-query one: the sticky flag
    # had no way out except a "who is the current X" question, so a genuine
    # change of subject got swallowed. Confirmed live, "what is turing"
    # followed by "what is the capital of japan" answered "the project."
    # A question whose content words are *all* absent from the project's own
    # vocabulary is a topic change, not a keywordless follow-up. This is the
    # same foreign-word test that fixed faq_match's false positives, and it
    # can't break the case the sticky flag exists for: "How confident does a
    # match need to be?" shares "match", "what if I don't pass any flags"
    # shares "flags".
    if active and not is_current:
        words = _keywords(question)
        if words and not (words & project_vocabulary()):
            return False, False

    return (is_current or (active and not who_query)), active


_PRONOUN = re.compile(r"\b(?:he|him|his|she|hers|they|them|their|its|it)\b", re.I)


def self_contained(question):
    """True when the question answers itself locally (clock, arithmetic).
    Such a question never refers back to an earlier turn, and never supplies
    a subject a later turn could refer back to."""
    return bool(clock(question) or arithmetic(question))


def subject_of(question):
    """The thing a question was about, for resolving the next question's
    pronoun against. Reuses ask.py's own prefix regexes rather than a new
    one: "who is steve jobs" gives "steve jobs".
    """
    stripped = _WHO_PREFIX.sub("", question.strip()).rstrip("?").strip()
    if stripped == question.strip().rstrip("?").strip():
        stripped = _QUESTION_PREFIX.sub("", stripped).strip()
    return stripped or None


def resolve_followup(question, last_subject):
    """Substitute a bare pronoun with whatever the last general-knowledge
    answer was about.

    chat.py exists to carry conversation memory, but that memory only ever
    covered *project* topics via the sticky topic flag. A general-knowledge
    follow-up had no referent at all, so it went to the encyclopedia as
    written. Confirmed live: "who is steve jobs" answered correctly, then
    "what company did he found" returned the 1997 slasher film "I Know What
    You Did Last Summer", because Wikipedia's title search matched the
    sentence's own words with nothing to say who "he" was.

    Only the first pronoun is replaced, which is enough to make the search
    query name its subject, and leaves the rest of the sentence intact.
    """
    if not last_subject or not _PRONOUN.search(question):
        return question
    # "it" in "what day is it" or "what is 2+2, is it 4" is a dummy subject,
    # not a reference to anything earlier. These questions answer themselves
    # from the clock or a calculator, so substituting into them can only
    # corrupt them. Confirmed live: "what year is it" then "what day is it"
    # became "what day is what year is it", which re-matched the year
    # pattern and answered 2026 twice.
    if self_contained(question):
        return question
    return _PRONOUN.sub(last_subject, question, count=1)


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


def answer_turn(question, history, topic_active, last_subject=None):
    """One turn of the conversation: (question, history, topic_active) in,
    (answer, updated topic_active) out. Shared by the plain CLI and the TUI
    so the two never drift into different answer logic.

    `last_subject` carries what the previous general-knowledge answer was
    about, so a pronoun follow-up can be resolved. Returns it updated as a
    third element; it defaults to None so a caller that doesn't track
    conversation state (the tests, one-shot use) behaves exactly as before.
    """
    project_scoped, _ = project_scope(question, topic_active)
    # resolve "he/she/it" against the last general-knowledge subject before
    # anything else looks at the question, but never inside a project topic,
    # where the sticky flag already handles continuity
    if not project_scoped:
        question = resolve_followup(question, last_subject)
    project_scoped, topic_active = project_scope(question, topic_active)
    answered_from_project = False
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
    elif not project_scoped:
        # The question isn't about the project and the encyclopedia had
        # nothing. Generating anyway means generating *from project
        # retrieval context*, which can only produce a project-flavoured
        # answer to an outside question. Confirmed live: "what is teh
        # capitol of frnace" (typo'd, so no source could match it) came back
        # "the Turing project", and a bare "why" produced invented detail
        # about a nonexistent model. Saying so is the honest option.
        answer = OUT_OF_SCOPE
    else:
        results = search(question)
        extracted = try_extract(question, results)
        if extracted:
            answer = extracted
            answered_from_project = True
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
    # Latch only on real evidence the question was about the project: an FAQ
    # match, a project extraction, or a question that was already in scope.
    #
    # The previous rule also latched on the bare generation fallback, which
    # is the catch-all every unanswered question lands in, *including* an
    # outside question the encyclopedia simply couldn't answer. Confirmed
    # live and it was severe: "who is taylor swift" answered fine, then "and
    # her net worth?" found nothing, fell to generation, invented "Turing.
    # Not a model." and latched the flag. Every later question in that
    # session was then treated as project-scoped, so "what is teh capitol of
    # frnace" answered "the Turing project". One failed outside question
    # permanently converted the conversation.
    if faq_answer or answered_from_project or project_scoped:
        topic_active = True
    # remember the subject only while the conversation is off-project, so a
    # stale person never gets substituted into a later project question
    if (holder_answer or gk_answer) and not self_contained(question):
        last_subject = subject_of(question) or last_subject
    elif topic_active:
        last_subject = None
    return answer, topic_active, last_subject


def chat():
    history = []
    topic_active = False
    last_subject = None
    print("Samantha (Turing project assistant). Ctrl+C or 'exit' to quit.\n")
    while True:
        try:
            question = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not question or question.lower() in EXIT_WORDS:
            break
        answer, topic_active, last_subject = answer_turn(question, history, topic_active, last_subject)
        print(f"Samantha: {answer}\n")
        history.append((question, answer))


def tui():
    import curses

    def run(stdscr):
        curses.curs_set(1)
        stdscr.scrollok(True)
        history = []
        topic_active = False
        last_subject = None
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
            answer, topic_active, last_subject = answer_turn(question, history, topic_active, last_subject)
            history.append((question, answer))
            for l in (f"Samantha: {answer}", ""):
                lines.extend(l.split("\n"))

    curses.wrapper(run)


if __name__ == "__main__":
    if "--tui" in sys.argv:
        tui()
    else:
        chat()
