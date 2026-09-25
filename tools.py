#!/usr/bin/env python3
"""Samantha's hands: a small fixed set of things she can do on this Mac.

Two layers. act() is a regex router, instant and exact, same category as
arithmetic/clock in ask.py: a recognisable command has one right action, so no
model is involved. agent() is for anything multi-step ("poke around hacker news
and tell me what's up"): qwen3:1.7b via Ollama's native tool calling drives the
same TOOLS. The 0.5B cannot pick tools reliably, that is a hardware ceiling,
not a tuning problem, so she borrows a bigger head for her hands.

No shell tool, deliberately. Every tool is a fixed argv, never a string a model
wrote handed to sh.
"""
import html
import json
import os
import re
import subprocess
import sys
import unicodedata
import urllib.parse
import urllib.request
import untrusted
import tools_util
from tools_image import remove_background, upscale_image, enhance_image, grayscale_image, rotate_image, flip_image, resize_image, crop_square, convert_image, image_info
from tools_files import find_file, recent_downloads, folder_size, move_file, copy_file, rename_file, zip_file, unzip_file, trash_file

AGENT_MODEL = "qwen3:1.7b"  # 8B was right but 7.6GB and minutes per run; 1.7B is right in 5s once the harness prefetches
OLLAMA_CHAT = "http://localhost:11434/api/chat"
BROWSER = "Google Chrome"
APP_DIRS = ("/Applications", "/System/Applications", "/System/Applications/Utilities",
            os.path.expanduser("~/Applications"))
SITES = {
    "hacker news": "https://news.ycombinator.com", "hn": "https://news.ycombinator.com",
    "github": "https://github.com", "youtube": "https://youtube.com",
    "gmail": "https://mail.google.com", "reddit": "https://reddit.com",
    "twitter": "https://x.com", "x": "https://x.com",
}


# SAMANTHA_HEADLESS=1: nothing visible or audible happens. For evals and
# development, so a test run never steals the screen from whoever is working.
HEADLESS = os.environ.get("SAMANTHA_HEADLESS") == "1"
_VISIBLE = ("open", "say", "screencapture")


def _run(argv, timeout=10):
    """Run a subprocess and return its output, or empty string in headless mode for visible apps."""
    if HEADLESS and argv[0] in _VISIBLE:
        return ""
    r = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    return (r.stdout or r.stderr).strip()


def installed_apps():
    """Scan Applications folders and return dict of app names to display names."""
    apps = {}
    for d in APP_DIRS:
        if os.path.isdir(d):
            for f in os.listdir(d):
                if f.endswith(".app"):
                    apps[f[:-4].lower()] = f[:-4]
    return apps


def _app_match(name):
    """Find an installed app by name, allowing partial matches and normalizing common names."""
    apps = installed_apps()
    key = re.sub(r"^(?:the |my )|(?: app)$", "", name.strip().lower())
    if key == "chrome":
        key = "google chrome"
    # exact, then unique-prefix: "pixelmator" finds "Pixelmator Pro"
    found = apps.get(key) or next((v for k, v in sorted(apps.items()) if k.startswith(key)), None)
    # "photoshop" is what people call any photo editor: without Photoshop, it means the one this Mac has
    if not found and key in ("photoshop", "adobe photoshop"):
        return _app_match("pixelmator")
    return found


def open_app(name):
    """Open an installed macOS app by name."""
    match = _app_match(name)
    if not match:
        return f"No app called {name!r} on this Mac."
    _run(["open", "-a", match])
    return f"Opened {match}."


def _url(target):
    """Convert a target (URL, domain, or site name) to a full HTTPS URL."""
    t = target.strip().strip("\"'")
    if t.lower() in SITES:
        return SITES[t.lower()]
    if re.match(r"^https?://", t, re.I):
        return t if re.match(r"^https?://[^\s/]", t, re.I) else None
    if re.match(r"^[\w-]+(\.[\w-]+)+(/\S*)?$", t):
        return "https://" + t
    return None


