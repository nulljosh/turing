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


# precision-sensitive facts: generation invents plausible-but-wrong specifics
# for these even with the right source in context (see eval/results-2026-09-13-rag2.md),
# so pull the answer straight from the retrieved text instead of trusting the model
EXTRACTORS = [
    (re.compile(r"\blicen[cs]e\b", re.I), re.compile(r"\b(MIT|Apache-2\.0|GPL-?v?\d|BSD-\d-Clause)\b")),
    # Same order-dependency bug as the FIXED_FACTS fixes: the old ".*" forms
    # required "train" to appear after "what tool" / "stand" after "LoRA",
    # so natural rephrasings ("The training uses what tool?", "What does
    # the acronym stand for, LoRA?") never matched and fell through to
    # generation, which this file's own comment says invents wrong specifics
    # for exactly these facts. Confirmed both misses before the fix.
    # Lookaheads make order irrelevant, same fix as the rest of this file.
    (re.compile(r"(?=.*\bwhat tool\b)(?=.*\btrain)", re.I), re.compile(r"`(mlx_lm\.lora|mlx-lm|run_lora_capped\.py)`")),
    (re.compile(r"(?=.*\bLoRA\b)(?=.*\bstand)", re.I), re.compile(r"Low-Rank Adaptation")),
]

# fixed facts that never change and don't benefit from retrieval: "Joshua
# Trommel" appears in nearly every repo across the fleet (he's the author of
# all of them), so it's not distinctive enough for Turing-specific search to
# isolate, tried several query variants, the maintainer chunk never made the
# top 15 results. This is invariant across every project, just answer it.
FIXED_FACTS = [
    (
        # Broad "who...wrote/author" alone false-positives on any unrelated
        # "who wrote X" question (e.g. "who wrote Romeo and Juliet"), which
        # would confidently answer "Joshua Trommel" if it ever reached this
        # fallback (general_knowledge() usually intercepts those first, but
        # it can fail, and this shouldn't depend on that). Require project
        # context explicitly instead of just the verb.
        re.compile(
            r"(?=.*\bwho\b)(?=.*\b(maintain|own|wrote|author)\b)"
            r"(?=.*\b(project|repo|repository|turing|samantha)\b)",
            re.I,
        ),
        "Joshua Trommel",
    ),
    (
        # Same class of bug as the who-wrote fix above: "project" and "right
        # now" alone aren't project-specific, so "Is the Conveyer project
        # blocked right now?" or even "Why is my sink blocked right now?"
        # both matched and confidently returned Turing's canned answer.
        # Confirmed both false-positive before the fix. Also fixed an
        # order bug: the old ".*"-based pattern required "project" to appear
        # *after* "blocked", so "Is this project blocked?" never matched at
        # all, lookaheads make word order irrelevant. Require an explicit
        # reference to this project instead of the generic words alone.
        re.compile(r"(?=.*\bblocked\b)(?=.*\b(?:this project|turing|samantha)\b)", re.I),
        # NOTE: this one is a snapshot, not truly invariant, update it when
        # the real blocker changes. Hardcoded because brain has no delete
        # endpoint (see roadmap.md), so a stale pre-fix roadmap.md chunk
        # keeps outranking the current text no matter how retrieval is tuned.
        "The Qwen3.5-0.8B base comparison is blocked, it doesn't fit this "
        "machine's training memory budget even with the Metal cache-limit "
        "fix applied. Confirmed final after multiple retries, see roadmap.md.",
    ),
    (
        # Third instance of the exact same order bug as the who-wrote and
        # blocked fixes above: the old ".*" pattern required "data" to
        # appear *after* "loss chart", so "What data feeds the loss chart?",
        # a completely natural phrasing of the same real question, never
        # matched. Confirmed before the fix. Lookahead makes order
        # irrelevant, same fix shape as the other two.
        re.compile(r"(?=.*\bloss chart\b)(?=.*\bdata\b)", re.I),
        "parse_log.py parses the training log into web/status.json, which "
        "the landing page fetches and renders on a canvas.",
    ),
]


FAQ_PATH = os.path.join(REPO, "FAQ.md")
FAQ_MATCH_THRESHOLD = 0.55  # below this, a "match" is more likely coincidence than intent


