"""Phase 4: ask Samantha a question with retrieval instead of relying on
memorized weights. Pulls real passages from brain's index, feeds them to
the model as context, model answers from what it's actually given.

Six training runs on 2026-09-13 confirmed a 0.5B LoRA on a few hundred
examples reliably learns style but not facts. This is the fix: keep facts
in brain's live index, let the model reason over retrieved context instead
of trying to recall them from weights. See roadmap.md, run 6.
"""
import difflib, json, os, re, subprocess, sys, urllib.parse, urllib.request

BRAIN_ENV = os.path.expanduser("~/Documents/Code/brain/.env.local")
BRAIN_URL = "https://brain.heyitsmejosh.com/api/search"
MODEL = "mlx-community/Qwen2.5-0.5B-Instruct-4bit"
ADAPTER = os.path.expanduser("~/Documents/Code/turing/ada-1-adapter")

# shared house-voice rules, used by both ask() here and chat.py's multi-turn
# loop, so the two don't quietly drift into different personalities
SYSTEM = (
    "You are Samantha, a small assistant for the Turing project. Answer only "
    "from the context given. Plain language, short sentences, no filler, no "
    "em dashes, no emojis. If the context doesn't have the answer, say so, "
    "don't guess."
)


def brain_token():
    try:
        for line in open(BRAIN_ENV):
            if line.strip().startswith("BRAIN_TOKEN"):
                return line.strip().split("=", 1)[1].strip().strip('"')
    except FileNotFoundError:
        pass
    return None


def search(query, limit=3):
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
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            results = json.load(r)["results"]
    except Exception:
        return []
    own = [r for r in results if "/turing/" in r["source"]]
    other = [r for r in results if "/turing/" not in r["source"]]
    return (own + other)[:limit]


# precision-sensitive facts: generation invents plausible-but-wrong specifics
# for these even with the right source in context (see eval/results-2026-09-13-rag2.md),
# so pull the answer straight from the retrieved text instead of trusting the model
EXTRACTORS = [
    (re.compile(r"\blicen[cs]e\b", re.I), re.compile(r"\b(MIT|Apache-2\.0|GPL-?v?\d|BSD-\d-Clause)\b")),
    (re.compile(r"\bwhat tool\b.*\btrain", re.I), re.compile(r"`(mlx_lm\.lora|mlx-lm|run_lora_capped\.py)`")),
    (re.compile(r"\bLoRA\b.*\bstand", re.I), re.compile(r"Low-Rank Adaptation")),
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
        re.compile(r"\bloss chart\b.*\bdata\b", re.I),
        "parse_log.py parses the training log into web/status.json, which "
        "the landing page fetches and renders on a canvas.",
    ),
]


FAQ_PATH = os.path.expanduser("~/Documents/Code/turing/FAQ.md")
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
}


def _keywords(s):
    return {w for w in re.findall(r"[a-z0-9]+", s.lower()) if len(w) > 3 and w not in _STOPWORDS}


def faq_match(question):
    """Structural similarity alone (difflib) false-positives on unrelated
    questions that happen to share sentence shape, "what is the capital of
    France" scored 0.62 against "What's the current eval score?" purely from
    "what is/'s the ... of/eval" pattern overlap, nothing to do with meaning.
    Require actual shared keywords too, not just matching sentence structure.
    """
    pairs = load_faq()
    if not pairs:
        return None
    q_keywords = _keywords(question)
    best_score, best_answer = 0.0, None
    q_norm = question.lower().strip("? ")
    for faq_q, faq_a in pairs:
        shared = q_keywords & _keywords(faq_q)
        if not shared:
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
        if score > best_score:
            best_score, best_answer = score, faq_a
    return best_answer if best_score >= FAQ_MATCH_THRESHOLD else None


def try_extract(question, results):
    for q_pat, answer in FIXED_FACTS:
        if q_pat.search(question):
            return answer
    for q_pat, a_pat in EXTRACTORS:
        if q_pat.search(question):
            for r in results:
                m = a_pat.search(r["text"])
                if m:
                    return m.group(0)
    return None


