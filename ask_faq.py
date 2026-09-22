"""Samantha's project FAQ: FAQ.md parsed into question/answer pairs, a lexical matcher hardened against
false positives, an optional embedding matcher, and the exact-fact extractors. Split out of ask.py, which
re-exports every name here."""
import difflib, hashlib, html, json, math, os, re, subprocess, sys, time, urllib.parse, urllib.request

REPO = os.path.dirname(os.path.abspath(__file__))

# words that mark a question as about this project; project_vocabulary() adds the FAQ's own words
PROJECT_KEYWORDS = {
    "turing", "samantha", "arthur", "lora", "faq", "roadmap", "ask.py",
    "chat.py", "brain", "mlx", "qwen", "phase", "whitepaper", "readme",
    "claude.md", "extractor", "fixed_fact", "faq_match", "adapter",
    "project", "repo", "repository", "model",
}


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
    with open(FAQ_PATH, encoding="utf-8") as f:
        text = f.read()
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