def load_faq():
    """Parse FAQ.md's `## Question` / answer paragraph pairs. Structural fix for
    the whack-a-mole FIXED_FACTS approach: instead of hand-writing one entry per
    failing eval prompt, any question close enough to an existing FAQ entry gets
    that FAQ's real answer directly, no generation, no chance to invent details.
    """
    if not os.path.exists(FAQ_PATH):
        return []
    text = open(FAQ_PATH).read()
    pairs = []
    for block in re.split(r"\n## ", text)[1:]:
        lines = block.split("\n", 1)
        if len(lines) < 2:
            continue
        question, rest = lines[0].strip(), lines[1].strip()
        if question and rest:
            pairs.append((question, rest))
    return pairs


_STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "what", "who", "why", "how",
    "does", "do", "did", "this", "that", "it", "its", "to", "for", "of", "in",
    "on", "at", "be", "used", "let", "and", "or", "not", "with", "right", "now",
    "current",
    # "about" is pure filler, but being 5 letters it survived the length
    # filter and read as content. Confirmed live: right after an honest
    # decline, the follow-up "what about that" returned "What About Bob?,
    # a 1991 American comedy film", because every other word in it is
    # already a stopword and "about" alone carried the search. A question
    # made entirely of filler now has no content word left, so the
    # contentless-query guard declines it instead.
    "about",
}


EMBED_MODEL = "nomic-embed-text"
EMBED_URL = "http://localhost:11434/api/embed"
EMBED_THRESHOLD = 0.70
EMBED_CACHE = os.path.join(REPO, ".faq_embeddings.json")


def _embed(texts, timeout=8):
    """Embed via the local Ollama daemon. Returns None on any failure, which
    is a real and expected case (fresh clone, Ollama not installed or not
    running, model not pulled), never an error, the caller falls back to
    lexical matching. Timeout is deliberately short: a warm request is 0.07s,
    but the very first one after the model unloads costs ~10s to load, and
    hanging the CLI that long is worse than one lexically-matched answer
    while Ollama warms up in the background.
    """
    try:
        req = urllib.request.Request(
            EMBED_URL,
            data=json.dumps({"model": EMBED_MODEL, "input": texts}).encode(),
            headers={"Content-Type": "application/json"},
        )
        return json.load(urllib.request.urlopen(req, timeout=timeout))["embeddings"]
    except Exception:
        return None


def _faq_vectors(headers):
    """FAQ header embeddings, computed once and cached to disk. Keyed by a
    hash of the headers themselves so editing FAQ.md invalidates the cache
    automatically, no manual rebuild step to forget.
    """
    key = hashlib.sha256("\n".join(headers).encode()).hexdigest()
    try:
        cached = json.load(open(EMBED_CACHE))
        if cached.get("key") == key:
            return cached["vectors"]
    except Exception:
        pass
    # building the cache is a one-time cost, worth waiting out a model load
    vectors = _embed(headers, timeout=120)
    if vectors is None:
        return None
    try:
        json.dump({"key": key, "vectors": vectors}, open(EMBED_CACHE, "w"))
    except OSError:
        pass  # a read-only checkout still works, just recomputes each run
    return vectors


def _cosine(a, b):
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def semantic_faq_match(question, pairs):
    """Match a question to a FAQ entry by meaning instead of shared letters.

    Measured against eval/faq_paraphrase.py's 16 natural rephrasings, which
    lexical matching only got 5 of: embeddings get 12 at this threshold with
    zero wrong entries and zero out-of-scope false positives. It resolves
    exactly the cases no amount of lexical tuning could, "who works on this"
    to "Who maintains this project?" (no shared word at all), and it cleanly
    separates the pair that had precision and recall deadlocked, "why did
    arthur fail" scores 0.85 while "is my sink blocked right now" scores
    0.657, below the line, where lexically the two are the same shape.

    Threshold 0.70 rather than the 0.68 that scored one better: the highest
    out-of-scope score measured was 0.657, and this project treats a
    confident wrong answer as worse than a miss, so the extra margin is
    worth one recall point.
    """
    vectors = _faq_vectors([q for q, _ in pairs])
    if not vectors:
        return None
    qv = _embed([question])
    if not qv:
        return None
    best_score, best_answer = 0.0, None
    for (_, answer), vec in zip(pairs, vectors):
        score = _cosine(qv[0], vec)
        if score > best_score:
            best_score, best_answer = score, answer
    return best_answer if best_score >= EMBED_THRESHOLD else None


