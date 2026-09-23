"""Phase 4: ask Samantha a question with retrieval instead of relying on
memorized weights. Pulls real passages from brain's index, feeds them to
the model as context, model answers from what it's actually given.

Six training runs on 2026-09-13 confirmed a 0.5B LoRA on a few hundred
examples reliably learns style but not facts. This is the fix: keep facts
in brain's live index, let the model reason over retrieved context instead
of trying to recall them from weights. See roadmap.md, run 6.
"""
import difflib, hashlib, html, json, math, os, re, subprocess, sys, time, urllib.parse, urllib.request

# Every project-local path derives from this file, never from a hardcoded
# ~/Documents/Code/turing. That absolute path meant a clone anywhere else
# silently loaded an empty FAQ: CI failed on a topic-scope test for exactly
# that reason, because project_vocabulary() came back with no FAQ words in
# it and every question looked like a change of subject.
REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)
import library  # noqa: E402  (her offline library, the last stop in general_knowledge)

BRAIN_ENV = os.path.expanduser("~/Documents/Code/brain/.env.local")
BRAIN_URL = "https://brain.heyitsmejosh.com/api/search"
MODEL = "mlx-community/Qwen2.5-0.5B-Instruct-4bit"
ADAPTER = os.path.join(REPO, "ada-1-adapter")

# shared house-voice rules, used by both ask() here and chat.py's multi-turn
# loop, so the two don't quietly drift into different personalities
SYSTEM = (
    "You are Samantha, a small assistant for the Turing project. Answer only "
    "from the context given. Plain language, short sentences, no filler, no "
    "em dashes, no emojis. If the context doesn't have the answer, say so, "
    "don't guess."
)


def brain_token():
    """Load the brain API token from .env.local, or None if not found."""
    try:
        for line in open(BRAIN_ENV):
            if line.strip().startswith("BRAIN_TOKEN"):
                return line.strip().split("=", 1)[1].strip().strip('"')
    except FileNotFoundError:
        pass
    return None


def search(query, limit=3):
    """Retrieve passages from brain RAG, biased toward Turing project sources."""
    # brain is a private, personal RAG service, a fresh clone of this repo
    # won't have brain/.env.local at all. Degrade to no retrieval context
    # instead of crashing, generation still runs, just without sources.
    token = brain_token()
    if not token:
        return []
    # bias the embedding itself toward this project, brain's index spans
    # ~50 other repos and a generic question often matches them just as
    # well as it matches Turing's own docs
    biased_query = f"Turing Samantha LoRA project: {query}"
    url = f"{BRAIN_URL}?q={urllib.parse.quote(biased_query)}&limit={max(limit * 3, 10)}"
    req = urllib.request.Request(url, headers={
        "authorization": f"Bearer {token}",
        "user-agent": "turing-ask/1.0",
    })
    cached = _cache_get(url)
    if cached is not None:
        results = cached
    else:
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                results = json.load(r)["results"]
        except Exception:
            return []
        _cache_put(url, results)
    own = [r for r in results if "/turing/" in r["source"]]
    other = [r for r in results if "/turing/" not in r["source"]]
    return (own + other)[:limit]


# the FAQ matcher (ask_faq.py) and the local exact answers (ask_local.py) live in their own files; every name is re-exported here, except the FAQ vocabulary cache, which lives only in ask_faq
from ask_faq import *  # noqa: F401,F403
from ask_faq import _CANT_PIN_DOWN, _STOPWORDS, _cosine, _embed, _faq_vectors, _keywords, _stem  # noqa: F401
from ask_local import *  # noqa: F401,F403
from ask_local import _ARITH_OK, _ARITH_WORDS, _CLOCK_PATTERNS, _CONVERT_PATTERNS, _QUESTION_PREFIX, _SMALLTALK, _TEMPS, _UNITS, _from_celsius, _tidy, _to_celsius  # noqa: F401


# the web lookups (HTTP cache, officeholders, the article reader, plausibility guards) live in ask_web.py
from ask_web import *  # noqa: F401,F403
from ask_web import _ECHO_FILLER, _FACT_SHAPED, _LOOKUP_PREFIX, _WANTS_NUMBER, _WHO_PREFIX, _cache_get, _cache_load, _cache_put, _is_definition_of, _reading_order, _wikipedia_answer_is_plausible  # noqa: F401


