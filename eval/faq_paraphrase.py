"""Measure how often faq_match() survives a natural rephrasing.

Every eval prompt in prompts.jsonl is worded the way the FAQ itself words
things, so a 29/29 score says nothing about whether a real person's own
phrasing lands. Three separate live bugs in one session (2026-09-14) were
all the same shape: a question the FAQ genuinely answers, phrased normally,
matched the wrong entry or nothing at all. Each got patched by adding
another FAQ entry, which is whack-a-mole, not a fix.

This measures the actual miss rate so the "is lexical matching good enough"
question gets a number instead of a hunch. Each case is a paraphrase a
person would plausibly type, paired with the FAQ header that genuinely
answers it. Run: ./.venv/bin/python eval/faq_paraphrase.py [--verbose]
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ask import faq_match, load_faq

# (what a person types, the FAQ header that actually answers it)
CASES = [
    ("which base model is samantha built on", "What base model does Samantha use?"),
    ("why does it make stuff up sometimes", "Why does Samantha hallucinate, or sometimes make things up?"),
    ("what do you use to train it", "What tool actually runs training?"),
    ("who works on this", "Who maintains this project?"),
    ("is this open source, what license", "What license is this project under?"),
    ("how is it scoring on evals right now", "What's the current eval score?"),
    ("how does the faq matching work", "What is the FAQ-matcher?"),
    ("does it have a full screen terminal ui", "Is there a TUI, not just a plain CLI?"),
    ("how do i start a chat session", "How do I boot into Samantha and chat with her?"),
    ("what is the scratch folder for", "What is scratch/ in this repo?"),
    ("why did arthur fail", "What went wrong with Arthur?"),
    ("does training cost money", "Does Turing use a paid API or cloud service to train?"),
    ("how is lora different from full fine tuning", "What's the difference between LoRA and full fine-tuning?"),
    ("what counts as success here", "What is the honest win condition?"),
    ("where did the training data come from", "What data was Samantha trained on?"),
    ("can samantha look things up outside the project docs", "Can Samantha answer general-knowledge questions, not just project facts?"),
]


def main():
    verbose = "--verbose" in sys.argv
    by_question = dict(load_faq())
    missing = [h for _, h in CASES if h not in by_question]
    if missing:
        # a renamed or deleted FAQ header would otherwise silently score as
        # a miss forever, looking like a matcher regression instead of a
        # stale test case
        print("FAQ headers referenced by this test no longer exist:")
        for h in missing:
            print(f"  {h}")
        return 1

    hits = wrong = nothing = 0
    for asked, expected_header in CASES:
        got = faq_match(asked)
        expected = by_question[expected_header]
        if got == expected:
            hits += 1
            status = "HIT "
        elif got is None:
            nothing += 1
            status = "MISS"
        else:
            wrong += 1
            status = "WRONG"
        if verbose or status != "HIT ":
            print(f"[{status}] {asked}")
            if status == "WRONG":
                actual = next((q for q, a in by_question.items() if a == got), "?")
                print(f"         wanted: {expected_header}")
                print(f"         got:    {actual}")

    total = len(CASES)
    print(f"\n{hits}/{total} paraphrases matched the right entry "
          f"({wrong} matched the wrong entry, {nothing} matched nothing)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
