"""Samantha's utility tools: thirty-one small things that need no app and no network.

Math and text (calculate, convert_units, dice, hashes, base64...) are pure Python.
The system readers (disk_space, uptime, memory_usage...) run one fixed argv each and
only read. Three tools touch the Mac (copy_to_clipboard, sleep_display,
reveal_in_finder) and stay silent under SAMANTHA_HEADLESS=1, so a test run never
clobbers a clipboard or blanks a screen. Like the rest of her hands there is no
shell: every command is a fixed list, never a string someone wrote.

ROUTES is the regex table tools.py appends to its own, so each of these also works
with no model in the loop.
"""
import ast
import base64
import hashlib
import json
import math
import operator
import os
import random
import re
import secrets
import shutil
import string
import subprocess
import uuid
from datetime import date, datetime
from zoneinfo import ZoneInfo

HEADLESS = os.environ.get("SAMANTHA_HEADLESS") == "1"


def _sh(argv, timeout=5):
    """Run one fixed argv and return its output, or "" if it is not here."""
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return ""
    return (r.stdout or "").strip()


def _num(x):
    """1.0 reads as 1, 0.1+0.2 reads as 0.3, big floats keep ten digits."""
    x = round(x, 10)
    return str(int(x)) if x == int(x) and abs(x) < 1e15 else str(x)


# ---------- math ----------

_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod, ast.Pow: operator.pow}
_FUNCS = {"sqrt": math.sqrt, "abs": abs, "round": round, "sin": math.sin, "cos": math.cos, "tan": math.tan, "log": math.log10, "ln": math.log}
_CONSTS = {"pi": math.pi, "e": math.e}


def _eval(node):
    """Walk a parsed expression. Numbers, + - * / // % **, a few functions, nothing else."""
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.Name) and node.id in _CONSTS:
        return _CONSTS[node.id]
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        v = _eval(node.operand)
        return v if isinstance(node.op, ast.UAdd) else -v
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        a, b = _eval(node.left), _eval(node.right)
        if isinstance(node.op, ast.Pow) and abs(b) > 1000:
            raise ValueError("that power is too big")
        return _OPS[type(node.op)](a, b)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _FUNCS and len(node.args) == 1 and not node.keywords:
        return _FUNCS[node.func.id](_eval(node.args[0]))
    raise ValueError("I only do plain arithmetic")


def calculate(expression):
    """Work out an arithmetic expression. Takes + - * / // % **, parentheses, sqrt, pi, and "15% of 80"."""
    text = expression.lower().replace("x", "*").replace("^", "**").replace(",", "").strip()
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*% of (\d+(?:\.\d+)?)", text)
    if m:
        return f"{_num(float(m.group(1)) * float(m.group(2)) / 100)}"
    try:
        return _num(_eval(ast.parse(text, mode="eval").body))
    except ZeroDivisionError:
        return "You cannot divide by zero."
    except ValueError as e:
        return f"Cannot work that out: {e}."
    except (SyntaxError, OverflowError, TypeError):
        return "Cannot work that out: I only do plain arithmetic."


_LENGTH = {"mm": .001, "cm": .01, "m": 1, "km": 1000, "in": .0254, "ft": .3048, "yd": .9144, "mi": 1609.344}
_MASS = {"g": .001, "kg": 1, "lb": .45359237, "oz": .028349523125}
_VOLUME = {"ml": .001, "l": 1, "cup": .2365882365, "gal": 3.785411784}
_TIME = {"s": 1, "min": 60, "h": 3600, "day": 86400, "week": 604800}
_UNIT_ALIASES = {
    "millimeter": "mm", "millimeters": "mm", "centimeter": "cm", "centimeters": "cm", "meter": "m", "meters": "m",
    "metre": "m", "metres": "m", "kilometer": "km", "kilometers": "km", "kilometre": "km", "kilometres": "km",
    "inch": "in", "inches": "in", "foot": "ft", "feet": "ft", "yard": "yd", "yards": "yd", "mile": "mi", "miles": "mi",
    "gram": "g", "grams": "g", "kilogram": "kg", "kilograms": "kg", "kilo": "kg", "kilos": "kg", "pound": "lb", "pounds": "lb",
    "lbs": "lb", "ounce": "oz", "ounces": "oz", "milliliter": "ml", "milliliters": "ml", "liter": "l", "liters": "l",
    "litre": "l", "litres": "l", "cups": "cup", "gallon": "gal", "gallons": "gal",
    "second": "s", "seconds": "s", "sec": "s", "minute": "min", "minutes": "min", "mins": "min", "hour": "h", "hours": "h",
    "hr": "h", "hrs": "h", "days": "day", "weeks": "week",
    "celsius": "c", "centigrade": "c", "fahrenheit": "f", "kelvin": "k", "°c": "c", "°f": "f"}
