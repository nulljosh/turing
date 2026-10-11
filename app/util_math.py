"""Samantha's pure utility tools: math, unit conversion, chance and text. No app, no network, no side effects.
Split out of tools_util.py, which re-exports every name here, so callers and the ROUTES table are unchanged."""
import ast
import base64
import hashlib
import json
import math
import operator
import random
import re
import secrets
import string
import uuid


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
    text = expression.lower().replace(",", "").strip().rstrip("?").strip()
    # spoken shapes first (dogfood 5.11.2: "square root of 2" could not be worked out): root, squared, cubed, powers, percent
    text = re.sub(r"^(?:what(?:'s| is) )?(?:the )?(?:square root|sqrt) of (.+)$", r"sqrt(\1)", text)
    text = re.sub(r"^(.+?) squared$", r"(\1)**2", text)
    text = re.sub(r"^(.+?) cubed$", r"(\1)**3", text)
    text = re.sub(r"^(.+?) (?:to the power of|to the) (.+?)(?:th|st|nd|rd)?(?: power)?$", r"(\1)**(\2)", text)
    text = re.sub(r"^(.+?) percent of (.+)$", r"\1% of \2", text)
    text = text.replace("x", "*").replace("^", "**")
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


_LENGTH = {"mm": .001, "cm": .01, "m": 1, "km": 1000, "in": .0254, "ft": .3048, "yd": .9144, "mi": 1609.344, "ly": 9460730472580800.0}
_MASS = {"g": .001, "kg": 1, "lb": .45359237, "oz": .028349523125}
_VOLUME = {"ml": .001, "l": 1, "cup": .2365882365, "gal": 3.785411784}
_TIME = {"s": 1, "min": 60, "h": 3600, "day": 86400, "week": 604800}
_UNIT_ALIASES = {
    "millimeter": "mm", "millimeters": "mm", "centimeter": "cm", "centimeters": "cm", "meter": "m", "meters": "m",
    "metre": "m", "metres": "m", "kilometer": "km", "kilometers": "km", "kilometre": "km", "kilometres": "km",
    "inch": "in", "inches": "in", "foot": "ft", "feet": "ft", "yard": "yd", "yards": "yd", "mile": "mi", "miles": "mi", "lightyear": "ly", "lightyears": "ly",
    "gram": "g", "grams": "g", "kilogram": "kg", "kilograms": "kg", "kilo": "kg", "kilos": "kg", "pound": "lb", "pounds": "lb",
    "lbs": "lb", "ounce": "oz", "ounces": "oz", "milliliter": "ml", "milliliters": "ml", "liter": "l", "liters": "l",
    "litre": "l", "litres": "l", "cups": "cup", "gallon": "gal", "gallons": "gal",
    "second": "s", "seconds": "s", "sec": "s", "minute": "min", "minutes": "min", "mins": "min", "hour": "h", "hours": "h",
    "hr": "h", "hrs": "h", "days": "day", "weeks": "week",
    "celsius": "c", "centigrade": "c", "fahrenheit": "f", "kelvin": "k", "°c": "c", "°f": "f"}
_TEMPS = ("c", "f", "k")


