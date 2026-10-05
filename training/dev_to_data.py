"""Turns retired blind sets into picker training rows, gen_hands_data.py's exact shape: the self-improvement step.

A blind set stops being blind once its misses have been read and fixed against, so its sentences become training
data. Each row's label comes from somewhere trustworthy, never guessed:
- a non-command (tool null) stays null;
- a right pick the guard lets run keeps her own tool and argument (she was right, the guard agreed);
- a miss gets the wanted tool with the set's argument hint, only when the guard would run that hint as written
  (a half argument like "jpg" for "convert this to jpg" teaches the drift this fixes). Anything else is skipped.
Phrasings any eval already owns are dropped (feedback_to_data.reserved_phrases).

Run: ./.venv/bin/python training/dev_to_data.py DUMP [DUMP...] --out hands-data/dev.jsonl
Then append to train.jsonl by hand and retrain (docs/KAGGLE.md). Never pass a sealed set's dump (heldout4, heldout7).
"""
import collections, json, os, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(REPO, d) for d in ("app", "eval", "training")]
os.environ.setdefault("SAMANTHA_HEADLESS", "1")
import tools_registry as R  # noqa: E402
from feedback_to_data import reserved_phrases  # noqa: E402

SYSTEM = "You are Samantha's hands. Reply with one JSON tool call. If this is not a command, reply {\"tool\": null, \"arg\": \"\"}."
SEALED = ("heldout4", "heldout7")


def label(r):
    """(tool, arg, why) for one dump row, or (None, None, why) when it cannot be labelled honestly."""
    want, got, text = r["wanted_tool"], r["picked_tool"], r["text"]
    if want is None:
        return None, "", "null"
    if want == got:
        arg = R.repair(got, r["picked_arg_raw"] or "", text)
        if R._sound(got, arg, text):
            return got, arg, "self"
    hint = R.repair(want, (r.get("wanted_arg") or "").strip(), text)
    if R._sound(want, hint, text):  # only a label the guard itself would run as written: a half argument teaches drift
        return want, hint, "hint"
    return None, None, "skipped"


def rows(paths):
    """Training rows from the dumps, deduped, with a count of where each label came from."""
    seen, out, why = reserved_phrases(), [], collections.Counter()
    for path in paths:
        assert not any(s in os.path.basename(path) for s in SEALED), f"{path} is sealed"
        for line in open(path):
            r = json.loads(line)
            key = r["text"].lower().rstrip(".?!")
            if key in seen:
                why["reserved or repeat"] += 1
                continue
            tool, arg, how = label(r)
            why[how] += 1
            if how == "skipped" or tool == "agent":
                continue
            seen.add(key)
            out.append({"messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": r["text"]},
                                     {"role": "assistant", "content": json.dumps({"tool": tool, "arg": arg})}]})
    return out, why


def demo():
    """Self-check: a null stays null, a miss with an uncopied hint is skipped, a copied hint is used."""
    assert label({"wanted_tool": None, "picked_tool": "battery", "text": "ugh my battery"})[0] is None
    assert label({"wanted_tool": "translate", "picked_tool": "translate", "picked_arg_raw": "", "text": "what's this in japanese",
                  "wanted_arg": "into Japanese"})[2] == "skipped"
    assert label({"wanted_tool": "move_file", "picked_tool": "copy_file", "picked_arg_raw": "", "text": "put a.txt in Pictures",
                  "wanted_arg": "a.txt"})[2] == "skipped"  # half the pair
    assert label({"wanted_tool": "battery", "picked_tool": "disk_space", "picked_arg_raw": "", "text": "how's my battery",
                  "wanted_arg": ""})[:2] == ("battery", "")
    print("dev_to_data ok")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        demo()
        sys.exit()
    out_path = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else os.path.join(REPO, "hands-data", "dev.jsonl")
    paths = [a for a in sys.argv[1:] if a.endswith(".jsonl") and a != out_path]
    data, why = rows(paths)
    with open(out_path, "w") as f:
        f.writelines(json.dumps(d) + "\n" for d in data)
    print(f"{len(data)} rows to {out_path}:", dict(why))
