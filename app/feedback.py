"""Her feedback: a spoken verdict on the last turn, logged to a file only she reads, so a retrain can learn
from real use, not just from eval scores.

Not a tool a model picks. The rating phrases below are caught by harness.Session before any routing happens,
so "good" and "wrong" never fire a tool, only this module (chat.py's own chat()/tui() loops hand it their
general-knowledge turns too, through Session.record, since those never go through the harness at all).
feedback_summary is the one part of this that is a real route ("how am I rating you"), private like recall,
spliced into tools.TOOLS / tools._ROUTES / tools.NOT_FOR_MODELS from here so tools.py's own line count barely
moves (CLAUDE.md, File size; eval/laws.py law 8).
"""
import json
import os
import re
import time

import tools

_UP = re.compile(r"^(?:good|thanks,? that'?s right|👍|\+1)[.!]*$", re.I)
_DOWN = re.compile(r"^(?:bad|wrong|that'?s not what i meant|👎|-1)[.!]*$", re.I)
_CORRECTION = re.compile(r"^wrong,?\s*i meant\s+(.+)$", re.I)
_SUMMARY = re.compile(r"^(?:how am i rating you|show my feedback)\??$", re.I)
_TOOL_CALL = re.compile(r"\[(\w+)\((.*)\)\]")


def _path():
    """Where her feedback lives: ~/.samantha/feedback.jsonl, or SAMANTHA_FEEDBACK (the tests use it)."""
    return os.path.expanduser(os.environ.get("SAMANTHA_FEEDBACK", "~/.samantha/feedback.jsonl"))


def match(text):
    """A rating verdict in a raw message: (rating, correction), rating +1 or -1 and correction the text after
    "I meant" or None, or plain None when the message is not a rating at all. Tight on purpose, matched whole:
    "good morning" and "what's wrong with my wifi" are sentences, not verdicts, and never match. "thanks for
    nothing" is sarcasm outside the fixed phrase list on purpose too, so it stays unrated rather than guessed at."""
    t = text.strip()
    m = _CORRECTION.match(t)
    if m:
        return (-1, m.group(1).strip())
    if _UP.match(t):
        return (1, None)
    if _DOWN.match(t):
        return (-1, None)
    return None


def is_summary(text):
    """Whether a message is asking to see her own rating record. Read only."""
    return bool(_SUMMARY.match(text.strip()))


def parse_calls(calls):
    """The tool a turn's log lines named, and its args, from harness.Session's own "[name(args)]" call log; or
    ("answer", ()) when nothing was called, a question answered straight from her head."""
    for call in calls or ():
        m = _TOOL_CALL.search(call)
        if m:
            args = tuple(a.strip() for a in m.group(2).split(",")) if m.group(2).strip() else ()
            return m.group(1), args
    return "answer", ()


def record(query, tool, args, reply, rating, correction=None):
    """Log one rating for the last turn: timestamp, the query, the tool she picked (or "answer"), its args, her
    reply (capped 500 characters), the rating, and the correction text if given. Local only, nothing leaves the
    Mac. Returns her short reply."""
    path = _path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    entry = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "query": query, "tool": tool, "args": list(args or ()),
              "reply": (reply or "")[:500], "rating": rating, "correction": correction}
    with open(path, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return "Noted, I'll learn from that." if rating < 0 else "Noted."


def _entries():
    """Every logged rating, oldest first, skipping any line that will not parse."""
    try:
        with open(_path()) as f:
            lines = f.read().splitlines()
    except OSError:
        return []
    out = []
    for line in lines:
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def feedback_summary():
    """How she is rated so far: an up/down count and the last five downs with their corrections. Read only,
    private, so only asked for by name, never a model's own pick."""
    entries = _entries()
    if not entries:
        return "No feedback yet."
    up = sum(1 for e in entries if e.get("rating", 0) > 0)
    down = sum(1 for e in entries if e.get("rating", 0) < 0)
    lines = [f"{up} up, {down} down."]
    for e in reversed([e for e in entries if e.get("rating", 0) < 0][-5:]):
        note = f" (meant: {e['correction']})" if e.get("correction") else ""
        lines.append(f"- {e.get('query', '')}{note}")
    return "\n".join(lines)


# Spliced into tools.py from here rather than edited there, so a new private tool never costs tools.py more
# than the one import line at the bottom of the file that pulls this module in.
tools.TOOLS["feedback_summary"] = feedback_summary
tools.feedback_summary = feedback_summary  # also a real attribute on the module, like every other TOOLS entry (eval/actions.py mocks by name)
tools.NOT_FOR_MODELS = tools.NOT_FOR_MODELS | {"feedback_summary"}
tools._ROUTES = tools._ROUTES + ((_SUMMARY, lambda m: feedback_summary()),)


def demo():
    """Self-check: the matcher's positives and negatives, and the summary against a scratch file."""
    assert match("good") == (1, None) and match("Good!") == (1, None) and match("+1") == (1, None)
    assert match("thanks that's right") == (1, None) and match("thanks, that's right.") == (1, None)
    assert match("bad") == (-1, None) and match("wrong") == (-1, None) and match("-1") == (-1, None)
    assert match("that's not what I meant") == (-1, None)
    assert match("wrong, I meant open safari") == (-1, "open safari")
    assert match("wrong i meant the weather") == (-1, "the weather")
    for negative in ("good morning", "what's wrong with my wifi", "thanks for nothing", "good morning joshua",
                     "that's not what I ordered", "-100", "goodbye"):
        assert match(negative) is None, negative
    assert is_summary("how am I rating you") and is_summary("show my feedback?")
    assert not is_summary("how am I doing")
    assert parse_calls(["  [open_url(github.com)]"]) == ("open_url", ("github.com",))
    assert parse_calls([]) == ("answer", ())
    import tempfile
    old = os.environ.get("SAMANTHA_FEEDBACK")
    os.environ["SAMANTHA_FEEDBACK"] = os.path.join(tempfile.mkdtemp(), "feedback.jsonl")
    try:
        assert feedback_summary() == "No feedback yet."
        assert record("what is turing", "answer", (), "a project", 1) == "Noted."
        assert record("open chrome", "open_app", ("safari",), "Opened.", -1, "open safari") == "Noted, I'll learn from that."
        s = feedback_summary()
        assert "1 up, 1 down." in s and "open chrome" in s and "meant: open safari" in s
    finally:
        if old is None:
            os.environ.pop("SAMANTHA_FEEDBACK", None)
        else:
            os.environ["SAMANTHA_FEEDBACK"] = old
    print("feedback ok")


if __name__ == "__main__":
    demo()
