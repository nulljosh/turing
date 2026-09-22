"""Answers computed on this machine with no network: arithmetic, the clock, unit conversion, and small talk.
Split out of ask.py, which re-exports every name here."""
import difflib, hashlib, html, json, math, os, re, subprocess, sys, time, urllib.parse, urllib.request

_QUESTION_PREFIX = re.compile(
    r"^(what'?s?|who'?s?|when'?s?|where'?s?|why|how)\s+(is|are|was|were|does|do|did)\s+(the\s+)?",
    re.I,
)


_ARITH_WORDS = (
    (r"\b(?:times|multiplied by)\b", "*"),
    (r"\bplus\b", "+"),
    (r"\bminus\b", "-"),
    (r"\b(?:divided by|over)\b", "/"),
    (r"\bx\b", "*"),
)
_ARITH_OK = re.compile(r"^[\d\s+\-*/().]+$")


def arithmetic(query):
    """Answer plain arithmetic locally and exactly.

    "what is 2+2" used to be sent to the web like any other question, and
    came back as a Danganronpa game; "what is 10 times 7" came back as The
    New York Times (the word "times" matched a newspaper). Both are
    confident wrong answers to questions with one exact answer, which no
    search engine should ever have been asked in the first place.

    Evaluated by walking a parsed AST with an explicit node whitelist, not
    eval(), so a crafted "question" can't execute anything. Anything that
    isn't purely numbers and operators returns None and falls through.
    """
    import ast

    expr = _QUESTION_PREFIX.sub("", query.strip().rstrip("?")).strip()
    expr = re.sub(r"^(?:what\s+(?:is|are)|calculate|compute)\s+", "", expr, flags=re.I).strip()
    for pattern, symbol in _ARITH_WORDS:
        expr = re.sub(pattern, symbol, expr, flags=re.I)
    expr = expr.strip()
    if not expr or not _ARITH_OK.match(expr) or not any(c.isdigit() for c in expr):
        return None
    if not any(op in expr for op in "+-*/"):
        return None  # a bare number isn't a question

    allowed = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant,
               ast.Add, ast.Sub, ast.Mult, ast.Div, ast.USub, ast.UAdd)
    try:
        tree = ast.parse(expr, mode="eval")
        for node in ast.walk(tree):
            if not isinstance(node, allowed):
                return None
            if isinstance(node, ast.Constant) and not isinstance(node.value, (int, float)):
                return None
        value = eval(compile(tree, "<arithmetic>", "eval"), {"__builtins__": {}}, {})
    except ZeroDivisionError:
        return f"{expr} has no answer: you can't divide by zero."
    except Exception:
        return None
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return f"{expr} = {value}"


_CLOCK_PATTERNS = (
    (re.compile(r"\bwhat(?:'s| is)?\s+(?:the\s+)?time\b", re.I), "%-I:%M %p"),
    # These must be present-tense only. The first version matched a bare
    # "what year", so "what year did world war 2 end" confidently answered
    # **2026**, the current year, to a historical question. Require an
    # explicit "is it"/"is this"/"are we in" so a question about some other
    # year falls through to a real lookup.
    (re.compile(r"\bwhat(?:'s| is)?\s+(?:the\s+)?year\s+(?:is\s+it|is\s+this|are\s+we\s+in)\b|\bwhat\s+year\s+is\s+it\b", re.I), "%Y"),
    (re.compile(r"\bwhat\s+month\s+is\s+it\b", re.I), "%B %Y"),
    (re.compile(r"\bwhat\s+day(?:\s+of\s+the\s+week)?\s+is\s+it\b", re.I), "%A"),
    (re.compile(r"\bwhat(?:'s| is)?\s+(?:today'?s?\s+)?(?:the\s+)?date\b", re.I), "%A, %B %-d, %Y"),
    (re.compile(r"\bwhat\s+is\s+today\b", re.I), "%A, %B %-d, %Y"),
)


# alias -> (dimension, factor to the dimension's base unit, display name)
_UNITS = {}
for _names, _dim, _factor, _label in [
    (("mm", "millimeter", "millimeters", "millimetre", "millimetres"), "length", 0.001, "mm"),
    (("cm", "centimeter", "centimeters", "centimetre", "centimetres"), "length", 0.01, "cm"),
    (("m", "meter", "meters", "metre", "metres"), "length", 1.0, "m"),
    (("km", "kilometer", "kilometers", "kilometre", "kilometres"), "length", 1000.0, "km"),
    (("in", "inch", "inches"), "length", 0.0254, "in"),
    (("ft", "foot", "feet"), "length", 0.3048, "ft"),
    (("yd", "yard", "yards"), "length", 0.9144, "yd"),
    (("mi", "mile", "miles"), "length", 1609.344, "mi"),
    (("mg", "milligram", "milligrams"), "mass", 0.001, "mg"),
    (("g", "gram", "grams"), "mass", 1.0, "g"),
    (("kg", "kilogram", "kilograms"), "mass", 1000.0, "kg"),
    (("oz", "ounce", "ounces"), "mass", 28.349523125, "oz"),
    (("lb", "lbs", "pound", "pounds"), "mass", 453.59237, "lb"),
    (("ml", "milliliter", "milliliters", "millilitre", "millilitres"), "volume", 0.001, "ml"),
    (("l", "liter", "liters", "litre", "litres"), "volume", 1.0, "L"),
    (("cup", "cups"), "volume", 0.2365882365, "cups"),
    (("pint", "pints"), "volume", 0.473176473, "pints"),
    (("gal", "gallon", "gallons"), "volume", 3.785411784, "gal"),
]:
    for _n in _names:
        _UNITS[_n] = (_dim, _factor, _label)