def local_answer(query, hands=True):
    """Answers computable on this machine, exactly, with no network at all.

    Deliberately NOT gated behind is_question(). That gate exists to stop a
    task instruction ("write a commit message for X") reaching Wikipedia and
    matching a loosely-related article, which is a real risk for a *search*.
    It is no risk here: these only fire on a recognisable expression, a date
    word, or a unit pair. Gating them anyway was a real bug, "convert 100
    fahrenheit to celsius" was declined as out of scope while the exact same
    conversion answered fine through a question-shaped phrasing.

    hands=False skips the tools, for a caller that is itself a tool (web_search answering a question).

    Returns (answer, source) or (None, None).
    """
    for fn, source in ((small_talk, "small talk"), (arithmetic, "arithmetic"), (clock, "system clock"), (convert, "unit conversion")):
        exact = fn(query)
        if exact:
            return exact, source
    # actions ("open chrome", "go to hacker news"): same shape, a recognisable
    # command with one right outcome. Here so ask.py, chat.py, the TUI and
    # serve.py all get hands from one place.
    if not hands:
        return None, None
    from tools import do
    try:
        done = do(query)
    except Exception as e:
        # a tool that breaks is an honest reply, the same words the chat harness gives
        from harness import failed
        return failed([], e), "tools"
    if done:
        return done, "tools"
    return None, None


def general_knowledge(query, skip_officeholder=False, hands=True):
    """Same pattern as nimble/docs/engine.js's ddg()/wiki(): DuckDuckGo's
    Instant Answer API first, Wikipedia's summary API as fallback. No API
    key, no proxy needed here since this runs server-side, not a browser
    (nimble needs ANSWER_PROXY only to dodge CORS in-browser).

    Deliberately conservative: DDG's instant-answer API returns empty for
    most non-trivial or opinion-flavored queries, so this rarely fires on
    a project-specific question by accident, only clear factual ones.
    """
    # skip_officeholder avoids a second identical Wikidata round trip when
    # the caller has already tried it. That matters under rate limiting,
    # which is exactly when this path runs.
    exact, exact_source = local_answer(query, hands=hands)
    if exact:
        return exact, exact_source

    # A question with no content word left after stopwords has nothing to
    # look up, and both DDG and Wikipedia will happily title-match it to
    # something anyway. Confirmed live: a bare "why" returned "Why.., the
    # first extended play by the South Korean boy band BoyNextDoor".
    # Checked after arithmetic, since "2+2" has no word characters either
    # and is genuinely answerable.
    if not _keywords(query):
        return None, None

    if not skip_officeholder:
        holder, src = current_officeholder(query)
        if holder:
            return holder, src

    normalized = normalize_query(query)

    reachable = False
    d = http_json(f"https://api.duckduckgo.com/?q={urllib.parse.quote(normalized)}&format=json&no_html=1&skip_disambig=1", on_error=FETCH_FAILED)
    if d is FETCH_FAILED:
        d = None
    else:
        reachable = True
    if d:
        for field, src_field in (("Answer", None), ("AbstractText", "AbstractSource"), ("Definition", "DefinitionSource")):
            text = d.get(field)
            if text:
                if field == "AbstractText" and not _is_definition_of(query, d.get("Heading") or ""):
                    continue  # right topic, not an answer: let the reader have the page
                src = d.get(src_field) if src_field else "DuckDuckGo"
                return text.strip(), src or "DuckDuckGo"

    # Deliberately srlimit=1. Searching the top 3 and taking the first hit
    # whose summary passes the plausibility guard looked like an obvious
    # improvement (it would rescue a real article ranked behind a title
    # coincidence), and measured worse: "what is the chemical symbol for
    # gold" went from correct to answering "silver", because hit 2 and 3 are
    # frequently *related but wrong* rather than better. It also tripled
    # request volume, which made Wikipedia's rate limiting fire mid-eval and
    # turned the score itself unreliable. Reverted, measured, documented.
    s = http_json(f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(normalized)}&format=json&srlimit=6&origin=*", on_error=FETCH_FAILED)
    if s is FETCH_FAILED:
        s = None
    else:
        reachable = True
    found = [h for h in (s or {}).get("query", {}).get("search", []) if h.get("title")]
    hits = [h["title"] for h in found]
    title = hits[0] if hits else None
    if not title:
        # borrowed from nimble/docs/engine.js's wiki(): fulltext search and
        # prefix search are separate endpoints, and opensearch finds titles
        # fulltext misses entirely
        o = http_json(f"https://en.wikipedia.org/w/api.php?action=opensearch&search={urllib.parse.quote(normalized)}&limit=1&format=json&origin=*")
        try:
            title = o[1][0]
        except Exception:
            title = None
    if title:
        summary = http_json(f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(title)}")
        extract = (summary or {}).get("extract")
        # A disambiguation page is a list of things sharing a name, never an
        # answer to anything. Confirmed live: "what do bees make" returned
        # "Bees Make Honey may refer to:Bees Make Honey (band), British
        # band". Wikipedia labels these itself, so this needs no heuristic.
        if (summary or {}).get("type") == "disambiguation":
            extract = None
        if not _is_definition_of(query, title):
            # The top hit for "largest country in the world" is a list page,
            # which is a table, and a table has no sentence to read. The
            # second or third hit usually is the prose article that says it.
            asked = set(_keywords(normalize_query(query)))
            for candidate in _reading_order(asked, found)[:3]:
                # Two guards, both from real wrong answers. A page sharing no
                # word with the question is search noise ("how many days are in
                # a week" ranked Bodybuilding.com). And a "List of" page is a
                # table of many right-looking names: the reader pulled "United
                # States" out of a GDP list for "largest country", and the
                # grounding check passed because the name really was on the page.
                read = read_article(query, candidate)
                if read:
                    return read, f"Wikipedia: {candidate}"
            # The page is not the thing asked about and reading it found no
            # answer, so its summary answers some other question. "who wrote
            # 1984" came back as the plot of Murder, She Wrote this way.
            extract = None
        if extract and _wikipedia_answer_is_plausible(query, title, extract):
            return extract.strip(), f"Wikipedia: {title}"
    # The web had nothing, or could not be reached: her own library
    # (library.py, saved Wikipedia leads and the fieldbook) may still. It
    # answers only on an exact page or every word asked, and names the page.
    shelf_answer, shelf_source = library.look_up(query)
    if shelf_answer:
        return shelf_answer, shelf_source
    # "I searched and found nothing" and "I could not reach anything to
    # search" are different answers and the user deserves the true one.
    # Confirmed live: with Wikipedia rate-limiting this session, ordinary
    # questions came back "outside what I know about this project", which
    # reads as a confident scope claim when the real cause was a dead
    # network. Same principle as the Wikidata outage fix.
    return (None, None) if reachable else (None, UNREACHABLE)


