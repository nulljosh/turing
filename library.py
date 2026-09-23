"""Her library: what she can look up without the internet. Your fieldbook (every field explained plainly) plus the
lead section of every one of Wikipedia's ~11,000 vital articles (the list Wikipedia's own editors keep of what an
encyclopedia must cover), saved in ~/.samantha/library (or SAMANTHA_LIBRARY) and indexed with SQLite full-text search.
A small model cannot hold facts in its weights without inventing them, so she reads instead.

    python3 library.py fetch      # the fieldbook and the vital articles, about 10 minutes, polite to Wikipedia
    python3 library.py ask "what is kinship"

ask.general_knowledge falls back to look_up() when the web had no answer or could not be reached. Every answer
names the page it came from. It answers what-is and who-was questions from the page of that name, and declines the rest.
"""
import json
import os
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

FIELDBOOK = os.path.expanduser("~/Documents/Code/fieldbook/fields.json")
VITAL = ["Level/3"] + ["Level/4/" + x for x in ("People", "History", "Geography", "Arts", "Religion", "Everyday life",
                                               "Society and social sciences", "Health and medicine", "Science",
                                               "Technology", "Mathematics")]
UA = {"User-Agent": "samantha-library/1.0 (https://github.com/nulljosh/turing)"}
STOP = set("a an and are as at be by did do does for from how in is it its of on or that the this to was were what "
           "when where which who whom why will with about into than then there these those can could would should "
           "tell me explain define mean means meaning many much".split())
# what a question says before its subject: "what is", "who was", "tell me about", "define"
ASKING = re.compile(r"^(?:(?:what|who)(?:'s| is| are| was| were)|tell me about|explain|define|describe)\s+(?:an? |the )?", re.I)


def shelf():
    """The folder her library lives in."""
    return os.path.expanduser(os.environ.get("SAMANTHA_LIBRARY", "~/.samantha/library"))


def words(text):
    """The content words of a text, lowercased, stopwords out."""
    return [w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOP and len(w) > 1]


def _wiki(params, tries=6):
    """One Wikipedia API call, JSON back. A 429 waits and tries again, longer each time."""
    url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode({**params, "format": "json"})
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == tries - 1:
                raise
            time.sleep(int(e.headers.get("Retry-After") or 0) or 5 * 2 ** attempt)


def vital_titles(log=print):
    """Every article on Wikipedia's vital articles lists, levels 3 and 4, in list order, no repeats."""
    titles = []
    for page in VITAL:
        cont, got = {}, 0
        while True:
            d = _wiki({"action": "query", "prop": "links", "titles": "Wikipedia:Vital articles/" + page,
                       "plnamespace": 0, "pllimit": "max", "redirects": 1, **cont})
            for p in d.get("query", {}).get("pages", {}).values():
                links = [l["title"] for l in p.get("links", [])]
                titles += links
                got += len(links)
            if "continue" not in d:
                break
            cont = d["continue"]
            time.sleep(0.5)
        log(f"{page}: {got} articles")
    return list(dict.fromkeys(titles))


def _db(create=False):
    """The index: one row per page (title, source, text), full-text indexed. None when there is no library yet."""
    path = os.path.join(shelf(), "index.db")
    if not create and not os.path.exists(path):
        return None
    db = sqlite3.connect(path)
    db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS pages USING fts5(title, source UNINDEXED, body)")
    return db


def fetch(titles=None, log=print):
    """Fill the library: the fieldbook, then the lead of every vital article, 20 per request. Returns pages saved."""
    os.makedirs(shelf(), exist_ok=True)
    db = _db(create=True)
    db.execute("DELETE FROM pages")
    saved = 0
    if os.path.exists(FIELDBOOK):
        with open(FIELDBOOK) as f:
            fields = json.load(f)
        db.executemany("INSERT INTO pages VALUES (?, ?, ?)",
                       [(f["n"], f"Fieldbook: {f['n']}", f"{f['n']}: {f.get('s', '')} {f.get('p', '')}") for f in fields])
        saved += len(fields)
        log(f"fieldbook: {len(fields)} fields")
    titles = titles if titles is not None else vital_titles(log)
    for i in range(0, len(titles), 20):
        d = _wiki({"action": "query", "prop": "extracts", "exintro": 1, "explaintext": 1, "exlimit": 20,
                   "redirects": 1, "titles": "|".join(titles[i:i + 20])})
        rows = [(p["title"], f"Wikipedia: {p['title']} (saved)", p["extract"].strip())
                for p in d.get("query", {}).get("pages", {}).values() if len(p.get("extract") or "") > 80]
        db.executemany("INSERT INTO pages VALUES (?, ?, ?)", rows)
        db.commit()
        saved += len(rows)
        if i % 1000 == 0:
            log(f"{i + len(titles[i:i + 20])} of {len(titles)} articles")
        time.sleep(0.5)  # be polite to Wikipedia
    db.commit()
    db.close()
    return saved


def _first(text, n=3):
    """The first n sentences of a text."""
    return " ".join(re.split(r"(?<=[.!?])\s+", text.strip())[:n])


def look_up(question):
    """What her library says about a question, as (answer, source), or (None, None).
    Only a page named exactly what was asked ("what is kinship" -> Kinship, "who was Margaret Mead") answers,
    with its opening sentences. Matching words across pages was tried and cut: word overlap is not reading, it
    answered "what year did world war 2 end" with a sentence about civil wars since then. Declined, never guessed."""
    asked = words(question)
    db = _db() if asked else None
    if db is None:
        return None, None
    try:
        subject = ASKING.sub("", question.strip().rstrip("?!. ")).strip().strip("\"'“”‘’ ")
        for name in dict.fromkeys((subject, subject[:-1] if subject.endswith("s") else "", subject + "s")):
            if not name:
                continue
            row = db.execute("SELECT source, body FROM pages WHERE lower(title) = lower(?) LIMIT 1", (name,)).fetchone()
            if row:
                return _first(row[1]), row[0]
    except sqlite3.Error:
        return None, None
    finally:
        db.close()
    return None, None


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "fetch":
        print(f"saved {fetch()} pages to {shelf()}")
    elif len(sys.argv) > 2 and sys.argv[1] == "ask":
        answer, source = look_up(" ".join(sys.argv[2:]))
        print(f"{answer}\n({source})" if answer else "Not in my library.")
    else:
        print(__doc__)
