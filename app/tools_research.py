"""Deep research: "research X" reads several sources and writes a short brief that cites them. Wikipedia's top
articles for the topic, her offline library, your own notes, and a page named right in the question (a URL, or a
site named when Wikipedia has no article) are the sources; the passages that matter go to the biggest local model
(tools_llm: oMLX, then Ollama), which writes four to six sentences with a [n] after each claim. Then the brief is
checked: a sentence with a number no source contains, or with no citation, is dropped, and if nothing survives she
says so. A named page that will not read back (JS-only, blocked, down) is admitted honestly, not silently dropped.
"Tell me more about X" reuses the sources already gathered for the last brief before it searches again. Nothing
leaves the Mac except the Wikipedia reads and any page fetch the question itself named.
"""
import os
import re
import urllib.parse

ARTICLES = 4  # Wikipedia articles read per topic
PASSAGE = 1800  # characters of each source handed to the writer
PROMPT = ("Write a research brief on: {topic}\n\nUse ONLY the numbered sources below. Write four to six plain sentences. "
          "After every sentence put the number of the source it came from in brackets, like [2]. If the sources do not "
          "cover something, leave it out. No headings, no lists, no em dashes.\n\n{sources}")

# a URL, or a bare domain, named right in the question: "research https://x.com/docs", "research the docs at
# example.com/api", "research news on bbc.com". Deliberately narrow: it only fires on something that looks like a
# real host, never on an ordinary word, so a plain topic never tries to fetch itself as a page.
_NAMED_PAGE = re.compile(r"(https?://\S+|\b(?:[a-z0-9-]+\.)+(?:com|org|net|io|dev|edu|gov|co)\b\S*)", re.I)


def _named_page(topic):
    """A URL named in the topic, normalized to an http(s) address, or None."""
    m = _NAMED_PAGE.search(topic)
    if not m:
        return None
    url = m.group(1).rstrip(".,)")
    return url if url.startswith("http") else f"https://{url}"


def _wikipedia(topic):
    """(title, text) for the top Wikipedia articles on a topic, full plain text, or [] when unreachable."""
    from ask_web import http_json
    base = "https://en.wikipedia.org/w/api.php?format=json&origin=*&"
    found = http_json(base + urllib.parse.urlencode({"action": "query", "list": "search", "srsearch": topic, "srlimit": ARTICLES}))
    titles = [h["title"] for h in (found or {}).get("query", {}).get("search", []) if not h["title"].startswith("List of")]
    out = []
    for title in titles:
        page = http_json(base + urllib.parse.urlencode({"action": "query", "prop": "extracts", "explaintext": 1,
                                                          "redirects": 1, "titles": title}))
        for p in (page or {}).get("query", {}).get("pages", {}).values():
            if len(p.get("extract") or "") > 200:
                out.append((f"Wikipedia: {p['title']}", p["extract"]))
    return out


def sources(topic):
    """Every source for a topic as (name, passage), the parts of each that share the most words with the topic."""
    import library
    import tools_util
    found = _wikipedia(topic)
    page_url = _named_page(topic)
    if page_url:
        from ask_web import fetch_text
        text = fetch_text(page_url)
        if text:
            found.append((f"Page: {page_url}", text))
        # unreadable (JS-only, blocked, down): no source added here. research() checks _named_page again
        # and says so honestly instead of pretending the page was never asked for.
    shelf, name = library.look_up(topic if topic.lower().startswith(("what", "who")) else f"what is {topic}")
    if shelf:
        found.append((name, shelf))
    try:
        from ask import search
        found += [(f"Notes: {r.get('source', 'notes')}", r["text"]) for r in search(topic, limit=2)]
    except Exception:
        pass  # notes are optional: no brain token means no notes, not no brief
    seen, out = set(), []
    for name, text in found:
        if name not in seen:
            seen.add(name)
            out.append((name, tools_util._passages(text, topic, limit=PASSAGE)))
    return out


