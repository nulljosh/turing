"""Samantha's organizer family: the parts of Reminders, Calendar and Notes that new_reminder, calendar_today
and new_note do not reach yet. Reads (list_reminders, calendar_tomorrow, search_notes) are read only, same
class as unread_mail. Writes (complete_reminder, add_event, append_note) ask first, same as new_note and
new_reminder. Every AppleScript rides through tools_apps._app, argv only, never spliced into the script.
"""
import re

from tools_apps import _app, _when

_I = re.I


# ---------- reminders: list and complete ----------

_LIST_REMINDERS = '''on run argv
set q to item 1 of argv
set out to ""
tell application "Reminders"
repeat with r in (reminders whose completed is false)
set n to name of r
if q is "" or n contains q then
set dd to due date of r
if dd is missing value then
set out to out & n & linefeed
else
set out to out & n & " (due " & (dd as string) & ")" & linefeed
end if
end if
end repeat
end tell
return out
end run'''


def list_reminders(query=""):
    """Incomplete reminders, read only, across every list. Due date shown when set. A word narrows it by name."""
    out = _app(_LIST_REMINDERS, query.strip())
    lines = [l for l in out.splitlines() if l.strip()]
    if not lines:
        return f"No reminders matching {query.strip()!r}." if query.strip() else "No reminders."
    shown = "\n".join(lines[:10])
    return shown + (f"\n...and {len(lines) - 10} more." if len(lines) > 10 else "")


_FIND_REMINDERS = '''on run argv
set q to item 1 of argv
set out to ""
tell application "Reminders"
repeat with r in (reminders whose completed is false)
set n to name of r
if n contains q then
set out to out & n & linefeed
end if
end repeat
end tell
return out
end run'''

_COMPLETE_REMINDER = '''on run argv
set nm to item 1 of argv
tell application "Reminders"
repeat with r in (reminders whose completed is false)
if name of r is nm then
set completed of r to true
exit repeat
end if
end repeat
end tell
end run'''


def complete_reminder(name):
    """Mark the first incomplete reminder whose name contains the text as completed. Says plainly when none
    match, and when several match lists them and changes nothing. Asks first."""
    name = name.strip().strip("'\"")
    if not name:
        return "Complete which reminder? Give me a name."
    matches = [l for l in _app(_FIND_REMINDERS, name).splitlines() if l.strip()]
    if not matches:
        return f"No reminder matching {name!r}."
    if len(matches) > 1:
        return f"That matches {len(matches)} reminders: " + ", ".join(matches[:10]) + ". Be more specific."
    _app(_COMPLETE_REMINDER, matches[0])
    return f"Completed: {matches[0]}."


# ---------- calendar: add an event, tomorrow's list ----------

_ADD_EVENT = '''on run argv
set d to current date
set day of d to 1
set year of d to (item 2 of argv) as integer
set month of d to (item 3 of argv) as integer
set day of d to (item 4 of argv) as integer
set hours of d to (item 5 of argv) as integer
set minutes of d to (item 6 of argv) as integer
set seconds of d to 0
set d2 to d + 1 * hours
tell application "Calendar"
set c to first calendar whose writable is true
tell c to make new event with properties {summary:item 1 of argv, start date:d, end date:d2}
end tell
end run'''


def add_event(text):
    """Add an event to the first writable calendar: title and start time, one hour long. Reuses tools_apps._when
    for the date, so "tomorrow at noon" and "on friday at 3pm" work the same as a reminder. No time given is an
    honest ask, not a guess. Asks first."""
    title, start, why = _when(text.strip())
    if why:
        return why
    if not start:
        return f"What time should I put \"{title[:80]}\" on the calendar? Give me a day and time, like \"tomorrow at noon\"."
    _app(_ADD_EVENT, title, str(start.year), str(start.month), str(start.day), str(start.hour), str(start.minute))
    return f"Added to your calendar: {title[:80]}, {start.strftime('%A %B %-d at %-I:%M %p')}."


