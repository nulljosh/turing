"""The regex router: the phrase table that maps a plain sentence to a tool call, and the
text normalization act() runs first. Split from tools.py for size (CLAUDE.md, File size).

install(t) builds the phrase table against the tools module `t`, passed in explicitly by
tools.py itself (never `import tools` here): tools.py calls this mid-load, before its own
top-level execution finishes, and a bare `import tools` at that point would make Python
start a second, independent execution of tools.py (fatal when it is run directly as
__main__, since nothing has registered it as `tools` yet). Every tool call in the table
goes through `t` (`t.music(...)`, not a bare `music(...)`), so a test that does
`setattr(tools, name, recorder)` (eval/actions.py, the same way it patches every other
tool) still catches it, exactly as it did when this table lived inside tools.py itself.
"""
import re
import unicodedata

import tools_dev
import tools_files
import tools_image
import tools_organizer
import tools_system
import tools_util

_UNIT = {"s": 1 / 60, "m": 1, "h": 60}

_ROUTES = _GREEDY = _schema = _named_page = None  # set by install(), so tools.py can re-export them


def install(t):
    """Build _ROUTES, _GREEDY, _schema and _named_page against tools module `t`."""
    global _ROUTES, _GREEDY, _schema, _named_page

    def _util_route(name, arg):
        """A tools_util or tools_image route as a tools.py one. The function is looked up
        on `t` at call time, so eval/actions.py can swap it for a recorder like every other tool."""
        takes = t.TOOLS[name].__code__.co_argcount
        return lambda m: getattr(t, name)(arg(m)) if takes else getattr(t, name)()

    _ROUTES = (
        (re.compile(r"^(?:play|resume)(?: (?:the |some |my )?(?:music|song|tunes))?$", re.I), lambda m: t.music("play")),
        (re.compile(r"^pause$|^(?:pause|stop) (?:the |my |this )?(?:music|song|track)$", re.I), lambda m: t.music("pause")),
        (re.compile(r"^(?:skip|next)(?: (?:this |the )?(?:song|track|one))?$", re.I), lambda m: t.music("next")),
        (re.compile(r"^(?:previous|last|go back a|go back one)(?: (?:song|track))?$", re.I), lambda m: t.music("previous")),
        (re.compile(r"^what(?:'s| is) (?:this song|playing)\b|^what song is (?:this|playing)", re.I), lambda m: t.music("playing")),
        (re.compile(r"^(?:what(?:'s| is) the |how(?:'s| is) the |(?:look up|check|get) the )?weather\b(?: like)?(?: today| outside| right now| now)*(?: (?:in|for) (.+))?$", re.I),
         lambda m: t.weather(m.group(1) or "")),
        (re.compile(r"^(?:set |start )?(?:a |an )?(?:timer (?:for )?(\d+(?:\.\d+)?) ?(s|m|h)\w*|(\d+(?:\.\d+)?)[ -]?(s|m|h)\w* timer)$", re.I),
         lambda m: t.timer(float(m.group(1) or m.group(3)) * _UNIT[(m.group(2) or m.group(4)).lower()])),
        (re.compile(r"^remind me (?:to |that |about )?(.+)$|^(?:add|create|make|set|new) (?:a |me a )?(?:new )?reminder(?: to| that says| saying|:)? (.+)$", re.I),
         lambda m: t.new_reminder(m.group(1) or m.group(2))),
        (re.compile(r"^(?:(?:make|create|take|write|add|new) (?:a |me a )?(?:new )?note|note)(?: that says| saying| that|:)? (.+)$", re.I), lambda m: t.new_note(m.group(1))),
        (re.compile(r"^what(?:'s| is) on (?:my |the )?(?:calendar|schedule|agenda)\b|^(?:my )?(?:calendar|schedule|agenda)(?: for)?(?: today)?$|^what do i have (?:on )?today", re.I),
         lambda m: t.calendar_today()),
        (re.compile(r"^(?:check (?:my )?|do i have |is there )?(?:any )?(?:new |unread )?(?:mail|email)\??$", re.I), lambda m: t.unread_mail("")),
        (re.compile(r"^(?:is there |do i have )?anything from (.+?) in my (?:mail|email|inbox)(?: today)?\??$|^(?:mail|email) from (.+?)(?: today)?\??$", re.I),
         lambda m: t.unread_mail(m.group(1) or m.group(2))),
        (re.compile(r"^what needs (?:my attention|me)$", re.I), lambda m: t.needs_attention()),
        (re.compile(r"^(?:am i free|when am i free|how free am i|do i have (?:any )?time)(?:\s+(.+))?$", re.I), lambda m: t.free_when(m.group(1) or "")),
        (re.compile(r"^(?:make|design|draw|create|build)(?: me)? (?:a |an )?((?:(?:complex|intricate|detailed|elaborate|ornate|fancy|crazy|insane|original|wordless|abstract|textless) )*)(?:logo|icon)(?: for| of)? (.+)$", re.I), lambda m: t.make_logo((m.group(1) or "") + m.group(2))),
        (re.compile(r"^(?:paint|repaint)(?: me)? (?:a picture of |a painting of |the (?:image|photo|picture) (?:at )?)?(\S+\.(?:jpe?g|png|heic|webp|tiff?))$", re.I), lambda m: t.paint_image(m.group(1))),
        (re.compile(r"^(?:(?:show me |tell me )?what(?:'s| is) (?:on|in) (?:my |the )?clipboard|(?:read|show)(?: me)? (?:my |the )?clipboard)\b", re.I), lambda m: t.clipboard()),
        (re.compile(r"^(?:set |turn |put )?(?:the |it |my )?(?:volume )?(?:up |down )?(?:to |at )(\d{1,3})\b", re.I), lambda m: t.set_volume(m.group(1))),
        (re.compile(r"^(?:set |turn )?(?:the )?volume (\d{1,3})\b", re.I), lambda m: t.set_volume(m.group(1))),
        (re.compile(r"^(?:turn )?(?:the |it )?(?:volume )?(up|down)$|^(?:turn )?(?:the )?volume (up|down)$|^(louder|quieter)$", re.I),
         lambda m: t.set_volume("up" if (m.group(1) or m.group(2) or m.group(3)).lower() in ("up", "louder") else "down")),
        (re.compile(r"^mute\b", re.I), lambda m: t.set_volume(0)),
        (re.compile(r"^(?:how(?:'s| is) (?:my |the )?battery|battery(?: level| status)?$|what(?:'s| is) (?:my |the )?battery|how much battery)", re.I), lambda m: t.battery()),
        (re.compile(r"^say (.+)$", re.I), lambda m: t.say(m.group(1))),
        (re.compile(r"^(?:list|show)(?: me)? (?:the )?(?:files|folder|contents) (?:in|of|at) (.+)$", re.I), lambda m: t.list_dir(m.group(1))),
        (re.compile(r"^(?:read|show|cat)(?: me)? (?:the )?file (.+)$", re.I), lambda m: t.read_file(m.group(1))),
        (re.compile(r"^(?:take a |grab a )?screenshot\b", re.I), lambda m: t.screenshot()),
        (re.compile(r"^what(?:'s| is) (?:on |in )?(?:my |the )?(?:current |open )?(?:tab|chrome|browser)\b", re.I), lambda m: t.current_tab()),
        (re.compile(rf"^(?:search|look up|find) (?:on )?({t._SITE_NAMES}) for (.+)$|^(?:search|look up) (.+) on ({t._SITE_NAMES})$", re.I),
         lambda m: t.open_url(t.site_search(m.group(1) or m.group(4), m.group(2) or m.group(3)))),
        (re.compile(rf"^(?:open |go to |pull up )?({t._SITE_NAMES}) and search(?: it)?(?: for)? (.+)$", re.I), lambda m: t.open_url(t.site_search(m.group(1), m.group(2)))),
        (re.compile(r"^(?:search|google|look up)(?: search)?(?: (?:the web|online|the internet|on google|google))?(?: for)? (.+)$", re.I), lambda m: t.web_search(m.group(1))),
        (re.compile(r"^(?:read|fetch) (?:me )?(?:the )?(?:page |site |website )?(?:at )?(https?://\S+|[\w-]+(?:\.[\w-]+)+(?:/\S*)?)$|^what does (https?://\S+|[\w-]+(?:\.[\w-]+)+(?:/\S*)?) say$", re.I),
         lambda m: t.read_page(m.group(1) or m.group(2))),
        (re.compile(r"^summari[sz]e (?:this |the )?(?:page|tab)$", re.I), lambda m: t.summarize("")),
        (re.compile(r"^summari[sz]e (?:my |the )?(?:unread )?(?:mail|email|inbox)$", re.I), lambda m: t.summarize("mail")),
        (re.compile(r"^summari[sz]e (?:me )?(?:the )?(?:document|pdf|doc|file called) (.+)$", re.I), lambda m: t.summarize(m.group(1))),
        (re.compile(r"^summari[sz]e (~/\S+|/\S+)$", re.I), lambda m: t.summarize(m.group(1))),
        (re.compile(r"^summari[sz]e (?:me )?(?:the )?(?:page |site |website )?(?:at )?(https?://\S+|[\w-]+(?:\.[\w-]+)+(?:/\S*)?)$", re.I),
         lambda m: t.summarize(m.group(1))),
        (re.compile(rf"^translate (?:the page |the site )?(.+?) (?:to|into) ({t.LANGUAGES})$|^how do you say (.+?) in ({t.LANGUAGES})$", re.I),
         lambda m: t.translate((m.group(1) or m.group(3)) + "\t" + (m.group(2) or m.group(4)))),
        (re.compile(r"^(?:open|launch|start) (?:up )?(?:chrome|the browser) (?:and |then )?(?:go to|open|visit|load) (.+)$", re.I), lambda m: t.open_url(m.group(1))),
        (re.compile(r"^(?:go to|visit|browse to|pull up) (.+)$", re.I), lambda m: t.open_url(m.group(1))),
        (re.compile(r"^(?:open|launch|start) (?:up )?(.+)$", re.I),
         # one unknown word is a mistyped app, say so. A phrase that is no app
         # ("the turing repo on github") is something to look for.
         lambda m: t.open_url(m.group(1)) if t._url(m.group(1)) or (" " in m.group(1).strip() and not t._app_match(m.group(1))) else t.open_app(m.group(1))),
    )

    # the catch-all routes whose argument is any text: a sentence they swallow may really be several commands
    _GREEDY = {_ROUTES[-2][0], _ROUTES[-1][0]}

    # the image tools before the utilities, so "convert cat.png to jpg" is an image and never a unit conversion
    _ROUTES = _ROUTES + tuple((pat, _util_route(name, arg)) for pat, name, arg in tools_image.ROUTES)
    _ROUTES = _ROUTES + tuple((pat, _util_route(name, arg)) for pat, name, arg in tools_files.ROUTES)  # find a file, downloads, folder size
    _ROUTES = _ROUTES + tuple((pat, _util_route(name, arg)) for pat, name, arg in tools_util.ROUTES)  # 31 utility tools: math, text, dice, this Mac's vitals
    # organizer's, system's and dev's own phrasings go in FRONT of everything above: "search notes for X" would
    # otherwise be swallowed by the "search ... for" catch-all, and "quit spotify"/"run the tests" by nothing today either
    _ROUTES = tuple((pat, _util_route(name, arg)) for _mod in (tools_organizer, tools_system, tools_dev) for pat, name, arg in _mod.ROUTES) + _ROUTES

    def _schema(fn):
        """Build OpenAI tool schema from function signature and docstring."""
        args = fn.__code__.co_varnames[:fn.__code__.co_argcount]
        return {"type": "function", "function": {
            "name": fn.__name__, "description": fn.__doc__,
            "parameters": {"type": "object", "properties": {a: {"type": "string"} for a in args},
                           "required": [a for a in args if a != "target" or fn is t.open_url]}}}

    def _named_page(task):
        """The URL or known site a task mentions, if any."""
        m = re.search(r"https?://\S+|\b[\w-]+(?:\.[\w-]+)+(?:/\S*)?", task)
        if m and t._url(m.group(0).rstrip(".,")):
            return t._url(m.group(0).rstrip(".,"))
        low = task.lower()
        return next((url for name, url in sorted(t.SITES.items(), key=lambda kv: -len(kv[0]))
                     if re.search(rf"\b{re.escape(name)}\b", low)), None)


