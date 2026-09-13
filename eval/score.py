"""Real QA: automated pass/fail scoring instead of eyeballing 28 answers by
hand. Each prompt in prompts.jsonl carries objective criteria (required
substrings, banned substrings, style limits), this checks every answer
against them and prints a number, not a vibe.

Usage: ./.venv/bin/python eval/score.py [--verbose]
Exit code is nonzero if any prompt fails, so it can gate a commit/CI step.
"""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ask import ask

D = os.path.dirname(__file__)
PROMPTS = f"{D}/prompts.jsonl"


def check(answer, spec):
    lower = answer.lower()
    reasons = []

    for req in spec.get("must_contain", []):
        if req.lower() not in lower:
            reasons.append(f"missing required: {req!r}")

    any_list = spec.get("must_contain_any")
    if any_list and not any(a.lower() in lower for a in any_list):
        reasons.append(f"missing all of: {any_list}")

    for bad in spec.get("must_not_contain", []):
        if bad.lower() in lower:
            reasons.append(f"contains banned: {bad!r}")

    if spec.get("style_only"):
        if "—" in answer:
            reasons.append("contains an em dash")
        if not answer.strip():
            reasons.append("empty answer")

    max_words = spec.get("max_words")
    if max_words and len(answer.split()) > max_words:
        reasons.append(f"too long: {len(answer.split())} words > {max_words}")

    return reasons


def main():
    verbose = "--verbose" in sys.argv
    prompts = [json.loads(l) for l in open(PROMPTS) if l.strip()]
    passed, failed = 0, []

    for spec in prompts:
        answer, sources = ask(spec["prompt"])
        reasons = check(answer, spec)
        if reasons:
            failed.append((spec["prompt"], answer, reasons))
        else:
            passed += 1
        if verbose:
            status = "PASS" if not reasons else "FAIL"
            print(f"[{status}] {spec['prompt']}")
            if reasons:
                print(f"       {answer[:150]}")
                for r in reasons:
                    print(f"       - {r}")

    total = len(prompts)
    print(f"\n{passed}/{total} passed ({passed*100//total}%)")
    if failed and not verbose:
        print("\nFailed:")
        for prompt, answer, reasons in failed:
            print(f"  - {prompt}")
            print(f"    {answer[:120]}")
            print(f"    {'; '.join(reasons)}")

    sys.exit(0 if not failed else 1)


if __name__ == "__main__":
    main()