def open_url(target):
    """Open a website in Chrome for Joshua to see. Returns no page contents. Takes a URL, a bare domain, or a known site name."""
    if re.match(r"^(?:https?:)?/*:?/*$", target.strip(), re.I):
        return "That address is empty. Give me a site, like github.com."
    url = _url(target)
    if not url:
        return web_search(target)
    _run(["open", "-a", BROWSER, url])
    return f"Opened {url} in Chrome."


SITE_SEARCH = {
    "youtube": "https://www.youtube.com/results?search_query=", "amazon": "https://www.amazon.com/s?k=",
    "reddit": "https://www.reddit.com/search/?q=", "github": "https://github.com/search?q=",
    "wikipedia": "https://en.wikipedia.org/w/index.php?search=", "google maps": "https://www.google.com/maps/search/",
    "maps": "https://www.google.com/maps/search/",
}
_SITE_NAMES = "|".join(sorted(SITE_SEARCH, key=len, reverse=True))


def site_search(site, query):
    """The address of a search on one site: "search youtube for lofi" is YouTube's own results page, not a web search."""
    return SITE_SEARCH[site.lower()] + urllib.parse.quote_plus(query.strip())


def search_url(query):
    """The address of a web search for this query."""
    return "https://duckduckgo.com/?q=" + urllib.parse.quote_plus(query)


def web_search(query):
    """Open a web search in Chrome for Joshua. A question ("how tall is everest") is also answered, with its source, from
    the same lookup her questions use; anything else returns no results to you. To learn what a page says, use read_page."""
    _run(["open", "-a", BROWSER, search_url(query)])
    opened = f"Searching for {query!r} in Chrome."
    answer = search_answer(query)
    return f"{answer}\n{opened}" if answer else opened


def search_answer(query):
    """The answer to a searched question and where it came from, or None: a search should answer, not only open a tab.
    Only a real question is looked up ("best pizza in vancouver" is a list to browse, not a fact). Never fails the search."""
    try:
        import ask
        if not ask.is_question(query):
            return None
        text, source = ask.general_knowledge(query, hands=False)
    except Exception:
        return None
    return f"{text} (Source: {source}.)" if text and isinstance(source, str) and source else None


def current_tab():
    """Title and URL of the tab Chrome is showing right now."""
    out = _run(["osascript", "-e",
                f'tell application "{BROWSER}" to get (title of active tab of front window) & "\n" & (URL of active tab of front window)'])
    return out or "Chrome has no window open."


def read_page(target=""):
    """Fetch a web page and return its text. The ONLY way to know what a page says. Takes a URL, bare domain, or site name like 'hacker news'. No argument reads Chrome's current tab."""
    url = _url(target) if target else (current_tab().splitlines() or [""])[-1]
    if not url or not url.startswith("http"):
        return "No page to read."
    from ask_web import fetch_text
    text = fetch_text(url)
    if text is None:
        return f"Couldn't read {url}. It may be down, blocking this, or a JS-only page with nothing in the raw HTML."
    return text


def summarize(target=""):
    """A real summary, three to five plain sentences from the biggest local model on this Mac, not the one-sentence
    answer a lookup gives. Takes a document path in your home folder, a page (a URL, a site name, or nothing for the
    current Chrome tab), or "my unread mail" for the inbox."""
    target = target.strip()
    doc_exts = (".pdf", ".doc", ".docx", ".rtf", ".rtfd", ".html", ".htm", ".odt", ".webarchive", ".txt", ".md", ".csv", ".json", ".log")
    looks_like_path = target.startswith(("~", "/")) or target.lower().endswith(doc_exts)
    if re.fullmatch(r"(?:my |the )?(?:unread )?(?:mail|email|inbox)", target, re.I):
        text = unread_mail("")
    elif target and looks_like_path:
        text, why = tools_util._doc_text(target)
        if why:
            return why
        text = text[:8000]
    else:
        text = read_page(target)
    text = text.strip()
    if len(text) < 400:
        return text  # already short: a summary of a summary is nothing
    import tools_llm
    prompt = ("Summarize the following in three to five plain sentences. No headings, no lists, no em dashes, "
              "and do not mention that you are summarizing.\n\n" + text[:8000])
    reply = tools_llm.ask_llm(prompt)
    return reply.rsplit("\n(Answered by", 1)[0]


