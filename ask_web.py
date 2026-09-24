"""Samantha's web lookups: a cached JSON fetcher, the live officeholder lookup on Wikidata, the local reader that
answers from one article, and the guards that decline a title coincidence. Split out of ask.py, which re-exports every
name here and keeps general_knowledge, the chain that uses them.
"""
import difflib, hashlib, html, json, math, os, re, subprocess, sys, time, urllib.parse, urllib.request

REPO = os.path.dirname(os.path.abspath(__file__))

from ask_faq import _keywords  # noqa: E402
from ask_local import _QUESTION_PREFIX  # noqa: E402

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



def fetch_text(url, limit=3000):
    """Fetch any http(s) page and strip it down to readable text, or None if it could not be read (network
    error, blocked, or a JS-only page that renders nothing server-side). Shared by tools.read_page and
    tools_research.sources, so both read a page the same honest way: tags stripped, nothing beyond what
    was actually served."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Macintosh) Samantha"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            raw = r.read(400_000).decode("utf-8", "ignore")
    except Exception:
        return None
    raw = re.sub(r"(?is)<(script|style|noscript|svg)\b.*?</\1>", " ", raw)
    text = html.unescape(re.sub(r"<[^>]+>", " ", raw))
    # tag-strip, not a readability parser. JS-rendered pages come back near-empty; that is the honest signal
    # that this page cannot be read this way, not a bug to paper over.
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit] if len(text) > 200 else None


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