def convert_units(text):
    """Convert a quantity between units of length, weight, volume, time or temperature, like "5 km to miles"."""
    t = re.sub(r"\blight[ -]years?\b", "lightyear", text.lower().strip().rstrip("?").strip())  # one word, so "1 light year to km" parses like the rest
    m = re.fullmatch(r"\s*(-?\d+(?:\.\d+)?)\s*([a-z°]+)\s+(?:to|in|into|as)\s+([a-z°]+)\s*", t)
    if m:
        n, a, b = float(m.group(1)), m.group(2), m.group(3)
    else:  # "how many ounces in a pound": one of the second unit, in the first (dogfood 5.11.2)
        m = re.fullmatch(r"(?:how many )?([a-z°]+) (?:are |is )?(?:there )?in (?:a |an |one )?([a-z°]+)", t)
        if not m:
            return 'Say it like "5 km to miles".'
        n, a, b = 1.0, m.group(2), m.group(1)
        m = type("M", (), {"group": staticmethod(lambda i, _a=a, _b=b: {2: _a, 3: _b}[i])})  # the not-convertible sentence below names the units as typed
    a, b = _UNIT_ALIASES.get(a, a), _UNIT_ALIASES.get(b, b)
    if a in _TEMPS and b in _TEMPS:
        c = n if a == "c" else (n - 32) * 5 / 9 if a == "f" else n - 273.15
        out = c if b == "c" else c * 9 / 5 + 32 if b == "f" else c + 273.15
        return f"{_num(n)} {a.upper()} is {_num(round(out, 2))} {b.upper()}."
    for table in (_LENGTH, _MASS, _VOLUME, _TIME):
        if a in table and b in table:
            return f"{_num(n)} {a} is {_num(round(n * table[a] / table[b], 4))} {b}."
    return f"I cannot convert {m.group(2)} to {m.group(3)}."


# ---------- chance ----------

def flip_coin(count=""):
    """Flip a coin, or a few: "3" gives three results."""
    n = int(count) if str(count).strip().isdigit() else {"two": 2, "three": 3, "four": 4, "five": 5}.get(str(count).strip().lower(), 1)
    n = max(1, min(n, 20))
    flips = [random.choice(("Heads", "Tails")) for _ in range(n)]
    return ", ".join(flips) + "."


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
    """Write some text in morse code, or read morse (dots and dashes, a slash between words) back into text."""
    t = text.strip()
    if t and re.fullmatch(r"[.\-/ ]+", t):  # dogfood 5.11.3: "what does ... --- ... mean" had no way back
        back = {v: k for k, v in _MORSE.items()}
        words = [" ".join(back.get(c, "?") for c in w.split()) for w in re.split(r"\s*/\s*|\s{3,}", t) if w.strip()]
        return " ".join("".join(w.split()) for w in words).upper() or "Nothing there to translate."
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


_ROMAN = {"m": 1000, "d": 500, "c": 100, "l": 50, "x": 10, "v": 5, "i": 1}


def roman_numeral(number):
    """Write a number from 1 to 3999 in roman numerals, or read a roman numeral (MCMXCIX) back as a number."""
    s = str(number).strip().lower()
    if s and re.fullmatch(r"[mdclxvi]+", s):  # dogfood 5.11.3: "what is MCMXCIX in numbers"
        total = sum(-_ROMAN[a] if _ROMAN[a] < _ROMAN[b] else _ROMAN[a] for a, b in zip(s, s[1:] + "i"))
        return str(total) if 1 <= total <= 3999 and roman_numeral(str(total)).lower() == s else "That is not a roman numeral I can read."
    if not s.isdigit() or not 1 <= int(s) <= 3999:
        return "Roman numerals run from 1 to 3999."
    n, out = int(number), ""
    for value, sym in ((1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"), (50, "L"),
                       (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")):
        out, n = out + sym * (n // value), n % value
    return out


def tip(amount):
    """Work out 15, 18 and 20 percent tips on a bill, or one rate: "82.50 at 18%"."""
    m = re.fullmatch(r"\$?\s*(-?\d+(?:\.\d+)?)(?:\s+at\s+(\d+(?:\.\d+)?)\s*%?)?", str(amount).strip())
    bill = float(m.group(1)) if m else float("nan")
    if not math.isfinite(bill) or bill < 0:
        return "Give me the bill amount."
    if m.group(2):
        p = float(m.group(2))
        return f"Tip on {bill:.2f} at {p:g}% is {bill * p / 100:.2f}."
    return f"Tip on {bill:.2f}: " + ", ".join(f"{p}% is {bill * p / 100:.2f}" for p in (15, 18, 20)) + "."