LANGUAGES = ("english|french|spanish|german|italian|portuguese|dutch|swedish|norwegian|danish|finnish|polish|czech|"
             "romanian|hungarian|ukrainian|russian|greek|turkish|arabic|hebrew|hindi|japanese|chinese|mandarin|"
             "cantonese|korean|vietnamese|thai|indonesian|latin")


def translate(request):
    """Translate text, or a whole page, into a named language with the biggest local model, offline. Takes
    'text<TAB>language'; text that is a URL or site name is fetched first and its opening is translated."""
    text, _, language = request.partition("\t")
    text, language = text.strip().strip("\"'"), language.strip().lower()
    if not text or not language:
        return 'Translate what, into what? Say it like "translate good morning to french".'
    if _url(text):
        text = read_page(text)[:4000]
    import tools_llm
    prompt = (f"Translate the following into {language.capitalize()}. Reply with the translation only, no notes, "
              f"no quotes, no em dashes.\n\n{text}")
    reply = tools_llm.ask_llm(prompt)
    return reply.rsplit("\n(Answered by", 1)[0]


def screenshot():
    """Take a screenshot of the screen and return the file path."""
    path = os.path.expanduser("~/Desktop/samantha-shot.png")
    _run(["screencapture", "-x", path])
    return f"Saved {path}."


def clipboard():
    """Read what is on the clipboard."""
    return _run(["pbpaste"])[:2000] or "The clipboard is empty."


def set_volume(level):
    """Set the Mac's output volume. Takes 0 to 100, or "up" or "down"."""
    step = {"up": 15, "down": -15}.get(str(level).strip().lower())
    n = max(0, min(100, current_volume() + step if step else int(float(level))))
    _run(["osascript", "-e", f"set volume output volume {n}"])
    return f"Volume at {n}."


def current_volume():
    """The Mac's output volume, 50 if it cannot be read."""
    out = _run(["osascript", "-e", "output volume of (get volume settings)"])
    return int(out) if out.isdigit() else 50


def battery():
    """Battery or power status of this Mac."""
    return (_run(["pmset", "-g", "batt"]).splitlines() or ["No battery reading on this Mac."])[-1].strip()


def say(text):
    """Speak text out loud."""
    if not HEADLESS:
        subprocess.Popen(["say", text[:500]])
    return f"Saying: {text[:80]}"


from tools_apps import music, weather, timer, duration, new_note, new_reminder, calendar_today, unread_mail, needs_attention, free_when, _MUSIC  # noqa: E402,F401


HOME = os.path.realpath(os.path.expanduser("~"))


def _inside_home(path):
    """Resolve a path and verify it stays inside the home folder, return None if outside."""
    # realpath first: a symlink or ../ must not walk a read out of the home folder
    full = os.path.realpath(os.path.expanduser(path.strip() or "~"))
    return full if full == HOME or full.startswith(HOME + os.sep) else None


def list_dir(path="~"):
    """List a folder inside the home folder."""
    full = _inside_home(path)
    if not full or not os.path.isdir(full):
        return f"No folder at {path!r} inside your home folder."
    names = sorted(n for n in os.listdir(full) if not n.startswith("."))
    return ", ".join(names[:80]) or "Empty folder."