_PROJECT_VOCAB = None


def project_vocabulary():
    """Every content word the project's own FAQ uses, stemmed and cached.

    Used to tell a genuine topic change from a keywordless follow-up: a
    question whose content words are *all* absent from this vocabulary is
    not a continuation of a project conversation, whatever the sticky flag
    currently says.
    """
    global _PROJECT_VOCAB
    if _PROJECT_VOCAB is None:
        # Questions only, deliberately. Including answer text made the
        # vocabulary far too broad: FAQ answers discuss their own examples
        # ("the capital of France" appears in the write-up of a past false
        # positive), so "capital" counted as project vocabulary and "what is
        # the capital of japan" still read as a project follow-up. Headers
        # are what the FAQ is *about*; answers are prose that can mention
        # anything.
        vocab = set()
        for question, _ in load_faq():
            vocab |= _keywords(question)
        _PROJECT_VOCAB = vocab | {_stem(k) for k in PROJECT_KEYWORDS}
    return _PROJECT_VOCAB


def _stem(w):
    """Crude suffix stripping so a question and a FAQ header that use the
    same word in different forms still count as sharing it.

    Measured, not guessed: of 12 paraphrase misses, four shared no keyword
    at all purely from morphology, "what do you use to train it" against
    "What tool actually runs training?" (train/training), "how is it
    scoring on evals right now" against "What's the current eval score?"
    (scoring/score, evals/eval), "how does the faq matching work" against
    "What is the FAQ-matcher?" (matching/matcher). Nothing semantic about
    any of them, the matcher just couldn't see through an -ing.

    Trailing "e" goes too, so score/scoring collapse to the same stem
    rather than scor/score. Deliberately not a real Porter stemmer, this
    is a dozen lines against a 41-entry FAQ, and both sides get stemmed
    identically so an over-aggressive strip stays symmetric.
    """
    for suffix in ("ing", "ers", "er", "ed", "es", "s"):
        if w.endswith(suffix) and len(w) - len(suffix) >= 3:
            w = w[: -len(suffix)]
            break
    return w[:-1] if w.endswith("e") and len(w) > 3 else w


def _keywords(s):
    """Extract content words from text, excluding stopwords and short words."""
    # len > 2, not > 3: this project's most distinctive words are three-letter
    # acronyms (faq, tui, cli, api), and excluding them threw away the single
    # strongest signal a question about them carries.
    return {_stem(w) for w in re.findall(r"[a-z0-9]+", s.lower())
            if len(w) > 2 and w not in _STOPWORDS}


