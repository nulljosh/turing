"""Samantha driving the Mac's own apps: Music, Weather (a web lookup), timers, Notes, Reminders, Calendar, Mail.
Split out of tools.py to keep it under the line-count law (CLAUDE.md, File size); every name is re-exported there
so nothing that imports tools stops working.
"""
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request

HEADLESS = os.environ.get("SAMANTHA_HEADLESS") == "1"


def _app(script, *args):
    """AppleScript that drives another app. Text rides in argv, never spliced into the script. Headless does nothing: no app launches, no note gets written."""
    if HEADLESS:
        return ""
    r = subprocess.run(["osascript", "-e", script, *args], capture_output=True, text=True, timeout=30)
    return (r.stdout or r.stderr).strip()


_MUSIC = {"play": ("play", "Playing."), "pause": ("pause", "Paused."),
          "next": ("next track", "Skipped."), "previous": ("previous track", "Went back one.")}
_NOW_PLAYING = '''if application "Music" is running then
tell application "Music"
if player state is playing then return (name of current track) & " by " & (artist of current track)
end tell
end if
return ""'''


def music(command):
    """Control the Music app. command is one of: play, pause, next, previous, playing."""
    c = command.strip().lower()
    if c == "playing":
        return _app(_NOW_PLAYING) or "Nothing is playing."
    if c not in _MUSIC:
        return f"I can play, pause, skip, go back, or tell you what's playing. Not {command!r}."
    # ponytail: Music.app only, no "play <song>". Add a library search when she gets asked for one.
    _app(f'tell application "Music" to {_MUSIC[c][0]}')
    return _MUSIC[c][1]


def weather(place=""):
    """Current weather. Takes a city, or nothing for here."""
    # ponytail: wttr.in one-liner, located by IP. Swap for Open-Meteo if it gets flaky.
    url = "https://wttr.in/" + urllib.parse.quote(place.strip()) + "?format=%l:+%C,+%t,+feels+%f"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "curl/8"}), timeout=10) as r:
            out = r.read(300).decode("utf-8", "ignore").strip()
    except Exception as e:
        return f"Couldn't get the weather: {e}"
    return out if "°" in out else f"No weather for {place!r}."


_TIMER = ("import sys,time,subprocess;time.sleep(float(sys.argv[1]));"
          "subprocess.run(['osascript','-e','display notification \"Time is up.\" with title \"Samantha\" sound name \"Glass\"']);"
          "subprocess.run(['say','Time is up'])")


_NUMBER_WORDS = {w: n for n, w in enumerate("zero one two three four five six seven eight nine ten".split())} | {"a": 1, "an": 1, "half": 0.5}


def duration(text):
    """Minutes in a spoken length of time: "90 seconds", "an hour", "half an hour", "5". None if it is not one."""
    t = str(text).lower().strip()
    m = re.match(r"^(\d+(?:\.\d+)?|[a-z]+)(?: an| a)?[ -]?(s|m|h)?[a-z]*$", t)
    if not m:
        return None
    n = float(m.group(1)) if m.group(1)[0].isdigit() else _NUMBER_WORDS.get(m.group(1))
    return None if n is None else round(n * {"s": 1 / 60, "m": 1, "h": 60}[m.group(2) or "m"], 4)


def timer(minutes):
    """Start a timer. Takes a length of time: "5", "90 seconds", "half an hour". Notifies and speaks when it is done."""
    span = duration(minutes)
    if span is None:
        return f"{minutes!r} is not a length of time."
    secs = span * 60
    if not 0 < secs <= 86400:
        return "A timer runs from a second to a day."
    # ponytail: a sleeping child process. No cancel, gone on reboot. Fine for tea.
    if not HEADLESS:
        subprocess.Popen([sys.executable, "-c", _TIMER, str(secs)], start_new_session=True)
    return f"Timer set for {secs / 60:g} minutes." if secs >= 60 else f"Timer set for {secs:g} seconds."


def new_note(text):
    """Create a note in the Notes app."""
    _app('on run argv\ntell application "Notes" to make new note with properties {body:item 1 of argv}\nend run', text)
    return f"Noted: {text[:80]}"


_WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
_TIME = r"(noon|midnight|\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)?)"
_DAY = r"(today|tonight|tomorrow|" + "|".join(_WEEKDAYS) + r"|\d{4}-\d{2}-\d{2})"
_WHEN_TAIL = re.compile(rf"^(.+?)(?:\s+in\s+(\S+(?:\s+\S+)?)|\s+(?:on\s+)?{_DAY}(?:\s+at\s+{_TIME})?|\s+at\s+{_TIME}(?:\s+(?:on\s+)?{_DAY})?)$", re.I)
_WHEN_HEAD = re.compile(rf"^((?:in\s+\S+(?:\s+\S+)?|(?:on\s+)?{_DAY}(?:\s+at\s+{_TIME})?|at\s+{_TIME}(?:\s+(?:on\s+)?{_DAY})?))\s+(?:to|that|about)?\s*(.+)$", re.I)
_DUE = '''on run argv
set d to current date
set day of d to 1
set year of d to (item 2 of argv) as integer
set month of d to (item 3 of argv) as integer
set day of d to (item 4 of argv) as integer
set hours of d to (item 5 of argv) as integer
set minutes of d to (item 6 of argv) as integer
set seconds of d to 0
tell application "Reminders" to make new reminder with properties {name:item 1 of argv, due date:d}
end run'''