# ponytail: same shape as calendar_today in tools_apps.py, one day further out
_TOMORROW = '''set d0 to current date
set time of d0 to 0
set d0 to d0 + 1 * days
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


def calendar_tomorrow():
    """What is on the calendar tomorrow. Read only."""
    return _app(_TOMORROW) or "Nothing on the calendar tomorrow."


# ---------- notes: search and append ----------

_SEARCH_NOTES = '''on run argv
set q to item 1 of argv
set out to ""
set n to 0
tell application "Notes"
repeat with nt in notes
set nm to name of nt
set bd to body of nt
if nm contains q or bd contains q then
set n to n + 1
if n > 10 then exit repeat
set out to out & nm & " || " & bd & linefeed
end if
end repeat
end tell
return out
end run'''


def search_notes(query):
    """Notes.app notes whose name or body contains the word: names and a short snippet, max 10. Read only,
    private, same class as unread_mail."""
    query = query.strip()
    if not query:
        return "Search notes for what? Give me a word."
    lines = [l for l in _app(_SEARCH_NOTES, query).splitlines() if l.strip()]
    if not lines:
        return f"No notes matching {query!r}."
    shown = []
    for l in lines[:10]:
        name, _, body = l.partition(" || ")
        snippet = re.sub(r"<[^>]+>", " ", body)
        snippet = re.sub(r"\s+", " ", snippet).strip()[:80]
        shown.append(f"{name}: {snippet}" if snippet else name)
    return "\n".join(shown)


_FIND_NOTE = '''on run argv
set q to item 1 of argv
set out to ""
tell application "Notes"
repeat with nt in notes
if name of nt contains q then
set out to out & name of nt & linefeed
end if
end repeat
end tell
return out
end run'''

_APPEND_NOTE = '''on run argv
set nm to item 1 of argv
set ln to item 2 of argv
tell application "Notes"
repeat with nt in notes
if name of nt is nm then
set body of nt to (body of nt) & "<br>" & ln
exit repeat
end if
end repeat
end tell
end run'''


def append_note(request):
    """Append a line to the first note whose name contains the note name. Takes 'content<TAB>note name'. No
    matching note is an honest refusal; it never creates one. Asks first."""
    content, _, note_name = request.partition("\t")
    content, note_name = content.strip(), note_name.strip()
    if not content or not note_name:
        return "Append what, to which note?"
    matches = [l for l in _app(_FIND_NOTE, note_name).splitlines() if l.strip()]
    if not matches:
        return f"No note matching {note_name!r}. I never create one on my own."
    _app(_APPEND_NOTE, matches[0], content)
    return f"Added to {matches[0]}: {content[:80]}"


TOOLS = (list_reminders, complete_reminder, add_event, calendar_tomorrow, search_notes, append_note)

# (pattern, tool name, what to hand it), same shape as tools_files.ROUTES. tools.py must splice these in AHEAD of
# the base router's "search ... for" and "add ... calendar/note" catch-alls, or those steal the phrasing first.
_CAL = re.compile(r"^(?:add|put|schedule|create|new) (?:the event |an event |a )?(.+?)\s+(?:to|on)(?: my)? calendar\b(.*)$", _I)
_APPEND1 = re.compile(r"^add (.+) to (?:my |the )?(.+?) note$", _I)
_APPEND2 = re.compile(r"^append (.+) to (?:the )?note (.+)$", _I)

ROUTES = (
    (re.compile(r"^(?:what are |list |show(?: me)? )?(?:my )?reminders(?: (?:about|for|named|called) (.+))?$", _I), "list_reminders", lambda m: m.group(1) or ""),
    (re.compile(r"^(?:complete|finish) (?:the )?reminder(?: to| for)? (.+)$", _I), "complete_reminder", lambda m: m.group(1)),
    (re.compile(r"^mark (.+?) as (?:done|complete|completed)$", _I), "complete_reminder", lambda m: m.group(1)),
    (re.compile(r"^check off (.+)$", _I), "complete_reminder", lambda m: m.group(1)),
    (re.compile(r"^what(?:'s| is) on (?:my |the )?(?:calendar|schedule|agenda) tomorrow\b|^(?:my )?(?:calendar|schedule|agenda) (?:for )?tomorrow$|^what do i have tomorrow", _I),
     "calendar_tomorrow", lambda m: ""),
    (re.compile(r"^search (?:my |the )?notes for (.+)$|^find (.+) in (?:my |the )?notes$", _I), "search_notes", lambda m: m.group(1) or m.group(2)),
    (_APPEND1, "append_note", lambda m: m.group(1) + "\t" + m.group(2)),
    (_APPEND2, "append_note", lambda m: m.group(1) + "\t" + m.group(2)),
    (_CAL, "add_event", lambda m: (m.group(1).strip() + " " + m.group(2).strip()).strip()),
)


def demo():
    """Self-check: the pure parts, routing and formatting, no AppleScript needed."""
    m = _CAL.match("add lunch with sam to my calendar tomorrow at noon")
    assert m and (m.group(1).strip() + " " + m.group(2).strip()).strip() == "lunch with sam tomorrow at noon", m and m.groups()
    m = _CAL.match("put dentist on friday at 3pm on my calendar")
    assert m and (m.group(1).strip() + " " + m.group(2).strip()).strip() == "dentist on friday at 3pm", m and m.groups()
    m = _APPEND1.match("add eggs to my shopping note")
    assert m.group(1) == "eggs" and m.group(2) == "shopping", m.groups()
    m = _APPEND2.match("append call bob to the note todo")
    assert m.group(1) == "call bob" and m.group(2) == "todo", m.groups()
    for pat, name, arg in ROUTES:
        assert name in {f.__name__ for f in TOOLS}
    assert all(f.__doc__ for f in TOOLS)
    print("tools_organizer ok")


if __name__ == "__main__":
    demo()
