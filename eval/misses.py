"""The self-improvement round's first step: every miss in a pick dump, ready to fix.

    ./.venv/bin/python eval/misses.py /Volumes/LaCie/turing-v10/heldout8-picks.jsonl

Lists wrong picks the guard lets through (leaks) and right picks it stops (refusals), each with why the
guard stopped it (evidence cue missing, against cue hit, or the argument). Rows go through hands.py's own score_picks one at a time, so the kinds match its bar exactly. Sealed sets (heldout4,
heldout7) print counts per tool only, never their text, so they stay blind.
"""
import collections, json, os, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(REPO, "app"), os.path.join(REPO, "eval")]
os.environ["SAMANTHA_HEADLESS"] = "1"
import tools_registry as R  # noqa: E402

SEALED = ("heldout4", "heldout7", "heldout9", "heldout11")


def _sound(tool, arg, text, ev=True, ag=True):
    """The guard's verdict with its evidence or against cues switched off, restored after."""
    e, a = dict(R._EVIDENCE), dict(R._AGAINST)
    try:
        if not ev:
            R._EVIDENCE.clear()
        if not ag:
            R._AGAINST.clear()
        return R._sound(tool, arg, text)
    finally:
        R._EVIDENCE.clear(); R._EVIDENCE.update(e); R._AGAINST.clear(); R._AGAINST.update(a)


def why(tool, arg, text):
    """Which part of the guard stopped this pick."""
    if _sound(tool, arg, text, ev=False):
        return "evidence"
    if _sound(tool, arg, text, ag=False):
        return "against"
    return "argument"


def misses(path):
    """Each miss as hands.py scores it, row by row through its own score_picks (so the two never disagree):
    (kind, wanted, picked, text, arg, reason, sure). kind is leak, refused, refused-points (a sentence that only
    points, where a question would be right) or asked-named (asked although the sentence names its target)."""
    import hands
    out = []
    for line in open(path):
        r = json.loads(line)
        pick = (r["group"], r["text"], r["wanted_tool"], r["wanted_arg"], r["exact"], r["picked_tool"], r["picked_arg_raw"] or "", r.get("sure"))
        _, _, fired, blocked, _, bar = hands.score_picks([pick])
        got, text = r["picked_tool"], r["text"]
        arg = R.repair(got, pick[6], text) if got else ""
        kind = ("leak" if fired else "refused-points" if bar["points_refused"] else "refused" if blocked
                else "asked-named" if bar["named_asked"] else None)
        if kind:
            out.append((kind, r["wanted_tool"], got, text, arg, why(got, arg, text) if kind != "leak" else "", r.get("sure")))
    return out


def main():
    """Print the misses for each dump named on the command line."""
    for path in sys.argv[1:]:
        sealed = any(x in os.path.basename(path) for x in SEALED)
        rows = misses(path)
        print(f"== {os.path.basename(path)}:", dict(collections.Counter(r[0] for r in rows)))
        if sealed:  # counts only: by kind and tool, by kind and reason
            print("  ", dict(collections.Counter(f"{r[0]} {r[2]}" for r in rows)))
            print("  ", dict(collections.Counter(f"{r[0]} {r[5]}" for r in rows if r[5])))
            continue
        for kind, want, got, text, arg, reason, sure in rows:
            print(f"  {kind:14} {want} -> {got} | {text} | arg: {arg} | {reason} sure={sure}")


if __name__ == "__main__":
    main()