def _when(text):
    """(title, due datetime or None, why) from a reminder: "call mom tomorrow at 9am", "in 20 minutes water the
    plants", "on friday at 5pm pay rent". A bare hour of 1 to 7 means the afternoon. Repeats are a why, not a date."""
    from datetime import date, datetime, timedelta
    from util_dates import _clock_of, _day
    if re.search(r"\b(?:every|each|daily|weekly|hourly)\b", text, re.I):
        return text, None, ("I can set a reminder once, with a time, but not one that repeats: Reminders only takes "
                            "repeats from its own window. Say it like \"remind me tomorrow at 9am to water the plants\".")
    m = _WHEN_TAIL.match(text)
    if not m:
        head = _WHEN_HEAD.match(text)
        if not head:
            return text, None, None
        m = _WHEN_TAIL.match(f"{head.group(head.re.groups)} {head.group(1)}")
    title, span = m.group(1).strip(), m.group(2)
    day_word = m.group(3) or m.group(6)  # "tomorrow at 9am" fills 3 and 4; "at 9am tomorrow" fills 5 and 6
    clock = m.group(4) or m.group(5)
    now = datetime.now()
    if span:
        mins = duration(span)
        return (title, now + timedelta(minutes=mins), None) if mins else (text, None, None)
    when = now.date()
    if day_word:
        w = day_word.lower()
        if w in _WEEKDAYS:
            when = when + timedelta(days=(_WEEKDAYS.index(w) - when.weekday()) % 7 or 7)
        elif w != "tonight":
            when = _day(w) or when
    hm = _clock_of(clock) if clock else ((20, 0) if (day_word or "").lower() == "tonight" else (9, 0))
    if not hm:
        return text, None, None
    h, mi = hm
    if clock and not re.search(r"am|pm|a\.m|p\.m|noon|midnight", clock, re.I) and 1 <= h <= 7:
        h += 12  # ponytail: "at 5" is five in the afternoon; say 5am if you mean it
    due = datetime(when.year, when.month, when.day, h, mi)
    if not day_word and due <= now:
        due += timedelta(days=1)
    return title, due, None


def new_reminder(text):
    """Add a reminder to the Reminders app, with a due date when one is said ("tomorrow at 9am", "in 20 minutes", "on friday")."""
    title, due, why = _when(text.strip())
    if why:
        return why
    if not due:
        _app('on run argv\ntell application "Reminders" to make new reminder with properties {name:item 1 of argv}\nend run', title)
        return f"I'll remind you: {title[:80]}"
    _app(_DUE, title, str(due.year), str(due.month), str(due.day), str(due.hour), str(due.minute))
    return f"I'll remind you: {title[:80]}, {due.strftime('%A %B %-d at %-I:%M %p')}."


# ponytail: a repeating event only shows on the day it was first made, Calendar's scripting does not expand them. EventKit if that bites.
_TODAY = '''set d0 to current date
set time of d0 to 0
set d1 to d0 + 1 * days
set out to ""
tell application "Calendar"
repeat with c in calendars
repeat with e in (every event of c whose start date is greater than or equal to d0 and start date is less than d1)
set out to out & (time string of (get start date of e)) & " " & (summary of e) & linefeed
end repeat
end repeat
end tell
return out'''


def calendar_today():
    """What is on the calendar today."""
    return _app(_TODAY) or "Nothing on the calendar today."


_UNREAD_MAIL = '''on run argv
set q to item 1 of argv
set out to ""
set n to 0
tell application "Mail"
    set msgs to (messages of inbox whose read status is false)
    repeat with m in msgs
        set n to n + 1
        if n > 25 then exit repeat
        set s to (sender of m) as string
        set subj to (subject of m) as string
        if q is "" or s contains q or subj contains q then
            set out to out & s & " || " & subj & linefeed
        end if
    end repeat
end tell
return out
end run'''


def unread_mail(query=""):
    """Unread mail in your inbox, across every account, read only. A word narrows it to messages naming that word
    in the sender or subject, so "anything from the bank" only shows those."""
    out = _app(_UNREAD_MAIL, query.strip())
    if not out.strip():
        return f"No unread mail from or about {query.strip()!r}." if query.strip() else "No unread mail."
    lines = [l for l in out.splitlines() if l.strip()]
    shown = "\n".join(lines[:10])
    return shown + (f"\n...and {len(lines) - 10} more." if len(lines) > 10 else "")


# ---------- what needs me: unread mail, today's calendar and due reminders, ranked into three lines ----------

_DUE_REMINDERS = '''set d0 to current date
set time of d0 to 0
set d1 to d0 + 1 * days
set out to ""
tell application "Reminders"
repeat with r in (reminders whose completed is false)
set dd to due date of r
if dd is not missing value and dd < d1 then
if dd < d0 then
set tag to "overdue"
else
set tag to "today"
end if
set out to out & (name of r) & " (" & tag & ")" & linefeed
end if
end repeat
end tell
return out'''