def read_file(path):
    """Read a text file inside the home folder."""
    full = _inside_home(path)
    if not full or not os.path.isfile(full):
        return f"No file at {path!r} inside your home folder."
    # ponytail: refuses dotfiles outright instead of a secrets allowlist; .env and .ssh stay unread
    if any(part.startswith(".") for part in os.path.relpath(full, HOME).split(os.sep)):
        return "I don't read hidden files."
    with open(full, "rb") as f:
        return f.read(3000).decode("utf-8", "ignore")


# the logo designer and painter live in tools_logo.py; every name is re-exported here
from tools_logo import *  # noqa: E402,F401,F403
from tools_logo import _logo_layers, _complex_layers, _bloom_layers, _LOGO_SCHEMA, _COMPLEX_SCHEMA, _BLOOM_SCHEMA, _WANTS_SIMPLE, _WANTS_COMPLEX  # noqa: E402,F401

TOOLS = {f.__name__: f for f in (open_app, open_url, web_search, current_tab, read_page, summarize, translate, screenshot,
                                     clipboard, set_volume, battery, say, list_dir, read_file, make_logo, paint_image,
                                     music, weather, timer, new_note, new_reminder, calendar_today, unread_mail, needs_attention, free_when,
                                     remove_background, upscale_image, enhance_image, grayscale_image, rotate_image, flip_image, resize_image, crop_square, convert_image, image_info,
                                     find_file, recent_downloads, folder_size, move_file, copy_file, rename_file, zip_file, unzip_file, trash_file)}
TOOLS.update({f.__name__: f for f in tools_util.TOOLS})
globals().update({f.__name__: f for f in tools_util.TOOLS})  # eval/actions.py swaps every TOOLS name on this module for a recorder

import tools_registry  # noqa: E402  (organizer/system/dev families, WRITES/NOT_FOR_MODELS, the model-pick soundness guard: split for size)
tools_registry.register_families(TOOLS, globals())
NOT_FOR_MODELS = tools_registry.NOT_FOR_MODELS
WRITES = tools_registry.WRITES
_EVIDENCE = tools_registry._EVIDENCE
_AGAINST = tools_registry._AGAINST
_sound = tools_registry._sound

import tools_write  # noqa: E402  (phrase-routed only: each confirms itself with a diff, never a model's tool)
_WRITERS = {f.__name__: f for f in (tools_write.edit_last_draft, tools_write.edit_file, tools_write.write_code)}
TOOLS.update(_WRITERS)
globals().update(_WRITERS)

import tools_routes  # noqa: E402  (the regex router: phrase table + text normalization, split for size)
tools_routes.install(sys.modules[__name__])  # builds _ROUTES etc against this module, never `import tools` inside
_ROUTES = tools_routes._ROUTES
_GREEDY = tools_routes._GREEDY
_MULTISTEP = tools_routes._MULTISTEP
_EYES = tools_routes._EYES
_SCREEN_JOB = tools_routes._SCREEN_JOB
_ACTION = tools_routes._ACTION
_bare = tools_routes._bare
is_action = tools_routes.is_action
_schema = tools_routes._schema
_named_page = tools_routes._named_page


def act(query):
    """Do a recognisable single command, exactly. Returns the result or None."""
    if untrusted.is_untrusted(query): return untrusted.REFUSAL
    q = _bare(query)
    if _MULTISTEP.search(q) and not _EYES.search(q):
        return None
    for pattern, fn in _ROUTES:
        m = pattern.match(q)
        if m:
            return fn(m)
    return None


def model_tools():
    """The tools a model may choose from: everything except NOT_FOR_MODELS."""
    return {n: f for n, f in TOOLS.items() if n not in NOT_FOR_MODELS}



def plan(query):
    """Which tools would act() fire for this command, and with what? Nothing runs: every tool is
    swapped for a recorder while the router looks at the sentence, the way eval/actions.py does."""
    if untrusted.is_untrusted(query): return []
    calls, names = [], [n for n in TOOLS if n in globals()]
    saved = {n: globals()[n] for n in names}
    try:
        for n in names:
            globals()[n] = lambda *a, _n=n, **k: calls.append((_n, tuple(str(x) for x in a))) or "ok"
        act(query)
    finally:
        globals().update(saved)
    return calls


