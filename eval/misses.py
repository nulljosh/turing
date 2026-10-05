"""The self-improvement round's first step: every miss in a pick dump, ready to fix.

    ./.venv/bin/python eval/misses.py /Volumes/LaCie/turing-v10/heldout8-picks.jsonl

Lists wrong picks the guard lets through (leaks) and right picks it stops (refusals), each with why the
guard stopped it (evidence cue missing, against cue hit, or the argument). Refused includes sentences that only point ("that file"), where a question is the right move; hands.py counts those apart. Sealed sets (heldout4,
heldout7) print counts per tool only, never their text, so they stay blind.
"""
import collections, json, os, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(REPO, "app")]
os.environ["SAMANTHA_HEADLESS"] = "1"
import tools_registry as R  # noqa: E402

SEALED = ("heldout4", "heldout7")


def _sound(tool, arg, text, ev=True, ag=True):
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
    """(leaks, refusals): lists of (wanted, picked, text, arg, reason)."""
    leaks, refused = [], []
    for line in open(path):
        r = json.loads(line)
        want, got, arg, text = r["wanted_tool"], r["picked_tool"], r["picked_arg_raw"] or "", r["text"]
        if not got:
            continue
        ok = R._sound(got, arg, text)
        if got != want and ok:
            leaks.append((want, got, text, arg, ""))
        elif got == want and not ok:
            refused.append((want, got, text, arg, why(got, arg, text)))
    return leaks, refused


def main():
    for path in sys.argv[1:]:
        sealed = any(s in os.path.basename(path) for s in SEALED)
        leaks, refused = misses(path)
        print(f"== {os.path.basename(path)}: {len(leaks)} leaks, {len(refused)} refused")
        for name, rows in (("leak", leaks), ("refused", refused)):
            if sealed:
                print(f"  {name} by tool:", dict(collections.Counter(r[1] for r in rows)))
                continue
            for want, got, text, arg, reason in rows:
                print(f"  {name:7} {want} -> {got} | {text} | arg: {arg}" + (f" | {reason}" if reason else ""))


if __name__ == "__main__":
    main()
