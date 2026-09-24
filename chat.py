"""Multi-turn chat on top of ask.py's retrieval. Not a fundamentally new
model, same retrieval-augmented Samantha, but with short-term memory across
turns so it feels like a conversation instead of one-shot Q&A every time.

Honest scope: this makes Samantha feel more like a real assistant to use.
It does not and cannot make a 0.5B model "as good as Claude/GPT", see
roadmap.md's "What we will never do on this budget."
"""
import os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ask import search, try_extract, faq_match, general_knowledge, is_project_question, is_question, current_officeholder, _WHO_PREFIX, _QUESTION_PREFIX, _keywords, project_vocabulary, clock, arithmetic, convert, local_answer, NETWORK_DOWN, OUT_OF_SCOPE, UNREACHABLE, LOOKUP_FAILED, MODEL, ADAPTER, SYSTEM

HISTORY_TURNS = 3  # how many prior exchanges to keep as short-term memory

MODEL_DOWN = "My own model isn't answering on this machine right now, so I can't write that one. Questions I can look up and things I can do still work."

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
    return bool(clock(question) or arithmetic(question) or convert(question))


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
    """Remove echoed scaffold and markdown headers from model output."""
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


_answerer = None  # (model, tokenizer), loaded once per chat: a fresh process per turn spent ~2s reloading her before a word
STOPS = ("\nUser:", "\nSamantha:", "User:", "Samantha:", "\n##")  # the scaffold clean() cuts at; streaming stops there too
HOLD = max(map(len, STOPS))
SENTENCES = int(os.environ.get("SAMANTHA_SENTENCES", "2"))  # 0 lets her run to max_tokens
REPETITION = float(os.environ.get("SAMANTHA_REPETITION", "1.1"))  # 0 turns the penalty off  # characters held back while streaming, so a half-written marker is never shown


def _model():
    """Her answer model and tokenizer, loaded on first use and kept. Raises OSError when MLX or the weights are not here."""
    global _answerer
    if _answerer is None:
        try:
            from mlx_lm import load
            _answerer = load(MODEL, adapter_path=ADAPTER)
        except Exception as e:
            raise OSError(f"answer model unavailable: {e}") from e
    return _answerer


def generate(prompt, max_tokens=80, on_text=None):
    """Her model's reply to a prompt, streamed: on_text gets each safe piece as it is written. Stops at echoed scaffold."""
    from mlx_lm import stream_generate
    model, tok = _model()
    prompt = tok.apply_chat_template([{"role": "user", "content": prompt}], add_generation_prompt=True, tokenize=False)
    text, shown = "", 0
    penalty = None
    if REPETITION:  # a light repetition penalty: past the answer she loops ("deeper than the deeper one")
        from mlx_lm.sample_utils import make_logits_processors
        penalty = make_logits_processors(repetition_penalty=REPETITION)
    for r in stream_generate(model, tok, prompt, max_tokens=max_tokens, logits_processors=penalty):
        text += r.text
        if any(m in text for m in STOPS):
            break
        if SENTENCES and len(re.findall(r"[.!?](?:\s|$)", text)) >= SENTENCES:
            break  # her lessons answer in one or two sentences; what she writes after that is where she invents
        if on_text and len(text) - HOLD > shown:
            on_text(text[shown:len(text) - HOLD])
            shown = len(text) - HOLD
    return text


def build_prompt(history, context, question):
    """Construct a model prompt including system message, conversation history, and context."""
    parts = [SYSTEM, ""]
    if history:
        parts.append("Recent conversation:")
        for q, a in history[-HISTORY_TURNS:]:
            parts.append(f"User: {q}\nSamantha: {a}")
        parts.append("")
    parts.append(f"Context:\n{context}")
    parts.append(f"\nUser: {question}\nSamantha:")
    return "\n".join(parts)


def answer_turn(question, history, topic_active, last_subject=None, on_text=None):
    """One turn of the conversation: (question, history, topic_active) in,
    (answer, updated topic_active) out. Shared by the plain CLI and the TUI
    so the two never drift into different answer logic.

    `last_subject` carries what the previous general-knowledge answer was
    about, so a pronoun follow-up can be resolved. Returns it updated as a
    third element; it defaults to None so a caller that doesn't track
    conversation state (the tests, one-shot use) behaves exactly as before.
    """
    exact, _exact_source = local_answer(question)
    if exact:
        return exact, topic_active, last_subject

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
        gk_answer, gk_source = general_knowledge(question)
        if not gk_answer and gk_source is UNREACHABLE:
            gk_answer = NETWORK_DOWN

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
            try:
                answer = clean(generate(prompt, on_text=on_text), question) or MODEL_DOWN
            except (OSError, ImportError):
                # the weights live in .venv on the Mac; without them, or if the model hangs, say so
                answer = MODEL_DOWN

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