_TEMPS = {
    "c": "c", "celsius": "c", "centigrade": "c",
    "f": "f", "fahrenheit": "f",
    "k": "k", "kelvin": "k",
}

_CONVERT_PATTERNS = (
    # "convert 100 fahrenheit to celsius", "100 f in c", "what is 5 miles in km"
    re.compile(r"(-?\d+(?:\.\d+)?)\s*([a-z°]+)\s*(?:to|in|into|as)\s+([a-z°]+)", re.I),
    # "how many kilometers is 5 miles", "how many km in 5 miles"
    re.compile(r"how\s+many\s+([a-z°]+)\s+(?:is|are|in)\s+(-?\d+(?:\.\d+)?)\s*([a-z°]+)", re.I),
)


def _to_celsius(value, unit):
    """Any of celsius, fahrenheit or kelvin to celsius."""
    return {"c": value, "f": (value - 32) * 5 / 9, "k": value - 273.15}[unit]


def _from_celsius(value, unit):
    """Celsius to celsius, fahrenheit or kelvin."""
    return {"c": value, "f": value * 9 / 5 + 32, "k": value + 273.15}[unit]


def _tidy(value):
    """Round to four places and drop a trailing .0."""
    rounded = round(value, 4)
    return int(rounded) if rounded == int(rounded) else rounded


def convert(query):
    """Unit conversions, answered locally and exactly.

    Same category as arithmetic and clock: one correct answer that a search
    engine can only get wrong. Confirmed live, "how many kilometers is 5
    miles" returned an article about **available seat miles**, an airline
    capacity metric, and "convert 100 fahrenheit to celsius" was declined
    outright. Deliberately a small table of units people actually ask
    about rather than a units library, and it returns None on anything it
    doesn't recognise so the normal lookup path still runs.
    """
    text = query.strip().rstrip("?").replace("°", " ")
    for index, pattern in enumerate(_CONVERT_PATTERNS):
        match = pattern.search(text)
        if not match:
            continue
        if index == 0:
            amount, src, dst = match.group(1), match.group(2), match.group(3)
        else:
            amount, src, dst = match.group(2), match.group(3), match.group(1)
        amount = float(amount)
        src, dst = src.lower(), dst.lower()

        if src in _TEMPS and dst in _TEMPS:
            result = _from_celsius(_to_celsius(amount, _TEMPS[src]), _TEMPS[dst])
            return f"{_tidy(amount)} {src} = {_tidy(result)} {dst}"

        if src in _UNITS and dst in _UNITS:
            src_dim, src_factor, src_label = _UNITS[src]
            dst_dim, dst_factor, dst_label = _UNITS[dst]
            # refuse to convert across dimensions rather than printing a
            # confident nonsense number for "how many kg is 5 miles"
            if src_dim != dst_dim:
                return None
            return f"{_tidy(amount)} {src_label} = {_tidy(amount * src_factor / dst_factor)} {dst_label}"
    return None


def clock(query):
    """Answer date and time questions from the system clock.

    The machine knows what day it is; no search engine should be asked.
    Confirmed live: "what year is it" returned Wikipedia's **Flat Earth**
    article, because a question about the year has no searchable subject and
    the fulltext match landed on "Earth". Same category as arithmetic, one
    exact answer available locally, so it never reaches the network.
    """
    import datetime

    for pattern, fmt in _CLOCK_PATTERNS:
        if pattern.search(query):
            return datetime.datetime.now().strftime(fmt)
    return None


_SMALLTALK = (
    (re.compile(r"^(?:hi|hello|hey|yo|hiya|good (?:morning|evening|afternoon))(?: there| samantha)?[!.?]*$", re.I),
     lambda: "Hi. Ask me something, or tell me to do something on this Mac."),
    (re.compile(r"^(?:how are you|how's it going|how are things)(?: doing| today)?[!.?]*$", re.I),
     lambda: "Running fine, and ready. What do you need?"),
    (re.compile(r"^(?:thanks|thank you|thx|cheers|ty)(?: so much| samantha)?[!.?]*$", re.I), lambda: "Any time."),
    (re.compile(r"^(?:what can you do|what do you do|help|what are your (?:abilities|skills)|what can i ask you)[!.?]*$", re.I),
     lambda: abilities()),
    (re.compile(r"^(?:list|show me|what are|tell me about|which are) (?:all )?(?:of )?your tools[!.?]*$|^tools[!.?]*$", re.I), lambda: tool_list()),
)


def abilities():
    """What she can do, in one paragraph, counted from the live tool table so it never drifts."""
    import tools
    return (f"I answer questions: this project from its own docs, the rest from Wikipedia and the web, and I say so "
            f"instead of guessing. I also do things on this Mac with {len(tools.TOOLS)} tools: open apps and sites, search the web, "
            "Chrome tabs, notes, reminders, timers, music and volume, edit and paint pictures in Pixelmator, logos, math, time, "
            "dice, text, your documents and your screen, and for a hard question you can say ask claude. Anything that writes or sends asks you first. "
            'Try "google best pizza near me", "open pixelmator" or "make this photo black and white". Say "list your tools" for all of them.')


def tool_list():
    """Every tool she has, by name, straight from the tool table."""
    import tools
    return f"{len(tools.TOOLS)} tools: " + ", ".join(n.replace("_", " ") for n in sorted(tools.TOOLS)) + "."


def small_talk(query):
    """A greeting, a thanks, or "what can you do": a fixed, honest reply, no model and no lookup.
    Anchored to the whole message, so "hey calculate 8 + 8" and "help me find a file" still reach the tools."""
    q = query.strip()
    return next((reply() for pattern, reply in _SMALLTALK if pattern.match(q)), None)