# anything past the first verb phrase means more than one step: that is agent() work
_MULTISTEP = re.compile(r"\b(?:and (?:then )?(?:tell|read|find|summar|poke|look|check|see|click)|poke around|then )", re.I)
# "look at my screen and tell me what's wrong" is one question about one picture, not two steps
_EYES = re.compile(r"^(?:look at|describe|see|check out|what(?:'s| is) in) (?:(?:my |the )?screen|\S+\.(?:png|jpe?g|heic|gif|webp|tiff?|bmp)|this)\b"
                    r"|^what am i holding\b|^(?:read (?:this|that) label|what does (?:this|that) label say)\b|^(?:use|look through) (?:the |your )?camera\b", re.I)
# an explicit multi-step screen JOB, named as such: her own screen agent plans it, click_text/type_text/press_key one
# step at a time, every step confirmed. Ahead of _MULTISTEP so "log me into X and check my email" does not go to the
# tool-picking agent(), which has no screen tools at all (they are NOT_FOR_MODELS on purpose).
_SCREEN_JOB = re.compile(r"^(?:log (?:me )?(?:in|into)|sign (?:me )?(?:in|into)|walk me through|step me through)\b", re.I)
_ACTION = re.compile(r"^(?:open|launch|start|go to|visit|browse|pull up|search|google|look up|poke around|take a|grab a|screenshot|make|design|draw|paint|repaint|play|pause|skip|remind me|set a)\b", re.I)
# People do not type commands, they ask. "can you open chrome", "hey open
# github", "open up spotify for me please". Stripped once here so every route
# and is_action() see the bare command, instead of each regex growing its own
# politeness prefix. Live-tested 2026-09-20: 10 of 16 natural phrasings missed.
_LEAD = re.compile(r"^(?:(?:hey|ok|okay|yo|samantha|please|now|just)[, ]+)*"
                   r"(?:(?:can|could|would|will) you (?:please )?|i (?:want|need|would like|'d like) (?:you )?to |let's |go ahead and )?(?:please )?", re.I)
_TAIL = re.compile(r"(?:[, ]+(?:please|for me|real quick|now|thanks|thank you))+$", re.I)


# invisible and look-alike characters: a full-width "ｏｐｅｎ" is "open", and a control or direction-override
# character never rides into a note, a reminder or a search
_INVISIBLE = re.compile(r"[\x00-\x1f\x7f​-‏‪-‮⁠-⁩﻿]")
_DANGLING = re.compile(r"(?:[,;]?\s+(?:and then|and|then))+$", re.I)  # "open youtube and" is just "open youtube"
_CONTRACT = re.compile(r"\b(what|how|where|who)s\b", re.I)  # people type "whats the weather", the routes say "what's"


def _bare(query):
    """Strip politeness markers (please, can you, etc.) from a command."""
    q = _INVISIBLE.sub("", unicodedata.normalize("NFKC", query)).strip().rstrip(".!?")
    q = _DANGLING.sub("", _CONTRACT.sub(r"\1's", q))
    return _TAIL.sub("", _LEAD.sub("", q, count=1)).strip()


def is_action(query):
    """Check if query starts with an action verb, after stripping politeness markers."""
    return bool(_ACTION.match(_bare(query)))