# if the question mentions any of these, it's about this project, never
# route it to general_knowledge. Retrieval-score thresholds turned out
# unreliable here: search()'s query-biasing prefix ("Turing Samantha LoRA
# project: ...") inflates every result's similarity score roughly equally,
# so an unrelated question still shows turing/ sources ranked high. An
# explicit keyword gate is more honest than tuning a fragile threshold.
#
# "project"/"repo"/"repository" belong here too: confirmed live that
# "Is this project blocked?" was missing every named keyword, fell through
# to general_knowledge, and Wikipedia confidently returned "List of
# websites blocked in mainland China", a completely unrelated wrong
# answer. There's no other project this CLI could mean by "this project",
# so the bare deictic word is itself a reliable project-scope signal, not
# just the named entities.
#
# "model" too: confirmed live that "Is the model good?" (a natural
# follow-up in a Samantha conversation) matched none of the named
# keywords either, and Wikipedia confidently returned the "Bill Emerson
# Good Samaritan Food Donation Act", a completely unrelated law. Same
# reasoning as "project": there's no other model this CLI could mean.
def is_project_question(question):
    """Return True if question contains project keywords or is scoped to Turing."""
    q = question.lower()
    # ponytail: the one name that collides with the repo. "who was alan turing"
    # got the project FAQ. If a second collision ever shows up, make it a list.
    if "alan turing" in q:
        return False
    return any(kw in q for kw in PROJECT_KEYWORDS)


_QUESTION_SHAPE = re.compile(
    r"^(who|what|when|where|why|how|is|are|was|were|does|do|did|can|could|will|should)\b",
    re.I,
)