_STEP = re.compile(r"\s*(?:,? and then |,? then |,? and |; )\s*", re.I)
_THEN = re.compile(r"\bthen\b|;", re.I)
_TELL = re.compile(r"^(?:tell|show|give|read) me (?:my |the )?|^(?:also|and) ", re.I)


def _route_of(command):
    """The pattern of the first route that takes this bare command, or None."""
    return next((p for p, _ in _ROUTES if p.match(command)), None)


def chain(query, log=None, confirm=None):
    """Several plain commands in one sentence, run in order with no model: "open youtube and set the volume
    to 20". Only when every step routes on its own; one step the router does not know and it is agent() work.
    Each step is shown, and a write still waits for its own yes. Returns the replies, or None."""
    whole = _bare(query.splitlines()[-1])
    # "then" always means another step. A plain "and" may be part of one: a real route for the whole
    # sentence wins ("open chrome and go to github.com", "remind me to call mom and dad")
    if not _THEN.search(whole) and _route_of(whole) not in (None, *_GREEDY):
        return None
    parts = [_TELL.sub("", p).strip() for p in _STEP.split(whole)]
    if len(parts) < 2 or not all(parts):
        return None
    # a later step that only a catch-all takes ("open the garage") is more likely words than a command
    if any(_route_of(p) in _GREEDY for p in parts[1:]):
        return None
    steps = [plan(p) for p in parts]
    if not all(len(s) == 1 for s in steps):
        return None
    replies = []
    for part, [(name, args)] in zip(parts, steps):
        if log:
            log(f"  [{name}({', '.join(args)})]")
        if confirm and name in WRITES and not confirm(name, args):
            replies.append(f"Skipped {name}.")
            continue
        replies.append(act(part))
    return "\n".join(replies)


# a command with its object missing: ask for it instead of guessing ("search for" searched for the word "for")
_INCOMPLETE = (
    (re.compile(r"^(?:open|launch|start|go to|visit|browse to|pull up)(?: up)?$", re.I), "Open what? Name an app or a site."),
    (re.compile(r"^(?:search|google|look up|search for|search the web for|look for)$", re.I), "Search for what?"),
    (re.compile(r"^remind me(?: to| that| about)?$|^(?:set|add|create|make) (?:a )?reminder(?: to)?$", re.I), "Remind you of what?"),
    (re.compile(r"^(?:take|make|write|add|new) (?:a |me a )?(?:new )?note(?: that says| saying)?$|^note$", re.I), "What should the note say?"),
    (re.compile(r"^(?:set |start )?(?:a |an )?timer(?: for)?$", re.I), "For how long?"),
    (re.compile(r"^say$", re.I), "Say what?"),
    (re.compile(r"^(?:click|tap)(?: on)?$", re.I), 'Click what? Say it like "click Sign in".'),
    (re.compile(r"^type$", re.I), 'Type what? Say it like "type hello".'),
    (re.compile(rf"^(?:(?:ask|hey|have) )?(?:{tools_util._LLM_NAMES})[,:]?$", re.I), 'Ask what? Say it like "ask qwen why the sky is blue".'),
)


def missing(query):
    """What to ask back when a command has no object ("open", "remind me to"), or None."""
    q = _bare(query)
    return next((ask for pattern, ask in _INCOMPLETE if pattern.match(q)), None)