def safe_turn(question, history, topic_active, last_subject, on_text=None):
    """answer_turn, but a failure anywhere in the answer chain is a reply, never the end of the conversation."""
    try:
        return answer_turn(question, history, topic_active, last_subject, on_text)
    except Exception as e:
        return f"Something broke while I was answering that ({type(e).__name__}: {e}). Ask again, or ask something else.", topic_active, last_subject


def chat():
    """Run the interactive terminal chat loop."""
    import harness
    history = []
    topic_active = False
    last_subject = None
    # commands ("set the volume to 30", "take a note buy milk") run through the harness: the tool call is shown, and anything that writes asks first
    session = harness.Session(confirm=harness._ask_yes, log=print)
    print("Samantha (Turing project assistant). She answers questions and does things on this Mac, and asks before anything that writes. Ctrl+C or 'exit' to quit.\n")
    while True:
        try:
            question = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not question or question.lower() in EXIT_WORDS:
            break
        did = session.ask(question, or_none=True)
        if did is not None:
            print(f"Samantha: {did}\n")
            history.append((question, did))
            continue
        shown = []

        def show(piece):
            """Print her words as she writes them."""
            piece = piece if shown else "Samantha: " + piece.lstrip()
            shown.append(piece)
            print(piece, end="", flush=True)
        answer, topic_active, last_subject = safe_turn(question, history, topic_active, last_subject, on_text=show)
        said = "".join(shown).removeprefix("Samantha: ")
        print(answer[len(said):] + "\n" if shown and answer.startswith(said) else ("\n" if shown else "") + f"Samantha: {answer}\n")
        history.append((question, answer))


def tui():
    """Run the curses-based terminal UI for chat."""
    import curses

    def run(stdscr):
        """Inner TUI loop that renders and processes input."""
        curses.curs_set(1)
        stdscr.scrollok(True)
        import harness
        history = []
        topic_active = False
        last_subject = None
        lines = ["Samantha (Turing project assistant). She also does things on this Mac and asks before anything that writes. Ctrl+C or type 'exit' to quit.", ""]

        def confirm(name, args):
            """Ask on the bottom line whether to run a tool that writes or sends."""
            h, _ = stdscr.getmaxyx()
            stdscr.addstr(h - 1, 0, f"Run {name}({', '.join(args)})? [y/N] "[: stdscr.getmaxyx()[1] - 1])
            stdscr.refresh()
            return stdscr.getkey().lower() == "y"

        def working(line):
            """Show a tool call the moment it is found, with what she is doing, before the slow part runs."""
            lines.append(line)
            redraw()
            h, w = stdscr.getmaxyx()
            stdscr.addstr(h - 1, 0, f"working: {line.strip()}"[: w - 1])
            stdscr.refresh()

        session = harness.Session(confirm=confirm, log=working)

        def redraw():
            """Repaint the transcript and the input line."""
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
            did = session.ask(question, or_none=True)
            if did is not None:
                history.append((question, did))
                for l in (f"Samantha: {did}", ""):
                    lines.extend(l.split("\n"))
                continue
            live = len(lines)
            lines.append("Samantha: ")

            def show(piece):
                """Grow her line as she writes it; the finished answer replaces it below."""
                lines[live] += piece.replace("\n", " ")
                redraw()
            answer, topic_active, last_subject = safe_turn(question, history, topic_active, last_subject, on_text=show)
            del lines[live:]
            history.append((question, answer))
            for l in (f"Samantha: {answer}", ""):
                lines.extend(l.split("\n"))

    curses.wrapper(run)


if __name__ == "__main__":
    if "--voice" in sys.argv:
        import voice
        wake = None
        if "--wake" in sys.argv:
            i = sys.argv.index("--wake") + 1
            nxt = sys.argv[i] if i < len(sys.argv) else None
            wake = nxt if nxt and not nxt.startswith("--") else voice.WAKE_WORD
        voice.converse(wake=wake)
    elif "--tui" in sys.argv:
        tui()
    else:
        chat()
