"""Turns hand-written sentence batches into picker training rows, gen_hands_data.py's exact shape.

Each batch row is {"text", "tool", "arg"} from a writer model that never saw a test set. Rows are kept only when:
- the sentence is not a phrasing any eval already owns (feedback_to_data.reserved_phrases, every eval/heldout*.jsonl),
- it does not say a tool's own name (a writer echoing "run image_info" teaches the name, not the intent),
- a command's argument is one the guard would run as written, or the sentence only points and the argument is empty.
Nothing else is guessed. The counts of what was dropped and why print at the end.

Run: ./.venv/bin/python training/extra_to_data.py BATCH [BATCH...] --out OUT.jsonl
"""
import collections, glob, json, os, re, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(REPO, d) for d in ("app", "eval", "training")]
os.environ.setdefault("SAMANTHA_HEADLESS", "1")
import tools  # noqa: E402
import tools_registry as R  # noqa: E402
from feedback_to_data import reserved_phrases  # noqa: E402

SYSTEM = "You are Samantha's hands. Reply with one JSON tool call. If this is not a command, reply {\"tool\": null, \"arg\": \"\"}."


def norm(text):
    """A sentence reduced to lowercase words, for deduping."""
    return re.sub(r"\W+", " ", text.lower()).strip()


def keep(row, seen):
    """(row to train on or None, why) for one writer row."""
    text, tool = row["text"], row.get("tool")
    key = norm(text)
    if key in seen:
        return None, "repeat or owned by an eval"
    low = text.lower()
    if any(n in low or n.replace("_", " ") in low for n in tools.TOOLS if "_" in n):
        return None, "says a tool name"
    if tool is not None and tool not in tools.TOOLS:
        return None, "unknown tool"
    arg = R.repair(tool, row.get("arg") or "", text) if tool else ""
    if tool and arg and not R._sound(tool, arg, text) and not R.needs_target(tool, arg, text):
        return None, "argument the guard would not run"
    seen.add(key)
    return {"messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": text},
                         {"role": "assistant", "content": json.dumps({"tool": tool, "arg": arg})}]}, "kept"


def demo():
    """Self-check: a tool-name echo and an eval repeat are dropped, a plain command is kept."""
    seen = set()
    assert keep({"text": "run image_info", "tool": "image_info", "arg": ""}, seen)[0] is None
    assert keep({"text": "whats the battery at", "tool": "battery", "arg": ""}, seen)[1] == "kept"
    assert keep({"text": "Whats the battery at?", "tool": "battery", "arg": ""}, seen)[1] == "repeat or owned by an eval"
    print("extra_to_data ok")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        demo()
        sys.exit()
    out_path = sys.argv[sys.argv.index("--out") + 1]
    seen = reserved_phrases()
    for f in glob.glob(os.path.join(REPO, "eval", "heldout*.jsonl")):
        seen |= {norm(json.loads(line)["text"]) for line in open(f)}
    out, why = [], collections.Counter()
    for path in (a for a in sys.argv[1:] if a.endswith(".jsonl") and a != out_path):
        for line in open(path):
            row, reason = keep(json.loads(line), seen)
            why[reason] += 1
            if row:
                out.append(row)
    with open(out_path, "w") as f:
        f.writelines(json.dumps(r) + "\n" for r in out)
    print(f"{len(out)} rows to {out_path}:", dict(why))