_TEMPS = ("c", "f", "k")


def convert_units(text):
    """Convert a quantity between units of length, weight, volume, time or temperature, like "5 km to miles"."""
    m = re.fullmatch(r"\s*(-?\d+(?:\.\d+)?)\s*([a-z°]+)\s+(?:to|in|into)\s+([a-z°]+)\s*", text.lower())
    if not m:
        return 'Say it like "5 km to miles".'
    n, a, b = float(m.group(1)), m.group(2), m.group(3)
    a, b = _UNIT_ALIASES.get(a, a), _UNIT_ALIASES.get(b, b)
    if a in _TEMPS and b in _TEMPS:
        c = n if a == "c" else (n - 32) * 5 / 9 if a == "f" else n - 273.15
        out = c if b == "c" else c * 9 / 5 + 32 if b == "f" else c + 273.15
        return f"{_num(n)} {a.upper()} is {_num(round(out, 2))} {b.upper()}."
    for table in (_LENGTH, _MASS, _VOLUME, _TIME):
        if a in table and b in table:
            return f"{_num(n)} {a} is {_num(round(n * table[a] / table[b], 4))} {b}."
    return f"I cannot convert {m.group(2)} to {m.group(3)}."


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


# ---------- chance ----------

def flip_coin():
    """Flip a coin."""
    return random.choice(("Heads.", "Tails."))


def roll_dice(spec="1d6"):
    """Roll dice like 2d6 or d20. Up to 100 dice with up to 1000 sides."""
    m = re.fullmatch(r"(\d*)d(\d+)", spec.lower().strip() or "1d6")
    if not m:
        return 'Say it like "2d6" or "d20".'
    n, sides = int(m.group(1) or 1), int(m.group(2))
    if not (1 <= n <= 100 and 2 <= sides <= 1000):
        return "Up to 100 dice with 2 to 1000 sides."
    rolls = [random.randint(1, sides) for _ in range(n)]
    return str(rolls[0]) if n == 1 else f"{' + '.join(map(str, rolls))} = {sum(rolls)}"


def random_number(bounds=""):
    """A random whole number between two numbers, 1 to 100 when none are given."""
    nums = [int(x) for x in re.findall(r"-?\d+", bounds)[:2]]
    lo, hi = (min(nums), max(nums)) if len(nums) == 2 else (1, 100)
    return str(random.randint(lo, hi))


def make_password(length="16"):
    """Make a random password. Takes a length from 8 to 64. Nothing is stored or sent anywhere."""
    n = max(8, min(64, int(length) if str(length).strip().isdigit() else 16))
    pool = string.ascii_letters + string.digits + "!@#$%^&*-_"
    return "".join(secrets.choice(pool) for _ in range(n))


def make_uuid():
    """Make a random UUID."""
    return str(uuid.uuid4())


# ---------- text ----------

def hash_text(text):
    """The SHA-256 hash of some text."""
    return hashlib.sha256(text.encode()).hexdigest()


def base64_encode(text):
    """Encode text as base64."""
    return base64.b64encode(text.encode()).decode()


def base64_decode(text):
    """Decode base64 back to text."""
    try:
        return base64.b64decode(text.strip(), validate=True).decode()
    except (ValueError, UnicodeDecodeError):
        return "That is not valid base64 text."


def word_count(text):
    """Count the words and characters in some text."""
    words = len(text.split())
    return f"{words} word{'s' * (words != 1)}, {len(text)} characters."


def reverse_text(text):
    """Reverse some text."""
    return text[::-1]


def shout(text):
    """Turn some text into capital letters."""
    return text.upper()