def _due_reminders():
    """Reminders due today or overdue, read only, across every list."""
    out = _app(_DUE_REMINDERS)
    return out.strip() or "Nothing due."


def needs_attention():
    """"What needs my attention": one answer built from unread mail, today's calendar and due reminders, ranked,
    with the biggest local model on this Mac (the same path summarize uses) writing three short lines. Says
    plainly when a source is empty; nothing here is invented."""
    mail, cal, due = unread_mail(""), calendar_today(), _due_reminders()
    if mail == "No unread mail." and cal == "Nothing on the calendar today." and due == "Nothing due.":
        return "Nothing needs your attention: no unread mail, nothing on the calendar today, and no reminders due."
    import tools_llm
    prompt = ("Below are three real sources for one person, right now: unread mail, today's calendar and due "
              "reminders. Write exactly three short lines, one per source, ranked with whatever needs attention "
              "first at the top. If a source below says it is empty, say so plainly in its line, and invent "
              "nothing that is not in the source text. No headings, no lists, no em dashes.\n\n"
              f"Unread mail:\n{mail}\n\nToday's calendar:\n{cal}\n\nReminders due:\n{due}")
    reply = tools_llm.ask_llm(prompt)
    return reply.rsplit("\n(Answered by", 1)[0]


# ---------- am I free: the calendar's open gaps for a day or the week, not just today's list ----------

_RANGE = '''on run argv
set d0 to current date
set time of d0 to 0
set d0 to d0 + (item 1 of argv as integer) * days
set d1 to d0 + (item 2 of argv as integer) * days
set out to ""
tell application "Calendar"
repeat with c in calendars
repeat with e in (every event of c whose start date is less than d1 and end date is greater than d0)
set s0 to (start date of e) - d0
set e0 to (end date of e) - d0
if s0 < 0 then set s0 to 0
if e0 > (d1 - d0) then set e0 to (d1 - d0)
set out to out & s0 & " " & e0 & linefeed
end repeat
end repeat
end tell
return out
end run'''


def _busy_blocks(today, days_ahead):
    """[(start datetime, end datetime)] for every calendar event between today and days_ahead days out, clipped
    to that range. Empty when Calendar has nothing there, or cannot be reached."""
    from datetime import datetime, timedelta
    base = datetime.combine(today, datetime.min.time())
    blocks = []
    for line in _app(_RANGE, "0", str(days_ahead)).splitlines():
        parts = line.split()
        if len(parts) != 2:
            continue
        try:
            s, e = float(parts[0]), float(parts[1])
        except ValueError:
            continue
        blocks.append((base + timedelta(seconds=s), base + timedelta(seconds=e)))
    return blocks


_DAYPART = {"morning": (9, 12), "afternoon": (12, 18), "evening": (18, 22)}
_WORKDAY = (9, 18)


def free_when(request):
    """"Am I free Thursday afternoon", "when am I free this week": the calendar's open gaps for a day or the
    week, business hours (9am to 6pm, or the named morning/afternoon/evening), not just today's list. Says
    plainly when the calendar has nothing there for that window; it never invents a meeting."""
    from datetime import datetime, timedelta
    from util_dates import _hm
    q = request.strip().lower()
    today = datetime.now().date()
    if "week" in q:
        days = [today + timedelta(days=n) for n in range(7 - today.weekday()) if (today + timedelta(days=n)).weekday() < 5]
        if not days:  # asked over a weekend with no workday left in it: the coming Monday to Friday
            days = [today + timedelta(days=n) for n in range(7 - today.weekday(), 14 - today.weekday()) if (today + timedelta(days=n)).weekday() < 5]
    else:
        d = today + timedelta(days=1) if "tomorrow" in q else next(
            (today + timedelta(days=(_WEEKDAYS.index(w) - today.weekday()) % 7) for w in _WEEKDAYS if w in q), today)
        days = [d]
    part = next((p for p in _DAYPART if p in q), None)
    window = _DAYPART[part] if part else _WORKDAY
    blocks = _busy_blocks(today, (days[-1] - today).days + 1)
    lines = []
    for d in days:
        day_start = datetime.combine(d, datetime.min.time()) + timedelta(hours=window[0])
        day_end = datetime.combine(d, datetime.min.time()) + timedelta(hours=window[1])
        busy = sorted((max(s, day_start), min(e, day_end)) for s, e in blocks if s < day_end and e > day_start)
        cursor, gaps = day_start, []
        for s, e in busy:
            if s > cursor:
                gaps.append((cursor, s))
            cursor = max(cursor, e)
        if cursor < day_end:
            gaps.append((cursor, day_end))
        name = "Today" if d == today else "Tomorrow" if d == today + timedelta(days=1) else _WEEKDAYS[d.weekday()].capitalize()
        if not gaps:
            lines.append(f"{name}: booked solid" + (f" this {part}." if part else "."))
        else:
            lines.append(f"{name}: free " + ", ".join(f"{_hm(s)} to {_hm(e)}" for s, e in gaps) + ".")
    return " ".join(lines)
