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


FETCH_FAILED = object()  # sentinel: the request itself failed, not "no result"


HTTP_CACHE = os.path.join(REPO, ".http_cache.json")
HTTP_CACHE_TTL = 24 * 60 * 60  # a Wikipedia summary does not change hourly
_http_cache = None


def _cache_load():
    """Load the HTTP response cache from disk, initialize if missing."""
    global _http_cache
    if _http_cache is None:
        try:
            _http_cache = json.load(open(HTTP_CACHE))
        except Exception:
            _http_cache = {}
    return _http_cache


def _cache_get(url):
    """Retrieve cached HTTP response if it exists and is not stale."""
    entry = _cache_load().get(hashlib.sha256(url.encode()).hexdigest())
    if not entry:
        return None
    if time.time() - entry.get("t", 0) > HTTP_CACHE_TTL:
        return None
    return entry.get("body")


def _cache_put(url, body):
    """Store HTTP response in cache with a timestamp."""
    cache = _cache_load()
    cache[hashlib.sha256(url.encode()).hexdigest()] = {"t": time.time(), "body": body}
    try:
        json.dump(cache, open(HTTP_CACHE, "w"))
    except OSError:
        pass  # a read-only checkout still works, it just refetches


def http_json(url, timeout=8, on_error=None):
    """Returns parsed JSON, or `on_error` if the request failed.

    Successful responses are cached on disk for a day. Wikipedia summaries
    and Wikidata claims do not change hour to hour, and re-fetching them is
    what got this session rate-limited by *both* services badly enough that
    an eval run scored 9/20 through a dead network while the code was fine.
    Caching is the actual fix for that, not pacing: a repeated question
    costs nothing, and a rerun of the eval suite hits the network only for
    questions it has never asked before.

    Failures are deliberately never cached, so a throttled minute doesn't
    get frozen in for a day.

    The default keeps every existing caller unchanged, but a caller that
    needs to tell "the network is down" apart from "the service answered,
    and the answer was empty" can pass `on_error=FETCH_FAILED`. Collapsing
    both into None is what let a transient Wikidata outage masquerade as
    "this isn't an officeholder question", see current_officeholder.
    """
    cached = _cache_get(url)
    if cached is not None:
        return cached
    req = urllib.request.Request(url, headers={"user-agent": "turing-ask/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = json.load(r)
    except Exception:
        return on_error
    _cache_put(url, body)
    return body




_LOOKUP_PREFIX = re.compile(r"^(?:tell me (?:about|of)|explain|describe|define|what do you know about)\s+(?:the\s+)?", re.I)


def normalize_query(query):
    """Strip leading question-word filler before hitting search APIs. "what is
    the capital of France" full-text-searches worse on Wikipedia than the
    stripped "capital of France", filler words dilute relevance ranking.
    """
    # "tell me about ada lovelace" searched whole ranked Lord Byron first and
    # "tell me about tokyo" ranked a samurai: the filler carried the search.
    stripped = _LOOKUP_PREFIX.sub("", _QUESTION_PREFIX.sub("", query.strip())).rstrip("?").strip()
    return stripped or query


_WHO_PREFIX = re.compile(r"^who(?:'s|\s+(?:is|are|was|were))\s+", re.I)

UNREACHABLE = "__lookup_unreachable__"  # source marker, not a real source
OUT_OF_SCOPE = (
    "I couldn't find anything on that, and it's outside what I know about "
    "this project, so I'm not going to make something up."
)

NETWORK_DOWN = (
    "I couldn't reach the web to look that up just now, so I don't know. "
    "Not going to guess."
)

LOOKUP_FAILED = (
    "I couldn't reach Wikidata to look that up just now, so I don't know "
    "who currently holds it. Not going to guess at a name."
)


def current_officeholder(query):
    """DDG/Wikipedia summaries describe the office, not who holds it right
    now (documented limitation, see FAQ.md). Wikidata's structured claims
    fix this for "who is the president/prime minister/king of X" style
    questions: find the position entity, read its P1308 (officeholder)
    claim, skip any claim that has a P582 (end time) qualifier since that
    means someone already replaced them.

    Only fires on "who is/who's" questions, not a general lookup, so it
    stays a narrow fix for the pattern it actually solves.

    Picking the right claim: fixed-term offices (president, etc.) have
    Wikidata's expected end-of-term date pre-filled on the *current*
    holder too, so "no end date" isn't a valid current-holder signal.
    Wikidata's own `rank: preferred` is, that is exactly how its editors
    flag which value among several historical ones is current.
    """
    if not _WHO_PREFIX.match(query.strip()):
        return None, None
    # normalize_query's own prefix regex expects a second verb after "who's"
    # ("who's is"), which never happens for a contraction, so strip the
    # who-prefix here first instead of relying on it.
    office = _WHO_PREFIX.sub("", query.strip()).rstrip("?").strip()
    # confirmed live: "who is the CURRENT prime minister of Canada" broke
    # the Wikidata entity search entirely (silently returned no hits,
    # since Wikidata's entity is just "Prime Minister of Canada", not
    # "current prime minister of Canada"), which then fell through to a
    # wrong FAQ answer describing this very feature instead of using it.
    # Strip these filler words too, not just "the", they add no entity
    # identity of their own, every officeholder answer is already "as of
    # now" by definition (see current_officeholder's own docstring).
    office = re.sub(r"^(?:(?:the|current|present|sitting)\s+)+", "", office, flags=re.I)

    # A failed request and a genuine "Wikidata has no such office" both used
    # to return None here, and the caller could only read that as "not an
    # officeholder question, carry on". Confirmed live with Wikidata stubbed
    # out: "who is the current prime minister of canada" fell through and
    # answered with FAQ.md's own entry *describing this very feature* ("Yes,
    # as of 2026-09-13. DDG and a plain Wikipedia summary both describe the
    # office..."), documentation about itself presented as the answer. The
    # v0.7.4 entry logged this as a known resilience gap and left it. Keep
    # the two apart so a transient outage can be admitted instead of faked.
    hits = http_json(
        f"https://www.wikidata.org/w/api.php?action=wbsearchentities&search={urllib.parse.quote(office)}"
        "&language=en&format=json&limit=1",
        on_error=FETCH_FAILED,
    )
    if hits is FETCH_FAILED:
        return None, UNREACHABLE
    hits = (hits or {}).get("search", [])
    if not hits:
        return None, None
    entity_id = hits[0]["id"]

    claims = http_json(
        f"https://www.wikidata.org/w/api.php?action=wbgetclaims&entity={entity_id}&property=P1308&format=json",
        on_error=FETCH_FAILED,
    )
    if claims is FETCH_FAILED:
        return None, UNREACHABLE
    p1308 = (claims or {}).get("claims", {}).get("P1308", [])
    current = next((c for c in p1308 if c.get("rank") == "preferred"), None)
    if not current:
        current = next((c for c in p1308 if "P582" not in c.get("qualifiers", {})), None)
    if not current:
        return None, None
    holder_id = current["mainsnak"]["datavalue"]["value"]["id"]

    entities = http_json(
        f"https://www.wikidata.org/w/api.php?action=wbgetentities&ids={holder_id}&props=labels&languages=en&format=json",
        on_error=FETCH_FAILED,
    )
    if entities is FETCH_FAILED:
        return None, UNREACHABLE
    label = (entities or {}).get("entities", {}).get(holder_id, {}).get("labels", {}).get("en", {}).get("value")
    if not label:
        return None, None
    return f"{label} ({hits[0]['label']}).", "Wikidata"



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


READER_MODEL = "qwen3:1.7b"
READER_URL = "http://localhost:11434/api/chat"


_ECHO_FILLER = {"your", "my", "our", "their", "his", "her", "its", "this", "that", "these", "those"}


def _is_definition_of(query, title):
    """Check if article title directly answers the question by name match.

    True when the article IS the thing asked about, so its summary is the
    answer. "who is marie curie" against "Marie Curie": yes. "who invented the
    telephone" against "Telephone": no, the page is about the right topic and
    its first sentence is still not an answer."""
    # Equal, not contained. "what do bees make" sits inside the title "Bees
    # Make Honey" and that page is a band, not a definition of anything asked.
    # A bracket on the title only says which one: "Mercury (planet)".
    asked = set(_keywords(normalize_query(query)))
    return bool(asked) and asked == set(_keywords(re.sub(r"\s*\([^)]*\)", "", title)))


def read_article(query, title):
    """Found the right page, now actually read it. QA sweep 2026-09-20: eight
    of eighteen misses were the first sentence of a correct article returned as
    if it answered the question ("what year did world war 2 end" got the war's
    opening line). The small model reads, it does not recall: it sees the text
    and may only answer from it, and the answer is checked against that text
    before anyone sees it. Returns a sentence or None.
    """
    key = f"reader3:{READER_MODEL}:{title}:{query.lower().strip()}"
    cached = _cache_get(key)
    if cached is not None:
        return cached or None
    page = http_json("https://en.wikipedia.org/w/api.php?action=query&prop=extracts&explaintext=1"
                     f"&exsectionformat=plain&redirects=1&titles={urllib.parse.quote(title)}&format=json&origin=*")
    pages = ((page or {}).get("query") or {}).get("pages") or {}
    text = next(iter(pages.values()), {}).get("extract", "")[:7000]
    if not text or "may refer to" in text[:300]:  # a disambiguation page is a list of names, never an answer
        return None
    body = json.dumps({"model": READER_MODEL, "stream": False, "think": False, "options": {"temperature": 0},
                       "messages": [
        {"role": "system", "content": "Answer the question in one short sentence using ONLY the text. If the text does not contain the answer, reply exactly UNKNOWN."},
        {"role": "user", "content": f"Text:\n{text}\n\nQuestion: {query}"}]}).encode()
    try:
        req = urllib.request.Request(READER_URL, body, {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as r:
            answer = json.load(r)["message"]["content"]
    except Exception:
        return None  # no Ollama: fall back to the old behaviour, do not cache
    answer = re.sub(r"(?s)<think>.*?</think>", "", answer).strip()
    # grounding: every number and every capitalised name in the answer has to
    # be in the page. A reader that says something the page never said is a
    # guesser, and a guess is worse than a decline.
    claims = re.findall(r"\d[\d,.]*\d|\d|\b[A-Z][a-z]{2,}\b", answer)
    asked = query.lower()
    grounded = all(c.lower().rstrip(".,") in text.lower() or c.lower() in asked for c in claims[1:] or claims)
    # the 1.7B does not always say the word it was told to say
    declined = re.search(r"unknown|does not (?:contain|mention|say|provide|specify)|doesn't (?:contain|mention|say)|not (?:mentioned|stated|specified|provided)|no (?:information|mention)", answer, re.I)
    # an answer has to bring a word the question did not have. "What Color Is Your Sky" (an album) echoes
    # "what color is the sky" back at the asker, and a pronoun swapped in for "the" is not new information.
    adds = set(_keywords(answer)) - set(_keywords(query)) - _ECHO_FILLER
    if not answer or declined or not grounded or not adds:
        answer = ""
    _cache_put(key, answer)
    return answer or None


def _reading_order(asked, found):
    """Which search hits are worth reading, best first. Two ways in. The title
    shares a word with the question, or the search snippet holds every content
    word of it: the Nile's title shares nothing with "longest river in the
    world" and its snippet says exactly that. Pages named by nothing but the
    question's own words go first. For "largest ocean" that is Ocean, ahead of
    Ocean sunfish, whose page gave a confident answer about a fish.
    """
    topic, rest = [], []
    for h in found:
        title = h["title"]
        named = set(_keywords(re.sub(r"\s*\([^)]*\)", "", title)))
        if title.lower().startswith(("list of", "lists of")):
            continue  # a table of many right-looking names, the reader pulled "United States" out of a GDP list
        if re.match(r"(?:what|who|how|why|where|when)\b", title, re.I):
            continue  # a page titled like a question is a song or a book: "what color is the sky" found the album What Color Is Your Sky
        snippet = html.unescape(re.sub(r"<[^>]+>", "", h.get("snippet") or "")).lower()
        # "sixth-largest" and "one of the largest" are not "largest"
        hedged = re.search(r"\b(?:one of the|among the)\b|\w+-(?:large|long|tall|big|small|high|deep|fast|old)", snippet)
        if named and named <= asked:
            topic.append(title)
        elif asked & named or (len(asked) > 1 and asked <= set(_keywords(snippet)) and not hedged):
            rest.append(title)
    return topic + rest


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
    # "I searched and found nothing" and "I could not reach anything to
    # search" are different answers and the user deserves the true one.
    # Confirmed live: with Wikipedia rate-limiting this session, ordinary
    # questions came back "outside what I know about this project", which
    # reads as a confident scope claim when the real cause was a dead
    # network. Same principle as the Wikidata outage fix.
    return (None, None) if reachable else (None, UNREACHABLE)


# Wikipedia's fulltext search ranks by title match, so a question phrased
# as a sentence finds anything *named* like the sentence. Measured live:
# "what color is the sky" returned a country album titled "What Color Is
# Your Sky", "how many days are in a week" returned Bodybuilding.com, "what
# is the largest planet in the solar system" returned a software-licenses
# listing. Each is a confident wrong answer, the failure class this project
# treats as worse than any miss.
#
# A question asking "how many X" or "what color/year/temperature" wants a
# fact, and the article that answers it almost always names the subject.
# When the top hit shares none of the question's content words, it is a
# title coincidence, so decline instead. This cannot make a right answer
# wrong, it only converts confident nonsense into an honest miss.
_FACT_SHAPED = re.compile(r"^(?:how many|how much|what (?:color|colour|year|time|temperature))\b", re.I)

# Questions that want a number back. nimble/docs/engine.js:206 states the
# principle this encodes: "A model's number is an unsourced guess: for
# numeric answers prefer DDG when it has one." The same idea applies to an
# encyclopedia summary, which often describes a subject rather than
# answering a measurement. A value-seeking question answered with prose
# containing no digit at all is the topic, not the answer, so decline rather
# than sound confident.
#
# Worth recording honestly: this guard was written believing "how tall is
# mount everest" was such a case, because the first part of the summary
# reads "Its height was most recently measured in 2020..." and looked like
# it trailed off. Checking the whole extract rather than its opening showed
# it does give the figure, "8,848.86 m". That question was already answered
# correctly and an earlier roadmap entry saying otherwise was wrong. The
# guard still earns its place for summaries with no number at all, but the
# example that motivated it did not hold up.
_WANTS_NUMBER = re.compile(
    r"^(?:how (?:many|much|tall|long|old|far|fast|deep|high|wide|big))\b"
    r"|^what (?:year|percentage)\b"
    r"|\b(?:boiling|melting|freezing) point\b",
    re.I,
)


def _wikipedia_answer_is_plausible(query, title, extract):
    """Verify Wikipedia summary answer is relevant to the question, not a tangent."""
    subject = _keywords(query) - _keywords("what is are the a an how many much of in")
    if not subject:
        return True
    haystack = _keywords(f"{title} {extract[:300]}")
    if subject & haystack:
        return True
    # no shared subject word at all: only tolerate it for open-ended
    # questions, never for a fact-shaped one where a wrong article reads
    # as a confident answer
    return not _FACT_SHAPED.match(query.strip())


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