_MORSE = dict(zip("abcdefghijklmnopqrstuvwxyz0123456789",
                  ".- -... -.-. -.. . ..-. --. .... .. .--- -.- .-.. -- -. --- .--. --.- .-. ... - ..- ...- .-- -..- -.-- --.. "
                  "----- .---- ..--- ...-- ....- ..... -.... --... ---.. ----.".split()))


def morse_code(text):
    """Write some text in morse code. Letters and digits only."""
    return " ".join(_MORSE[c] for c in text.lower() if c in _MORSE) or "Nothing there to translate."


def json_pretty(text):
    """Tidy a JSON string into readable, indented form."""
    try:
        return json.dumps(json.loads(text), indent=2)[:2000]
    except ValueError:
        return "That is not valid JSON."


def is_prime(number):
    """Say whether a whole number is prime, and if it is not, its prime factors. Up to a trillion."""
    if not str(number).strip().isdigit() or not 2 <= int(number) <= 10 ** 12:
        return "Give me a whole number from 2 to a trillion."
    n, factors, p = int(number), [], 2
    while p * p <= n:
        while n % p == 0:
            factors.append(p)
            n //= p
        p += 1 if p == 2 else 2
    if n > 1:
        factors.append(n)
    return f"{number} is prime." if len(factors) == 1 else f"{number} is not prime: {' x '.join(map(str, factors))}."