def do(query, log=None, confirm=None):
    """The one entry point. The regex router first: instant, exact, and it has
    never fired the wrong tool. Several plain commands in one sentence run in
    order. What it does not recognise goes to her own head, which understands
    phrasings nobody wrote a rule for. Multi-step work goes to planner.plan()/run() when a sound plan can
    be built, checking each step's result before the next runs; agent() is the fallback when it cannot.
    Anything else is not a command: None."""
    if untrusted.is_untrusted(query): return untrusted.REFUSAL
    if not query.strip():
        return None
    ask_back = missing(query)
    if ask_back:
        return ask_back
    # before the single routes, whose free-text arguments ("open (.+)") would swallow "and set the volume to 20"
    steps = chain(query, log=log, confirm=confirm)
    if steps:
        return steps
    if confirm or log:
        for name, args in plan(query):
            if log:
                log(f"  [{name}({', '.join(args)})]")
            if confirm and name in WRITES and not confirm(name, args):
                return "Okay, I will not."
    done = act(query)
    if done:
        return done
    edited = tools_write.route(_bare(query), log=log, confirm=confirm)  # ahead of _ACTION: "make it..." is never make_logo
    if edited:
        return edited
    if _SCREEN_JOB.search(_bare(query)):
        from tools_screen_agent import screen_task
        return screen_task(query, log=log, confirm=confirm)
    if _MULTISTEP.search(_bare(query)) and not _EYES.search(_bare(query)):
        import planner
        steps = planner.plan(query)
        if steps:
            return planner.run(steps, query, log=log, confirm=confirm)
        return agent(query, log=log, confirm=confirm)
    if _faq_knows(query):
        return None  # a question her own FAQ answers is about her, not a job for her hands
    picked = pick(query)
    if picked and picked[0] != "agent":
        if log:
            log(f"  [{picked[0]}({picked[1]})]")
        if confirm and picked[0] in WRITES and not confirm(picked[0], (picked[1],)):
            return "Okay, I will not."
        fn = TOOLS[picked[0]]
        return fn(picked[1]) if fn.__code__.co_argcount else fn()
    return agent(query, log=log, confirm=confirm) if picked or is_action(query) else None


