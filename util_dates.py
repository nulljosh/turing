"""Samantha's time and date tools: the time in a city, today's date, days until a date, and exact date arithmetic.
Split out of tools_util.py, which re-exports every name here, so callers and the ROUTES table are unchanged."""
import re
from datetime import date, datetime
from zoneinfo import ZoneInfo


# ---------- time and dates ----------

_ZONES = {"tokyo": "Asia/Tokyo", "london": "Europe/London", "paris": "Europe/Paris", "berlin": "Europe/Berlin",
          "new york": "America/New_York", "los angeles": "America/Los_Angeles", "vancouver": "America/Vancouver",
          "toronto": "America/Toronto", "chicago": "America/Chicago", "denver": "America/Denver", "sydney": "Australia/Sydney",
          "dubai": "Asia/Dubai", "singapore": "Asia/Singapore", "hong kong": "Asia/Hong_Kong", "mumbai": "Asia/Kolkata",
          "delhi": "Asia/Kolkata", "moscow": "Europe/Moscow", "seoul": "Asia/Seoul", "beijing": "Asia/Shanghai",
          "shanghai": "Asia/Shanghai", "cairo": "Africa/Cairo", "sao paulo": "America/Sao_Paulo",
          "mexico city": "America/Mexico_City", "auckland": "Pacific/Auckland", "honolulu": "Pacific/Honolulu"}


def time_in(place=""):
    """The current time in a city (Tokyo, London, New York...), or here when no city is given."""
    key = place.lower().strip()
    if not key:
        return datetime.now().strftime("It is %-I:%M %p.")
    try:
        zone = ZoneInfo(_ZONES.get(key, place.strip().replace(" ", "_")))
    except Exception:
        return f"I do not know the time zone for {place.strip()}."
    return datetime.now(zone).strftime(f"It is %-I:%M %p on %A in {place.strip().title()}.")


def current_date():
    """Today's date and weekday."""
    return datetime.now().strftime("It is %A, %B %-d, %Y.")


_HOLIDAYS = {"christmas": (12, 25), "new year": (1, 1), "new years": (1, 1), "halloween": (10, 31),
             "canada day": (7, 1), "valentines day": (2, 14), "valentine's day": (2, 14)}


def days_until(target):
    """How many days from today until a date (2026-12-25) or a holiday (christmas, halloween, new year)."""
    key, today = target.lower().strip(), date.today()
    try:
        if key in _HOLIDAYS:
            d = date(today.year, *_HOLIDAYS[key])
            d = d if d >= today else date(today.year + 1, *_HOLIDAYS[key])
        else:
            d = date.fromisoformat(key)
    except ValueError:
        return 'Give me a date like 2026-12-25, or a holiday like christmas.'
    n = (d - today).days
    return "That is today." if n == 0 else f"{abs(n)} day{'s' * (abs(n) != 1)} {'until' if n > 0 else 'since'} {d.strftime('%B %-d, %Y')}."


_MONTHS = {m: i for i, m in enumerate(("january", "february", "march", "april", "may", "june", "july", "august",
                                         "september", "october", "november", "december"), 1)}
_MONTHS.update({m[:3]: i for m, i in list(_MONTHS.items())})
_MONTHS["sept"] = 9
_COUNT = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}


def _day(text):
    """A date from what people type: today, tomorrow, yesterday, 2026-12-25, July 4 1976, 4 July 1976, or a holiday
    (its next date). None when it is not one, or not a real day."""
    t = re.sub(r"[,.]|\b(?:the|of)\b|(?<=\d)(?:st|nd|rd|th)\b", " ", text.lower()).split()
    key, today = " ".join(t), date.today()
    try:
        if key in ("today", "now"):
            return today
        if key in ("tomorrow", "yesterday"):
            return date.fromordinal(today.toordinal() + (1 if key == "tomorrow" else -1))
        if key in _HOLIDAYS:
            d = date(today.year, *_HOLIDAYS[key])
            return d if d >= today else date(today.year + 1, *_HOLIDAYS[key])
        if len(t) == 1:
            return date.fromisoformat(t[0])
        if len(t) == 3 and t[0] in _MONTHS and t[1].isdigit() and t[2].isdigit():
            return date(int(t[2]), _MONTHS[t[0]], int(t[1]))
        if len(t) == 3 and t[1] in _MONTHS and t[0].isdigit() and t[2].isdigit():
            return date(int(t[2]), _MONTHS[t[1]], int(t[0]))
    except (ValueError, OverflowError):
        return None
    return None


def _shift(d, n, unit):
    """d moved by n days, weeks, months or years. A month or year landing past the month's end keeps to its last day."""
    if unit in ("day", "week"):
        return date.fromordinal(d.toordinal() + n * (7 if unit == "week" else 1))
    months = d.month - 1 + n * (12 if unit == "year" else 1)
    y, m = d.year + months // 12, months % 12 + 1
    last = (date(y + (m == 12), m % 12 + 1, 1).toordinal() - 1) - date(y, m, 1).toordinal() + 1
    return date(y, m, min(d.day, last))


_MONTH_NAMES = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December")
_DAY_NAMES = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


def _long(d):
    """July 4, 1976. Spelled out by hand: strftime's %Y writes year 1 as "1" on Linux and "0001" on macOS."""
    return f"{_MONTH_NAMES[d.month - 1]} {d.day}, {d.year}"


def _say(d):
    """A date the way she says it: Sunday, July 4, 1976."""
    return f"{_DAY_NAMES[d.weekday()]}, {_long(d)}"


def date_math(question):
    """Dates worked out exactly. Takes "100 days from now", "3 weeks ago", "2 months after 2026-01-31",
    "weekday July 4 1976" or "between 2026-01-01 and christmas"."""
    q = question.strip().lower()
    bad = 'Say it like "100 days from now", "weekday July 4 1976" or "between 2026-01-01 and 2026-12-25".'
    try:
        m = re.fullmatch(r"(\d{1,6}|a|an|one|two|three|four|five|six|seven|eight|nine|ten) (day|week|month|year)s? (from|after|before|ago)(?: (.+))?", q)
        if m:
            n = int(m.group(1)) if m.group(1).isdigit() else _COUNT[m.group(1)]
            base = date.today() if m.group(3) == "ago" or m.group(4) in (None, "now", "today") else _day(m.group(4))
            if m.group(3) == "ago" and m.group(4) or base is None:
                return bad
            d = _shift(base, -n if m.group(3) in ("before", "ago") else n, m.group(2))
            said = q + " now" if q.endswith(" from") else q  # the router drops a trailing "now" as filler
            return f"{said[0].upper() + said[1:]} is {_say(d)}."
        m = re.fullmatch(r"weekday (.+)", q)
        if m:
            d = _day(m.group(1))
            if not d:
                return bad
            tense = "is" if d == date.today() else "was" if d < date.today() else "will be"
            return f"{_long(d)} {tense} a {_DAY_NAMES[d.weekday()]}."
        m = re.fullmatch(r"between (.+?) and (.+)", q)
        if m:
            a, b = _day(m.group(1)), _day(m.group(2))
            if not a or not b:
                return bad
            n = abs((b - a).days)
            return f"{n:,} day{'s' * (n != 1)} between {_long(a)} and {_long(b)}."
    except (ValueError, OverflowError):
        return "That date is out of range: I can do years 1 to 9999."
    return bad