def faq_match(question):
    """Structural similarity alone (difflib) false-positives on unrelated
    questions that happen to share sentence shape, "what is the capital of
    France" scored 0.62 against "What's the current eval score?" purely from
    "what is/'s the ... of/eval" pattern overlap, nothing to do with meaning.
    Require actual shared keywords too, not just matching sentence structure.

    Flat keyword-overlap fraction has its own version of the same bug when
    two entries share the same *number* of keywords: it can't tell a shared
    common word from a shared rare, distinctive one. Confirmed live:
    "Is this project blocked?" (shares only "project" with one entry,
    "blocked" with another, one word each either way) scored higher against
    "Who maintains this project?" than against the actually-correct "What's
    blocked or paused right now?", purely from coincidental sentence-shape
    overlap. "project" appears in 4/37 FAQ questions, "blocked" in 1/37,
    "blocked" is the far stronger signal, but a flat count treats them the
    same.

    Tried weighting the whole overlap score by inverse document frequency
    first: it fixed this case but broke another, "difference"/"between"
    (each in only 1-2 FAQ questions, high weight) coincidentally outscored
    the actually-correct "turing"+"samantha"+"between" match, because a
    small 37-entry corpus doesn't have enough data for word rarity alone to
    reliably mean "topically distinctive" (a phrasing quirk can be just as
    rare as a real content word). So: keep flat overlap_fraction as the
    primary signal (already correct whenever the shared-keyword *count*
    actually differs, don't fix what isn't broken), and use rarity only as
    a tie-break for when two entries share the exact same number of words,
    which is the one situation flat counting genuinely can't resolve.
    """
    pairs = load_faq()
    if not pairs:
        return None
    # Semantic first, it beats the lexical path 12/16 to 5/16 on real
    # rephrasings. Falling through rather than returning on a semantic miss
    # is deliberate: the two approaches fail on different questions, and the
    # lexical path is precision-hardened (0/8 on the out-of-scope set), so
    # the union costs nothing measured and catches what embeddings rank just
    # under threshold. Falls through for free when Ollama isn't running.
    semantic = semantic_faq_match(question, pairs)
    if semantic:
        return semantic
    doc_freq = {}
    for faq_q, _ in pairs:
        for kw in _keywords(faq_q):
            doc_freq[kw] = doc_freq.get(kw, 0) + 1
    q_keywords = _keywords(question)
    q_norm = question.lower().strip("? ")
    best_key, best_score, best_answer = None, 0.0, None
    # A question's rarest content word is what it's actually about. If that
    # word appears in no FAQ question at all (document frequency 0), the
    # question is about something this FAQ has never heard of, and any
    # match is coming from generic filler overlap. Confirmed live, both
    # returning confident project answers to questions about other things:
    # "is my sink blocked right now" matched "What's blocked or paused
    # right now?" on the single word "blocked" ("sink" is unknown), and
    # "what is the difference between python and javascript" matched
    # "What's the actual difference between ask.py and chat.py?" on
    # "difference" alone. The earlier 2026-09-14 fix for the sink case
    # patched FIXED_FACTS only, this sibling path had the identical bug.
    # Requiring the match to share one of the question's minimum-df words
    # kills both: when the rarest words are unknown, nothing can share them.
    foreign = {kw for kw in q_keywords if kw not in doc_freq}
    for faq_q, faq_a in pairs:
        shared = q_keywords & _keywords(faq_q)
        # A question carrying more words this FAQ has never seen than words
        # it shares with an entry is a question about something else, and
        # the match is riding on generic filler. First attempt vetoed on
        # the rarest word being unknown at all, which killed recall outright
        # (3/16 to 0/16 on the paraphrase set): ordinary verbs like "come"
        # are unknown too, without being what the question is about. Counting
        # them against the shared words instead separates the two cases,
        # a real paraphrase shares several project words and drags in an
        # incidental unknown verb, an off-topic question shares one generic
        # word and drags in its own real subject.
        if not shared or len(foreign) >= len(shared):
            continue
        seq_ratio = difflib.SequenceMatcher(None, q_norm, faq_q.lower().strip("? ")).ratio()
        # blend in keyword-overlap fraction, pure sentence-shape similarity
        # (seq_ratio alone) can pick a lexically-similar but topically wrong
        # entry over one that shares the actual subject word, "what causes
        # Samantha to hallucinate" scored higher against "what data was
        # Samantha trained on" than against the real hallucination FAQ entry,
        # until the shared keyword fraction was weighted in too
        overlap_fraction = len(shared) / len(q_keywords) if q_keywords else 0
        score = seq_ratio * 0.5 + overlap_fraction * 0.5
        # a word absent from every FAQ question (df 0) is rarer than any
        # word that appears even once, treat it as df 1 instead of crashing
        rarity = max(1.0 / doc_freq.get(kw, 1) for kw in shared)
        key = (round(overlap_fraction, 6), round(rarity, 6), score)
        if best_key is None or key > best_key:
            best_key, best_score, best_answer = key, score, faq_a
    return best_answer if best_score >= FAQ_MATCH_THRESHOLD else None


_CANT_PIN_DOWN = (
    "I don't have that pinned down confidently from what's currently "
    "indexed, not going to guess at the specifics."
)


def try_extract(question, results):
    """Extract exact answers from retrieved context using pattern matching."""
    for q_pat, answer in FIXED_FACTS:
        if q_pat.search(question):
            return answer
    for q_pat, a_pat in EXTRACTORS:
        if q_pat.search(question):
            for r in results:
                m = a_pat.search(r["text"])
                if m:
                    return m.group(0)
            # Confirmed live: "What tool trains the adapter?" matches this
            # EXTRACTOR's question shape, but the top retrieved chunks
            # didn't happen to contain the fact (it lives in a real FAQ.md
            # entry, "## What tool actually runs training?", that just
            # didn't rank in the top results for this phrasing). Falling
            # through to generation here produced a real hallucination
            # ("Adversarial Training for Speech, ATR", fabricated). This
            # file's own top comment says generation invents wrong
            # specifics for exactly these precision-sensitive facts, so
            # once we know we're in that category, don't let it guess.
            return _CANT_PIN_DOWN
    return None


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