def demo():
    """Self-check for the router, the tools and the guard, with every subprocess mocked."""
    global _run, installed_apps
    calls, real, real_apps = [], _run, installed_apps
    _run = lambda argv, timeout=10: calls.append(argv) or ""
    # a fixed /Applications, so the self-check means the same thing on a Mac, a Linux CI runner and anywhere else
    installed_apps = lambda: {"google chrome": "Google Chrome", "safari": "Safari", "pixelmator pro": "Pixelmator Pro", "notes": "Notes"}
    try:
        assert act("open chrome") == "Opened Google Chrome."
        assert act("go to hacker news").startswith("Opened https://news.ycombinator.com")
        assert act("open chrome and go to github.com") == "Opened https://github.com in Chrome."
        assert act("search for mlx lora").startswith("Searching")
        assert "No app" in act("open definitelynotanapp")
        assert act("open chrome and poke around hacker news") is None  # multi-step, agent's job
        assert act("what is turing") is None and not is_action("what is turing")
        assert is_action("poke around hacker news")
        for pal in PALETTES:
            for motif in ("ring", "spark", "bars", "dot"):
                assert _logo_layers(pal, motif)[0]["type"] == "rounded_rectangle"
                assert not any(l["type"] == "text" for l in _logo_layers(pal, motif))
        big = _complex_layers("ember", 5, 36, "bars", 16, 12)
        assert len(big) == 1 + 36 + 5 + 16 + 3 and all(0 <= l.get("rotation", 0) < 360 for l in big)
        assert not any(l["type"] == "text" for l in _bloom_layers("ember", 89, "square", 3)) and len(_bloom_layers("paper", 144, "circle", 2)) == 145
        assert not any(l["type"] == "text" for l in big)
        assert _named_page("poke around hacker news and tell me") == "https://news.ycombinator.com"
        assert _named_page("read github.com/nulljosh/turing.") == "https://github.com/nulljosh/turing"
        assert _named_page("open pixelmator then tell me my battery") is None
        assert not is_action("Summarize what Turing is in one sentence.")  # real eval prompt, was hijacked
        assert act("summarize this page") == "No page to read."
        assert act("summarize my unread mail") == "No unread mail."
        assert "No file" in act("summarize ~/samantha-test-does-not-exist.pdf")
        assert act("volume 30") == "Volume at 30." and act("set the volume to 250") == "Volume at 100."
        assert "don't read hidden" in read_file("~/.ssh/id_rsa") or "No file" in read_file("~/.ssh/id_rsa")
        assert "No file" in read_file("/etc/passwd") and "No folder" in list_dir("~/../..")
        assert act("play some music") == "Playing." and act("skip this song") == "Skipped." and act("pause") == "Paused."
        assert [duration(x) for x in ("5", "90 seconds", "an hour", "half an hour", "ten minutes", "2 hrs", "soon")] == [5, 1.5, 60, 30, 10, 120, None]
        assert act("set a timer for 0 minutes").startswith("A timer runs") and act("what's playing") == "Nothing is playing."
        assert act("remind me to call mom") == "I'll remind you: call mom" and act("take a note buy milk") == "Noted: buy milk"
        import tools_apps
        from datetime import date, datetime, timedelta
        t, due, why = tools_apps._when("call mom tomorrow at 9am")
        assert (t, due.date(), due.hour, due.minute, why) == ("call mom", date.today() + timedelta(days=1), 9, 0, None)
        t, due, _ = tools_apps._when("at 5 to pay rent")
        assert (t, due.hour) == ("pay rent", 17) and due > datetime.now()
        t, due, _ = tools_apps._when("in 20 minutes water the plants")
        assert t == "water the plants" and 19 <= (due - datetime.now()).total_seconds() / 60 <= 20
        t, due, _ = tools_apps._when("pay rent on friday at noon")
        assert (t, due.weekday(), due.hour) == ("pay rent", 4, 12) and due.date() > date.today()
        assert tools_apps._when("call mom") == ("call mom", None, None)
        assert tools_apps._when("water the plants every morning")[2].startswith("I can set a reminder once")
        assert act("remind me tomorrow at 9am to call mom").startswith("I'll remind you: call mom, ")
        assert act("what's on my calendar today") == "Nothing on the calendar today."
        assert act("what needs my attention") == "Nothing needs your attention: no unread mail, nothing on the calendar today, and no reminders due."
        assert act("am i free") and "free" in act("am i free this week")  # weekday-independent: no exact day names asserted here
        assert act("what is the weather system") is None and act("play chess with me") is None  # questions, not commands
        if not HEADLESS:  # headless never reaches osascript at all
            note = [a for a in calls if a[-1] == "buy milk"][0]
            assert "buy milk" not in note[2]  # her words ride in argv, never inside the script
        assert _sound("set_volume", "40", "crank it to 40") and not _sound("set_volume", "90", "crank it to 40")
        assert _sound("new_note", "buy milk", "jot down buy milk") and not _sound("new_note", "sell the car", "jot down buy milk")
        assert not _sound("timer", "soon", "time me soon") and not _sound("rm_rf", "", "anything")
        assert all(a[0] in ("open", "osascript", "screencapture", "pbpaste", "pmset") for a in calls)
    finally:
        _run, installed_apps = real, real_apps
    tools_util.demo()
    assert NOT_FOR_MODELS <= set(TOOLS) and "run_shortcut" in NOT_FOR_MODELS  # side-effect tools never reach the model's menu
    print("tools ok")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        print(do(" ".join(sys.argv[1:]), log=print) or "Not an action.")
    else:
        demo()


from tools_agent import agent, pick, _faq_knows, HANDS_ADAPTER, HANDS_SYSTEM  # noqa: E402,F401  (her hands' choices, split out for size; re-exported)
import feedback  # noqa: E402,F401  (splices feedback_summary into TOOLS/_ROUTES/NOT_FOR_MODELS; private, never a model's pick or MCP)