# "tell me about X" is a request to look something up, not a task to
# perform, but it has no question mark and starts with a verb, so the
# question-shape test rejected it. Confirmed live: "tell me about
# photosynthesis" was declined as out of scope, an obviously answerable
# question. Kept as an explicit short list rather than loosening the rule,
# because the rule exists to stop "write a commit message for X" reaching
# Wikipedia and matching its Git article.
_LOOKUP_IMPERATIVE = re.compile(r"^(?:tell me about|explain|describe|define)\b", re.I)


def is_question(text):
    """Return True if text looks like a question, not a task instruction."""
    # general_knowledge hits DDG/Wikipedia, which sometimes returns a
    # loosely-related instant answer for an imperative instruction too
    # ("write a commit message for X" once matched Wikipedia's "Git"
    # article). Only real questions should reach it, not task prompts.
    text = text.strip()
    return (text.endswith("?") or bool(_QUESTION_SHAPE.match(text))
            or bool(_LOOKUP_IMPERATIVE.match(text)))


def ask(question):
    """Answer a question using local knowledge, FAQ matching, and retrieval-augmented generation."""
    # exact local answers first: no network, no ambiguity, and not subject
    # to the is_question() gate further down (see local_answer's docstring)
    exact, exact_source = local_answer(question)
    if exact:
        return exact, [exact_source]

    # "who is/who's the X" questions about a live office (president, prime
    # minister, etc.) can never have a correct static FAQ answer, the real
    # answer changes over time. Try this before faq_match, not after,
    # otherwise a coincidental lexical match (e.g. "current president" vs.
    # the FAQ's own "current eval score" entry) can win by accident. See
    # roadmap.md for the false-positive this caught.
    if not is_project_question(question) and _WHO_PREFIX.match(question.strip()):
        holder, holder_source = current_officeholder(question)
        if holder:
            return holder, [holder_source]
        # The lookup was attempted and the network failed, as opposed to
        # this simply not being an officeholder question. What must not
        # happen is FAQ.md answering with its own description of this
        # feature. But declining outright here was too broad: current_
        # officeholder() fires on every "who is X", not just offices, so a
        # throttled Wikidata made "who is steve jobs" decline even though
        # Wikipedia answers it perfectly. Caught by eval/basic_questions.py,
        # where running 19 questions in a row rate-limited Wikidata and all
        # four person questions declined at once. Skip the FAQ, still let
        # the encyclopedia try, and only admit defeat if it has nothing.
        if holder_source is UNREACHABLE:
            gk_answer, gk_source = general_knowledge(question, skip_officeholder=True)
            if gk_answer:
                return gk_answer, [gk_source]
            return LOOKUP_FAILED, []

    # "who was alan turing" is about a person, and FAQ.md answers it with the project's own blurb
    faq_answer = None if "alan turing" in question.lower() else faq_match(question)
    if faq_answer:
        return faq_answer, [FAQ_PATH]

    if not is_project_question(question) and is_question(question):
        gk_answer, gk_source = general_knowledge(question)
        if gk_answer:
            return gk_answer, [gk_source]
        if gk_source is UNREACHABLE:
            return NETWORK_DOWN, []

    results = search(question)
    extracted = try_extract(question, results)
    if extracted:
        return extracted, [r["source"] for r in results]
    # Same rule chat.py already applies, and it belongs here too: generating
    # for a question that isn't about the project means generating from
    # *project* retrieval context, which can only invent. chat.py got this
    # guard first and ask.py didn't, a divergence serve.py exposed
    # immediately, "asdkjfhaskdjfh" came back as garbled half-Chinese text
    # through the API while chat.py declined it cleanly.
    if not is_project_question(question):
        return OUT_OF_SCOPE, []
    context = "\n\n---\n\n".join(r["text"][:800] for r in results)
    prompt = f"{SYSTEM}\n\nContext:\n{context}\n\nQuestion: {question}"
    # generation is a ~2s subprocess that reloads the model every call, and
    # the same prompt always yields the same text, so cache it like a fetch
    cache_key = f"generate::{ADAPTER}::100::{prompt}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached, [r["source"] for r in results]
    out = subprocess.run(
        [
            os.path.join(REPO, ".venv/bin/mlx_lm.generate"),
            "--model", MODEL,
            "--adapter-path", ADAPTER,
            "--prompt", prompt,
            "--max-tokens", "100",
        ],
        capture_output=True, text=True,
    )
    gen = out.stdout.split("==========")[1].strip() if "==========" in out.stdout else out.stdout.strip()
    if gen:
        _cache_put(cache_key, gen)
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