_QUESTION_PREFIX = re.compile(
    r"^(what'?s?|who'?s?|when'?s?|where'?s?|why|how)\s+(is|are|was|were|does|do|did)\s+(the\s+)?",
    re.I,
)


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


_ARITH_WORDS = (
    (r"\b(?:times|multiplied by)\b", "*"),
    (r"\bplus\b", "+"),
    (r"\bminus\b", "-"),
    (r"\b(?:divided by|over)\b", "/"),
    (r"\bx\b", "*"),
)
_ARITH_OK = re.compile(r"^[\d\s+\-*/().]+$")


def arithmetic(query):
    """Answer plain arithmetic locally and exactly.

    "what is 2+2" used to be sent to the web like any other question, and
    came back as a Danganronpa game; "what is 10 times 7" came back as The
    New York Times (the word "times" matched a newspaper). Both are
    confident wrong answers to questions with one exact answer, which no
    search engine should ever have been asked in the first place.

    Evaluated by walking a parsed AST with an explicit node whitelist, not
    eval(), so a crafted "question" can't execute anything. Anything that
    isn't purely numbers and operators returns None and falls through.
    """
    import ast

    expr = _QUESTION_PREFIX.sub("", query.strip().rstrip("?")).strip()
    expr = re.sub(r"^(?:what\s+(?:is|are)|calculate|compute)\s+", "", expr, flags=re.I).strip()
    for pattern, symbol in _ARITH_WORDS:
        expr = re.sub(pattern, symbol, expr, flags=re.I)
    expr = expr.strip()
    if not expr or not _ARITH_OK.match(expr) or not any(c.isdigit() for c in expr):
        return None
    if not any(op in expr for op in "+-*/"):
        return None  # a bare number isn't a question

    allowed = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant,
               ast.Add, ast.Sub, ast.Mult, ast.Div, ast.USub, ast.UAdd)
    try:
        tree = ast.parse(expr, mode="eval")
        for node in ast.walk(tree):
            if not isinstance(node, allowed):
                return None
            if isinstance(node, ast.Constant) and not isinstance(node.value, (int, float)):
                return None
        value = eval(compile(tree, "<arithmetic>", "eval"), {"__builtins__": {}}, {})
    except Exception:
        return None
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return f"{expr} = {value}"


_CLOCK_PATTERNS = (
    (re.compile(r"\bwhat(?:'s| is)?\s+(?:the\s+)?time\b", re.I), "%-I:%M %p"),
    # These must be present-tense only. The first version matched a bare
    # "what year", so "what year did world war 2 end" confidently answered
    # **2026**, the current year, to a historical question. Require an
    # explicit "is it"/"is this"/"are we in" so a question about some other
    # year falls through to a real lookup.
    (re.compile(r"\bwhat(?:'s| is)?\s+(?:the\s+)?year\s+(?:is\s+it|is\s+this|are\s+we\s+in)\b|\bwhat\s+year\s+is\s+it\b", re.I), "%Y"),
    (re.compile(r"\bwhat\s+month\s+is\s+it\b", re.I), "%B %Y"),
    (re.compile(r"\bwhat\s+day(?:\s+of\s+the\s+week)?\s+is\s+it\b", re.I), "%A"),
    (re.compile(r"\bwhat(?:'s| is)?\s+(?:today'?s?\s+)?(?:the\s+)?date\b", re.I), "%A, %B %-d, %Y"),
    (re.compile(r"\bwhat\s+is\s+today\b", re.I), "%A, %B %-d, %Y"),
)


