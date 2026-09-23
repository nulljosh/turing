"""Deep research: "research X" reads several sources and writes a short brief that cites them. Wikipedia's top
articles for the topic, her offline library and your own notes are the sources; the passages that matter go to the
biggest local model (tools_llm: oMLX, then Ollama), which writes four to six sentences with a [n] after each claim.
Then the brief is checked: a sentence with a number no source contains, or with no citation, is dropped, and if
nothing survives she says so. Nothing leaves the Mac except the Wikipedia reads.
"""
import re
import urllib.parse

ARTICLES = 4  # Wikipedia articles read per topic
PASSAGE = 1800  # characters of each source handed to the writer
PROMPT = ("Write a research brief on: {topic}\n\nUse ONLY the numbered sources below. Write four to six plain sentences. "
          "After every sentence put the number of the source it came from in brackets, like [2]. If the sources do not "
          "cover something, leave it out. No headings, no lists, no em dashes.\n\n{sources}")


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


def research(topic):
    """Research a topic: read Wikipedia, her library and your notes, and write a short brief citing each source."""
    topic = topic.strip().rstrip("?.!")
    if not topic:
        return 'Research what? Say it like "research the history of the printing press".'
    found = sources(topic)
    if not found:
        return f"I could not find sources on {topic}. The web may be unreachable; try again in a minute."
    numbered = "\n\n".join(f"[{i}] {name}\n{text}" for i, (name, text) in enumerate(found, 1))
    import tools_llm
    brief = tools_llm.ask_llm(PROMPT.format(topic=topic, sources=numbered))
    brief = brief.rsplit("\n(Answered by", 1)[0]
    kept = check(brief, [t for _, t in found])
    if not kept:
        return f"I read {len(found)} sources on {topic} but could not write a brief I can stand behind. {brief if brief.startswith(('I could not', 'The local model')) else ''}".strip()
    cites = "\n".join(f"[{i}] {name}" for i, (name, _) in enumerate(found, 1) if f"[{i}]" in kept)
    return f"{kept}\n\nSources:\n{cites}"
