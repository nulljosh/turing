"""Turns real feedback into picker training rows, in the exact shape gen_hands_data.py writes: a system
prompt, the user's words, and the tool call the picker should have made.

A down with a correction is retargeted at what the correction actually asks for, found by running it through
the real router (tools.plan), never guessed. An up just confirms the tool she already picked was right. Both
are deduped by the query's own words, and never a phrasing eval/actions.py's CASES, eval/basic_questions.py's
CASES or eval/hands.py's own test set (hands-data/test.jsonl) already use: the roadmap's "never copy a test
case into training", the same rule gen_hands_data.py follows.

Not run automatically. Read the output, then retrain by hand.

Run: python3 training/feedback_to_data.py [--in ~/.samantha/feedback.jsonl] [--out hands-data/feedback.jsonl]
"""
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "eval"))
sys.path.insert(0, os.path.join(REPO, "training"))
os.environ.setdefault("SAMANTHA_HEADLESS", "1")


def _flag(name, default=None):
    """One command-line flag's value, or a default."""
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def reserved_phrases():
    """Every phrasing an eval already owns, lowercased and stripped of trailing punctuation, that training must
    never see."""
    from actions import CASES
    out = {c[0].lower().rstrip(".?!") for c in CASES}
    try:
        from basic_questions import CASES as QUESTIONS
        out |= {q[0].lower().rstrip(".?!") for q in QUESTIONS}
    except ImportError:
        pass
    test_path = os.path.join(REPO, "hands-data", "test.jsonl")
    if os.path.exists(test_path):
        for line in open(test_path):
            m = json.loads(line)["messages"]
            out.add(m[1]["content"].lower().rstrip(".?!"))
    return out


def _call(tool, arg):
    """Format a tool pick as the picker's own JSON, gen_hands_data.py's exact shape."""
    return json.dumps({"tool": tool, "arg": arg})


def _row(system, text, call):
    """One training row, gen_hands_data.py's exact JSONL shape."""
    return json.dumps({"messages": [{"role": "system", "content": system}, {"role": "user", "content": text},
                                     {"role": "assistant", "content": call}]})


def read_feedback(path):
    """Every line of feedback.jsonl that actually parses."""
    if not os.path.exists(path):
        return []
    out = []
    for line in open(path):
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def build(entries):
    """Feedback entries into deduped, eval-safe training rows."""
    import tools
    from gen_hands_data import SYSTEM

    reserved = reserved_phrases()
    rows, seen = [], set()
    for e in entries:
        query = (e.get("query") or "").strip()
        key = query.lower().rstrip(".?!")
        if not query or key in seen or key in reserved:
            continue
        rating = e.get("rating")
        if not rating:
            continue
        if rating < 0:
            correction = (e.get("correction") or "").strip()
            if not correction:
                continue  # a down with no correction says what was wrong, never what was right: nothing to learn
            picked = tools.plan(correction)
            if not picked:
                continue  # the correction itself does not name a real command: no honest label to give it
            tool, args = picked[0]
            arg = args[0] if args else ""
        else:
            tool = e.get("tool") or None
            tool = None if tool == "answer" else tool
            args = e.get("args") or []
            arg = args[0] if args else ""
        rows.append(_row(SYSTEM, query, _call(tool, arg)))
        seen.add(key)
    return rows


def main():
    """Read feedback.jsonl, write picker training rows. Never run automatically; a retrain is by hand."""
    src = _flag("--in", os.path.expanduser(os.environ.get("SAMANTHA_FEEDBACK", "~/.samantha/feedback.jsonl")))
    dst = _flag("--out", os.path.join(REPO, "hands-data", "feedback.jsonl"))
    rows = build(read_feedback(src))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, "w") as f:
        f.write("\n".join(rows) + ("\n" if rows else ""))
    print(f"feedback_to_data: {len(rows)} rows -> {dst}")


if __name__ == "__main__":
    main()