# alias -> (dimension, factor to the dimension's base unit, display name)
_UNITS = {}
for _names, _dim, _factor, _label in [
    (("mm", "millimeter", "millimeters", "millimetre", "millimetres"), "length", 0.001, "mm"),
    (("cm", "centimeter", "centimeters", "centimetre", "centimetres"), "length", 0.01, "cm"),
    (("m", "meter", "meters", "metre", "metres"), "length", 1.0, "m"),
    (("km", "kilometer", "kilometers", "kilometre", "kilometres"), "length", 1000.0, "km"),
    (("in", "inch", "inches"), "length", 0.0254, "in"),
    (("ft", "foot", "feet"), "length", 0.3048, "ft"),
    (("yd", "yard", "yards"), "length", 0.9144, "yd"),
    (("mi", "mile", "miles"), "length", 1609.344, "mi"),
    (("mg", "milligram", "milligrams"), "mass", 0.001, "mg"),
    (("g", "gram", "grams"), "mass", 1.0, "g"),
    (("kg", "kilogram", "kilograms"), "mass", 1000.0, "kg"),
    (("oz", "ounce", "ounces"), "mass", 28.349523125, "oz"),
    (("lb", "lbs", "pound", "pounds"), "mass", 453.59237, "lb"),
    (("ml", "milliliter", "milliliters", "millilitre", "millilitres"), "volume", 0.001, "ml"),
    (("l", "liter", "liters", "litre", "litres"), "volume", 1.0, "L"),
    (("cup", "cups"), "volume", 0.2365882365, "cups"),
    (("pint", "pints"), "volume", 0.473176473, "pints"),
    (("gal", "gallon", "gallons"), "volume", 3.785411784, "gal"),
]:
    for _n in _names:
        _UNITS[_n] = (_dim, _factor, _label)

_TEMPS = {
    "c": "c", "celsius": "c", "centigrade": "c",
    "f": "f", "fahrenheit": "f",
    "k": "k", "kelvin": "k",
}

_CONVERT_PATTERNS = (
    # "convert 100 fahrenheit to celsius", "100 f in c", "what is 5 miles in km"
    re.compile(r"(-?\d+(?:\.\d+)?)\s*([a-z°]+)\s*(?:to|in|into|as)\s+([a-z°]+)", re.I),
    # "how many kilometers is 5 miles", "how many km in 5 miles"
    re.compile(r"how\s+many\s+([a-z°]+)\s+(?:is|are|in)\s+(-?\d+(?:\.\d+)?)\s*([a-z°]+)", re.I),
)


def _to_celsius(value, unit):
    """Any of celsius, fahrenheit or kelvin to celsius."""
    return {"c": value, "f": (value - 32) * 5 / 9, "k": value - 273.15}[unit]


def _from_celsius(value, unit):
    """Celsius to celsius, fahrenheit or kelvin."""
    return {"c": value, "f": value * 9 / 5 + 32, "k": value + 273.15}[unit]


def _tidy(value):
    """Round to four places and drop a trailing .0."""
    rounded = round(value, 4)
    return int(rounded) if rounded == int(rounded) else rounded


def convert(query):
    """Unit conversions, answered locally and exactly.

    Same category as arithmetic and clock: one correct answer that a search
    engine can only get wrong. Confirmed live, "how many kilometers is 5
    miles" returned an article about **available seat miles**, an airline
    capacity metric, and "convert 100 fahrenheit to celsius" was declined
    outright. Deliberately a small table of units people actually ask
    about rather than a units library, and it returns None on anything it
    doesn't recognise so the normal lookup path still runs.
    """
    text = query.strip().rstrip("?").replace("°", " ")
    for index, pattern in enumerate(_CONVERT_PATTERNS):
        match = pattern.search(text)
        if not match:
            continue
        if index == 0:
            amount, src, dst = match.group(1), match.group(2), match.group(3)
        else:
            amount, src, dst = match.group(2), match.group(3), match.group(1)
        amount = float(amount)
        src, dst = src.lower(), dst.lower()

        if src in _TEMPS and dst in _TEMPS:
            result = _from_celsius(_to_celsius(amount, _TEMPS[src]), _TEMPS[dst])
            return f"{_tidy(amount)} {src} = {_tidy(result)} {dst}"

        if src in _UNITS and dst in _UNITS:
            src_dim, src_factor, src_label = _UNITS[src]
            dst_dim, dst_factor, dst_label = _UNITS[dst]
            # refuse to convert across dimensions rather than printing a
            # confident nonsense number for "how many kg is 5 miles"
            if src_dim != dst_dim:
                return None
            return f"{_tidy(amount)} {src_label} = {_tidy(amount * src_factor / dst_factor)} {dst_label}"
    return None