def check(brief, texts):
    """Keep only sentences that cite a real source and whose numbers all appear in the sources."""
    allowed = set(range(1, len(texts) + 1))
    corpus = " ".join(texts).lower()
    keep = []
    for sentence in re.split(r"(?<=[.!?\]])\s+", brief.strip()):
        cited = {int(n) for n in re.findall(r"\[(\d+)\]", sentence)}
        numbers = re.findall(r"\d[\d,.]*\d|\d", re.sub(r"\[\d+\]", "", sentence))
        if cited and cited <= allowed and all(n.rstrip(".,") in corpus for n in numbers):
            keep.append(sentence.strip())
    return " ".join(keep)


_last = {"topic": None, "brief": None, "sources": None}  # the most recent brief this process wrote, and the
# sources behind it, for "save that" and "tell me more"


def _slug(topic):
    """A filesystem-safe file name from a topic."""
    return re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")[:60] or "brief"


def _write_target(path):
    """Where a brief may be saved: inside the home folder, no hidden folders, or None if not."""
    home = os.path.realpath(os.path.expanduser("~"))
    full = os.path.realpath(os.path.expanduser(path.strip().strip("'\"")))
    rel = os.path.relpath(full, home)
    if rel.startswith("..") or any(part.startswith(".") and part != "." for part in rel.split(os.sep)):
        return None
    return full


def save_research(path=""):
    """Save the last research brief to a file (default ~/Desktop/research-<topic>.md). Asks first."""
    if not _last["brief"]:
        return "I have not researched anything yet this session. Ask me to research something first."
    path = path.strip() or f"~/Desktop/research-{_slug(_last['topic'])}.md"
    if not path.lower().endswith((".md", ".txt")):
        path += ".md"
    full = _write_target(path)
    if not full:
        return f"I can only save inside your home folder, not {path}."
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w") as f:
        f.write(f"# {_last['topic']}\n\n{_last['brief']}\n")
    return f"Saved to {full}."


def _brief_from(topic, found):
    """Write and check a brief from an already-gathered source list, or None if nothing survived."""
    numbered = "\n\n".join(f"[{i}] {name}\n{text}" for i, (name, text) in enumerate(found, 1))
    import tools_llm
    brief = tools_llm.ask_llm(PROMPT.format(topic=topic, sources=numbered))
    brief = brief.rsplit("\n(Answered by", 1)[0]
    kept = check(brief, [t for _, t in found])
    if not kept:
        return None, brief
    cites = "\n".join(f"[{i}] {name}" for i, (name, _) in enumerate(found, 1) if f"[{i}]" in kept)
    return f"{kept}\n\nSources:\n{cites}", brief


def research(topic):
    """Research a topic: read Wikipedia, her library, your notes, and a page the question named, and write a short
    brief citing each source. A named page that would not read back is admitted, not swallowed."""
    topic = topic.strip().rstrip("?.!")
    if not topic:
        return 'Research what? Say it like "research the history of the printing press".'
    found = sources(topic)
    page_url = _named_page(topic)
    page_missing = page_url and not any(name.startswith("Page:") for name, _ in found)
    decline = f" I couldn't read {page_url} here, it may be JS-only, behind a login, or blocking this." if page_missing else ""
    if not found:
        return f"I could not find sources on {topic}.{decline or ' The web may be unreachable; try again in a minute.'}"
    result, brief = _brief_from(topic, found)
    if result is None:
        return f"I read {len(found)} sources on {topic} but could not write a brief I can stand behind.{decline} {brief if brief.startswith(('I could not', 'The local model')) else ''}".strip()
    _last["topic"], _last["brief"], _last["sources"] = topic, result, found
    return result + decline


def research_more(topic=""):
    """Follow-up on the last brief: "tell me more about X" tries the sources already gathered before searching
    again. Only when they don't say enough about the new angle does it go back out for fresh sources."""
    topic = topic.strip().rstrip("?.!")
    if not _last["brief"]:
        return "I have not researched anything yet this session. Ask me to research something first."
    angle = f"{_last['topic']}, more detail on {topic}" if topic else f"{_last['topic']}, more detail"
    old = _last["sources"] or []
    if old:
        result, _ = _brief_from(angle, old)
        if result:
            _last["brief"] = result
            return result
    # the sources already gathered didn't cover it: search again, same as a fresh research() call
    return research(f"{_last['topic']} {topic}".strip())