def roman_numeral(number):
    """Write a number from 1 to 3999 in roman numerals."""
    if not str(number).strip().isdigit() or not 1 <= int(number) <= 3999:
        return "Roman numerals run from 1 to 3999."
    n, out = int(number), ""
    for value, sym in ((1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"), (50, "L"),
                       (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")):
        out, n = out + sym * (n // value), n % value
    return out


def tip(amount):
    """Work out 15, 18 and 20 percent tips on a bill."""
    try:
        bill = float(str(amount).replace("$", ""))
    except ValueError:
        return "Give me the bill amount."
    return f"Tip on {bill:.2f}: " + ", ".join(f"{p}% is {bill * p / 100:.2f}" for p in (15, 18, 20)) + "."


# ---------- this Mac, read only ----------

def disk_space():
    """How much disk space is free on this Mac."""
    u = shutil.disk_usage("/")
    return f"{u.free / 1e9:.0f} GB free of {u.total / 1e9:.0f} GB."


def uptime():
    """How long this Mac has been on since its last restart."""
    m = re.search(r"sec = (\d+)", _sh(["sysctl", "-n", "kern.boottime"]))
    if not m:
        return "I cannot read the uptime here."
    s = int(datetime.now().timestamp()) - int(m.group(1))
    d, h, mins = s // 86400, s % 86400 // 3600, s % 3600 // 60
    return "Up " + ", ".join(f"{v} {k}{'s' * (v != 1)}" for v, k in ((d, "day"), (h, "hour"), (mins, "minute")) if v or k == "minute") + "."


def memory_usage():
    """How much memory this Mac has and roughly how much is free."""
    total = _sh(["sysctl", "-n", "hw.memsize"])
    vm = _sh(["vm_stat"])
    if not total.isdigit() or not vm:
        return "I cannot read memory here."
    page = int((re.search(r"page size of (\d+)", vm) or [0, 16384])[1])
    free = sum(int((re.search(rf"Pages {k}:\s+(\d+)", vm) or [0, 0])[1]) for k in ("free", "inactive", "speculative"))
    return f"{int(total) / 2 ** 30:.0f} GB of memory, about {free * page / 2 ** 30:.1f} GB free."


def cpu_load():
    """How busy the processor is: the load average across its cores."""
    a, b, c = os.getloadavg()
    return f"Load average {a:.2f}, {b:.2f}, {c:.2f} on {os.cpu_count()} cores."


def ip_address():
    """This Mac's IP address on the local network."""
    ip = _sh(["ipconfig", "getifaddr", "en0"]) or _sh(["ipconfig", "getifaddr", "en1"])
    return ip or "No network address. Are you online?"


def wifi_name():
    """The Wi-Fi network this Mac is on."""
    ports = _sh(["networksetup", "-listallhardwareports"])
    m = re.search(r"Hardware Port: Wi-Fi\s+Device: (\w+)", ports)
    if not m:
        return "This Mac has no Wi-Fi."
    out = _sh(["networksetup", "-getairportnetwork", m.group(1)])
    return out.replace("Current Wi-Fi Network: ", "On ") if out.startswith("Current") else "Not on a Wi-Fi network."


def system_info():
    """The macOS version, chip and memory of this Mac."""
    ver, chip, mem = _sh(["sw_vers", "-productVersion"]), _sh(["sysctl", "-n", "machdep.cpu.brand_string"]), _sh(["sysctl", "-n", "hw.memsize"])
    if not ver:
        return "I cannot read the system info here."
    return f"macOS {ver} on {chip or 'an unknown chip'}" + (f", {int(mem) / 2 ** 30:.0f} GB." if mem.isdigit() else ".")


# ---------- this Mac, does something ----------

def copy_to_clipboard(text):
    """Put some text on the clipboard."""
    if not HEADLESS:
        subprocess.run(["pbcopy"], input=text[:10000], text=True, timeout=5)
    return "Copied."


def sleep_display():
    """Put the screen to sleep, which locks it if a password is required on wake."""
    if not HEADLESS:
        _sh(["pmset", "displaysleepnow"])
    return "Screen off."


def reveal_in_finder(path):
    """Show a file or folder in Finder. Only inside the home folder, never hidden files."""
    home = os.path.realpath(os.path.expanduser("~"))
    full = os.path.realpath(os.path.expanduser(path.strip()))
    rel = os.path.relpath(full, home)
    if rel.startswith("..") or any(part.startswith(".") and part != "." for part in rel.split(os.sep)) or not os.path.exists(full):
        return f"No file or folder {path.strip()} I am allowed to show."
    if not HEADLESS:
        _sh(["open", "-R", full])
    return f"Showing {os.path.basename(full)} in Finder."


TOOLS = (calculate, convert_units, time_in, current_date, days_until, flip_coin, roll_dice, random_number, make_password,
         make_uuid, hash_text, base64_encode, base64_decode, word_count, reverse_text, shout, morse_code, json_pretty,
         is_prime, roman_numeral, tip, disk_space, uptime, memory_usage, cpu_load, ip_address, wifi_name, system_info,
         copy_to_clipboard, sleep_display, reveal_in_finder)

_I = re.I
# (pattern, tool name, what to hand it). Names, not functions: tools.py looks each one up at call time.
ROUTES = (
    (re.compile(r"^(?:calc(?:ulate)?|compute|work out|math)[: ]+(.+)$", _I), "calculate", lambda m: m.group(1)),
    (re.compile(r"^convert (.+)$", _I), "convert_units", lambda m: m.group(1)),
    (re.compile(r"^what time is it in (.+)$|^(?:what(?:'s| is) )?(?:the )?time in (.+)$", _I), "time_in", lambda m: m.group(1) or m.group(2)),
    (re.compile(r"^what(?:'s| is)(?: the)? date(?: today)?$|^what day is it(?: today)?$|^today'?s date$", _I), "current_date", lambda m: ""),
    (re.compile(r"^(?:how many )?days? (?:until|till|to) (.+)$|^how long (?:until|till) (.+)$", _I), "days_until", lambda m: m.group(1) or m.group(2)),
    (re.compile(r"^(?:flip|toss) a coin$", _I), "flip_coin", lambda m: ""),
    (re.compile(r"^roll (\d*d\d+)$", _I), "roll_dice", lambda m: m.group(1)),
    (re.compile(r"^roll (?:a |the )?(?:dice|die)$", _I), "roll_dice", lambda m: "1d6"),
    (re.compile(r"^(?:pick |give me |generate )?(?:a )?random number(?: (?:between|from) (.+))?$", _I), "random_number", lambda m: m.group(1) or ""),
    (re.compile(r"^(?:generate|make|create|give me)(?: me)? (?:a |an )?(?:strong |secure |random )?password(?:(?: of| with)? (\d+)(?: char\w*)?)?$", _I), "make_password", lambda m: m.group(1) or "16"),
    (re.compile(r"^(?:generate|make|create|give me)(?: me)? (?:a |an )?(?:new |random )?(?:uuid|guid)$", _I), "make_uuid", lambda m: ""),
    (re.compile(r"^sha-?256(?: of)?[: ]+(.+)$|^hash(?: of|:) (.+)$", _I), "hash_text", lambda m: (m.group(1) or m.group(2))),
    (re.compile(r"^base64 encode[: ]+(.+)$", _I), "base64_encode", lambda m: m.group(1)),
    (re.compile(r"^base64 decode[: ]+(.+)$", _I), "base64_decode", lambda m: m.group(1)),
    (re.compile(r"^(?:count (?:the )?words in|word count(?: of)?)[: ]+(.+)$", _I), "word_count", lambda m: m.group(1)),
    (re.compile(r"^reverse(?: the)? (?:text|words?|string)[: ]+(.+)$|^reverse: (.+)$", _I), "reverse_text", lambda m: (m.group(1) or m.group(2))),
    (re.compile(r"^(?:shout|uppercase)[: ]+(.+)$", _I), "shout", lambda m: m.group(1)),
    (re.compile(r"^morse(?: code)?(?: for| of)?[: ]+(.+)$", _I), "morse_code", lambda m: m.group(1)),
    (re.compile(r"^(?:pretty ?print|format|prettify) json[: ]+(.+)$", _I), "json_pretty", lambda m: m.group(1)),
    (re.compile(r"^is (\d+) (?:a )?prime$|^(?:prime factors of|factor|factorize) (\d+)$", _I), "is_prime", lambda m: m.group(1) or m.group(2)),
    (re.compile(r"^roman numerals? (?:for |of )?(\d+)$|^(\d+) in roman numerals$", _I), "roman_numeral", lambda m: m.group(1) or m.group(2)),
    (re.compile(r"^(?:(?:what(?:'s| is) )?(?:the |a )?tip on|tip(?: for)?) \$?(\d+(?:\.\d+)?)$", _I), "tip", lambda m: m.group(1)),
    (re.compile(r"^(?:check )?disk space$|^how much (?:disk |storage )?space (?:do i have|is (?:left|free))(?: left)?$|^how much storage (?:do i have|is left)$", _I), "disk_space", lambda m: ""),
    (re.compile(r"^how long has (?:my mac|this mac|it) been (?:on|up|running)$|^uptime$", _I), "uptime", lambda m: ""),
    (re.compile(r"^(?:how much )?(?:ram|memory)(?: (?:do i have|is free|is left|am i using))?$|^(?:ram|memory) usage$", _I), "memory_usage", lambda m: ""),
    (re.compile(r"^(?:cpu|processor) (?:load|usage)$|^how busy is (?:my mac|the cpu)$|^load average$", _I), "cpu_load", lambda m: ""),
    (re.compile(r"^(?:what(?:'s| is) )?my (?:local )?ip(?: address)?$", _I), "ip_address", lambda m: ""),
    (re.compile(r"^(?:what|which) wi-?fi(?: network)?(?: am i (?:on|connected to))?$|^wi-?fi name$", _I), "wifi_name", lambda m: ""),
    (re.compile(r"^(?:system|mac) info$|^what mac (?:is this|am i on)$|^about this mac$", _I), "system_info", lambda m: ""),
    (re.compile(r"^copy (.+) to (?:the |my )?clipboard$", _I), "copy_to_clipboard", lambda m: m.group(1)),
    (re.compile(r"^(?:lock|sleep)(?: the| my)? (?:screen|display)$", _I), "sleep_display", lambda m: ""),
    (re.compile(r"^(?:reveal|show)(?: me)? (.+?) in finder$", _I), "reveal_in_finder", lambda m: m.group(1)),
)


def demo():
    """Self-check: the pure tools exactly, the system readers for shape, the Mac-touching ones silent."""
    global HEADLESS
    HEADLESS = True  # a self-check never touches the clipboard, the screen or Finder
    assert calculate("17*23") == "391" and calculate("2^10") == "1024" and calculate("15% of 80") == "12"
    assert calculate("sqrt(144) + 1") == "13" and calculate("1/0") == "You cannot divide by zero."
    assert calculate("__import__('os')").startswith("Cannot") and calculate("9**9999").startswith("Cannot")
    assert convert_units("5 km to miles") == "5 km is 3.1069 mi." and convert_units("212 f to c") == "212 F is 100 C."
    assert convert_units("1 lb to oz") == "1 lb is 16 oz." and convert_units("1 mile to feet") == "1 mi is 5280 ft."
    assert "cannot convert" in convert_units("5 km to kg") and convert_units("nonsense").startswith("Say it")
    assert time_in("tokyo").endswith("in Tokyo.") and "time zone" in time_in("atlantis") and time_in().startswith("It is")
    assert current_date().startswith("It is ") and days_until("christmas") != days_until("halloween")
    assert days_until("2000-01-01").endswith("since January 1, 2000.") and days_until("soon").startswith("Give me")
    assert flip_coin() in ("Heads.", "Tails.") and 1 <= int(roll_dice("d20")) <= 20 and roll_dice("3d6").count("+") == 2
    assert roll_dice("500d6").startswith("Up to") and roll_dice("banana").startswith("Say it")
    assert 5 <= int(random_number("between 5 and 9")) <= 9 and 1 <= int(random_number()) <= 100
    assert len(make_password("20")) == 20 and len(make_password("3")) == 8 and len(make_password("999")) == 64
    assert len(make_uuid()) == 36 and hash_text("hello").startswith("2cf24dba")
    assert base64_encode("hi there") == "aGkgdGhlcmU=" and base64_decode("aGkgdGhlcmU=") == "hi there" and "not valid" in base64_decode("%%%")
    assert word_count("one two three") == "3 words, 13 characters." and word_count("hi") == "1 word, 2 characters."
    assert reverse_text("abc") == "cba" and shout("hey") == "HEY" and morse_code("sos") == "... --- ..."
    assert json_pretty('{"a":[1,2]}').count("\n") == 5 and "not valid" in json_pretty("{")
    assert is_prime("17") == "17 is prime." and is_prime("84") == "84 is not prime: 2 x 2 x 3 x 7." and is_prime("1").startswith("Give me")
    assert roman_numeral("2026") == "MMXXVI" and roman_numeral("4") == "IV" and roman_numeral("4000").startswith("Roman")
    assert tip("45") == "Tip on 45.00: 15% is 6.75, 18% is 8.10, 20% is 9.00." and tip("abc").startswith("Give me")
    assert disk_space().endswith("GB.") and "cores" in cpu_load()
    assert copy_to_clipboard("x") == "Copied." and sleep_display() == "Screen off." and reveal_in_finder("~").startswith("Showing")
    assert reveal_in_finder("~/.ssh").startswith("No file") and reveal_in_finder("/etc/passwd").startswith("No file")
    assert len(TOOLS) == 31 and all(f.__doc__ for f in TOOLS)
    call = lambda name, a: globals()[name](a) if globals()[name].__code__.co_argcount else globals()[name]()
    hit = lambda q: next((call(name, arg(m)) for pat, name, arg in ROUTES if (m := pat.match(q))), None)
    assert hit("calculate 17 * 23") == "391" and hit("convert 5 km to miles") == "5 km is 3.1069 mi."
    assert hit("time in tokyo").endswith("in Tokyo.") and hit("what time is it in london").endswith("in London.")
    assert hit("roll 2d6").count("+") == 1 and hit("flip a coin") in ("Heads.", "Tails.") and hit("hash of hello").startswith("2cf2")
    assert len(hit("make me a password")) == 16 and len(hit("generate a strong password of 24 characters")) == 24
    assert hit("base64 encode hi there") == "aGkgdGhlcmU=" and hit("is 91 prime") == "91 is not prime: 7 x 13."
    assert hit("roman numerals for 1999") == "MCMXCIX" and hit("tip on 45").startswith("Tip on 45.00") and hit("morse sos") == "... --- ..."
    assert hit("what is my ip") is not None and hit("how much disk space do i have").endswith("GB.")
    assert hit("copy hello world to my clipboard") == "Copied." and hit("what is turing") is None and hit("open chrome") is None
    assert hit("hash browns are good") is None and hit("reverse psychology") is None and hit("reverse the text abc") == "cba" and hit("hash: hello").startswith("2cf2")
    print("tools_util ok")


if __name__ == "__main__":
    demo()