def clock(query):
    """Answer date and time questions from the system clock.

    The machine knows what day it is; no search engine should be asked.
    Confirmed live: "what year is it" returned Wikipedia's **Flat Earth**
    article, because a question about the year has no searchable subject and
    the fulltext match landed on "Earth". Same category as arithmetic, one
    exact answer available locally, so it never reaches the network.
    """
    import datetime

    for pattern, fmt in _CLOCK_PATTERNS:
        if pattern.search(query):
            return datetime.datetime.now().strftime(fmt)
    return None


_SMALLTALK = (
    (re.compile(r"^(?:hi|hello|hey|yo|hiya|good (?:morning|evening|afternoon))(?: there| samantha)?[!.?]*$", re.I),
     lambda: "Hi. Ask me something, or tell me to do something on this Mac."),
    (re.compile(r"^(?:how are you|how's it going|how are things)(?: doing| today)?[!.?]*$", re.I),
     lambda: "Running fine, and ready. What do you need?"),
    (re.compile(r"^(?:thanks|thank you|thx|cheers|ty)(?: so much| samantha)?[!.?]*$", re.I), lambda: "Any time."),
    (re.compile(r"^(?:what can you do|what do you do|help|what are your (?:abilities|skills)|what can i ask you)[!.?]*$", re.I),
     lambda: abilities()),
    (re.compile(r"^(?:list|show me|what are|tell me about|which are) (?:all )?(?:of )?your tools[!.?]*$|^tools[!.?]*$", re.I), lambda: tool_list()),
)


def abilities():
    """What she can do, in one paragraph, counted from the live tool table so it never drifts."""
    import tools
    return (f"I answer questions: this project from its own docs, the rest from Wikipedia and the web, and I say so "
            f"instead of guessing. I also do things on this Mac with {len(tools.TOOLS)} tools: open apps and sites, search the web, "
            "Chrome tabs, notes, reminders, timers, music and volume, edit and paint pictures in Pixelmator, logos, math, time, "
            "dice, text, your documents and your screen. Anything that writes or sends asks you first. "
            'Try "google best pizza near me", "open pixelmator" or "make this photo black and white". Say "list your tools" for all of them.')


def tool_list():
    """Every tool she has, by name, straight from the tool table."""
    import tools
    return f"{len(tools.TOOLS)} tools: " + ", ".join(n.replace("_", " ") for n in sorted(tools.TOOLS)) + "."


def small_talk(query):
    """A greeting, a thanks, or "what can you do": a fixed, honest reply, no model and no lookup.
    Anchored to the whole message, so "hey calculate 8 + 8" and "help me find a file" still reach the tools."""
    q = query.strip()
    return next((reply() for pattern, reply in _SMALLTALK if pattern.match(q)), None)


def local_answer(query):
    """Answers computable on this machine, exactly, with no network at all.

    Deliberately NOT gated behind is_question(). That gate exists to stop a
    task instruction ("write a commit message for X") reaching Wikipedia and
    matching a loosely-related article, which is a real risk for a *search*.
    It is no risk here: these only fire on a recognisable expression, a date
    word, or a unit pair. Gating them anyway was a real bug, "convert 100
    fahrenheit to celsius" was declined as out of scope while the exact same
    conversion answered fine through a question-shaped phrasing.

    Returns (answer, source) or (None, None).
    """
    for fn, source in ((small_talk, "small talk"), (arithmetic, "arithmetic"), (clock, "system clock"), (convert, "unit conversion")):
        exact = fn(query)
        if exact:
            return exact, source
    # actions ("open chrome", "go to hacker news"): same shape, a recognisable
    # command with one right outcome. Here so ask.py, chat.py, the TUI and
    # serve.py all get hands from one place.
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


def general_knowledge(query, skip_officeholder=False):
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
    exact, exact_source = local_answer(query)
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
PROJECT_KEYWORDS = {
    "turing", "samantha", "arthur", "lora", "faq", "roadmap", "ask.py",
    "chat.py", "brain", "mlx", "qwen", "phase", "whitepaper", "readme",
    "claude.md", "extractor", "fixed_fact", "faq_match", "adapter",
    "project", "repo", "repository", "model",
}


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