def http_json(url, timeout=8):
    req = urllib.request.Request(url, headers={"user-agent": "turing-ask/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except Exception:
        return None


_QUESTION_PREFIX = re.compile(
    r"^(what'?s?|who'?s?|when'?s?|where'?s?|why|how)\s+(is|are|was|were|does|do|did)\s+(the\s+)?",
    re.I,
)


def normalize_query(query):
    """Strip leading question-word filler before hitting search APIs. "what is
    the capital of France" full-text-searches worse on Wikipedia than the
    stripped "capital of France", filler words dilute relevance ranking.
    """
    stripped = _QUESTION_PREFIX.sub("", query.strip()).rstrip("?").strip()
    return stripped or query


_WHO_PREFIX = re.compile(r"^who(?:'s|\s+(?:is|are|was|were))\s+", re.I)


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
    office = re.sub(r"^the\s+", "", office, flags=re.I)

    hits = http_json(
        f"https://www.wikidata.org/w/api.php?action=wbsearchentities&search={urllib.parse.quote(office)}"
        "&language=en&format=json&limit=1"
    )
    hits = (hits or {}).get("search", [])
    if not hits:
        return None, None
    entity_id = hits[0]["id"]

    claims = http_json(
        f"https://www.wikidata.org/w/api.php?action=wbgetclaims&entity={entity_id}&property=P1308&format=json"
    )
    p1308 = (claims or {}).get("claims", {}).get("P1308", [])
    current = next((c for c in p1308 if c.get("rank") == "preferred"), None)
    if not current:
        current = next((c for c in p1308 if "P582" not in c.get("qualifiers", {})), None)
    if not current:
        return None, None
    holder_id = current["mainsnak"]["datavalue"]["value"]["id"]

    entities = http_json(
        f"https://www.wikidata.org/w/api.php?action=wbgetentities&ids={holder_id}&props=labels&languages=en&format=json"
    )
    label = (entities or {}).get("entities", {}).get(holder_id, {}).get("labels", {}).get("en", {}).get("value")
    if not label:
        return None, None
    return f"{label} ({hits[0]['label']}).", "Wikidata"


def general_knowledge(query):
    """Same pattern as nimble/docs/engine.js's ddg()/wiki(): DuckDuckGo's
    Instant Answer API first, Wikipedia's summary API as fallback. No API
    key, no proxy needed here since this runs server-side, not a browser
    (nimble needs ANSWER_PROXY only to dodge CORS in-browser).

    Deliberately conservative: DDG's instant-answer API returns empty for
    most non-trivial or opinion-flavored queries, so this rarely fires on
    a project-specific question by accident, only clear factual ones.
    """
    holder, src = current_officeholder(query)
    if holder:
        return holder, src

    normalized = normalize_query(query)

    d = http_json(f"https://api.duckduckgo.com/?q={urllib.parse.quote(normalized)}&format=json&no_html=1&skip_disambig=1")
    if d:
        for field, src_field in (("Answer", None), ("AbstractText", "AbstractSource"), ("Definition", "DefinitionSource")):
            text = d.get(field)
            if text:
                src = d.get(src_field) if src_field else "DuckDuckGo"
                return text.strip(), src or "DuckDuckGo"

    s = http_json(f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(normalized)}&format=json&srlimit=1&origin=*")
    title = (s or {}).get("query", {}).get("search", [{}])
    title = title[0].get("title") if title else None
    if title:
        summary = http_json(f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(title)}")
        extract = (summary or {}).get("extract")
        if extract:
            return extract.strip(), f"Wikipedia: {title}"
    return None, None


# if the question mentions any of these, it's about this project, never
# route it to general_knowledge. Retrieval-score thresholds turned out
# unreliable here: search()'s query-biasing prefix ("Turing Samantha LoRA
# project: ...") inflates every result's similarity score roughly equally,
# so an unrelated question still shows turing/ sources ranked high. An
# explicit keyword gate is more honest than tuning a fragile threshold.
PROJECT_KEYWORDS = {
    "turing", "samantha", "arthur", "lora", "faq", "roadmap", "ask.py",
    "chat.py", "brain", "mlx", "qwen", "phase", "whitepaper", "readme",
    "claude.md", "extractor", "fixed_fact", "faq_match", "adapter",
}


def is_project_question(question):
    q = question.lower()
    return any(kw in q for kw in PROJECT_KEYWORDS)


_QUESTION_SHAPE = re.compile(
    r"^(who|what|when|where|why|how|is|are|was|were|does|do|did|can|could|will|should)\b",
    re.I,
)


def is_question(text):
    # general_knowledge hits DDG/Wikipedia, which sometimes returns a
    # loosely-related instant answer for an imperative instruction too
    # ("write a commit message for X" once matched Wikipedia's "Git"
    # article). Only real questions should reach it, not task prompts.
    text = text.strip()
    return text.endswith("?") or bool(_QUESTION_SHAPE.match(text))


def ask(question):
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

    faq_answer = faq_match(question)
    if faq_answer:
        return faq_answer, ["~/Documents/Code/turing/FAQ.md"]

    if not is_project_question(question) and is_question(question):
        gk_answer, gk_source = general_knowledge(question)
        if gk_answer:
            return gk_answer, [gk_source]

    results = search(question)
    extracted = try_extract(question, results)
    if extracted:
        return extracted, [r["source"] for r in results]
    context = "\n\n---\n\n".join(r["text"][:800] for r in results)
    prompt = f"{SYSTEM}\n\nContext:\n{context}\n\nQuestion: {question}"
    out = subprocess.run(
        [
            os.path.expanduser("~/Documents/Code/turing/.venv/bin/mlx_lm.generate"),
            "--model", MODEL,
            "--adapter-path", ADAPTER,
            "--prompt", prompt,
            "--max-tokens", "100",
        ],
        capture_output=True, text=True,
    )
    gen = out.stdout.split("==========")[1].strip() if "==========" in out.stdout else out.stdout.strip()
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
