"""Can Samantha answer a basic question a child could answer?

Everything measured before this file was about the project's own docs
(prompts.jsonl) or FAQ phrasing robustness (faq_paraphrase.py). Neither
touches the case a person actually tries first: ask it something simple and
general. Live-tested 2026-09-14, it scored 1/5, and the four failures were
not the 0.5B model being weak, they were the general-knowledge chain
returning confident nonsense: "what is 2+2" got a Danganronpa game, "how
many days are in a week" got Bodybuilding.com, "what color is the sky" got
a country album literally titled that.

Each case lists accepted substrings, matched case-insensitively, so a
correct answer phrased differently still counts. A question the chain
honestly declines is scored as a miss, but it is a *safe* miss, and the
report separates the two because they need opposite fixes.

Run: ./.venv/bin/python eval/basic_questions.py [--verbose] [--min N]
"""
import os, sys, time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ask import ask

# (question, any one of these substrings counts as correct)
CASES = [
    ("what is 2+2", ["4", "four"]),
    ("what is 10 times 7", ["70", "seventy"]),
    ("what is the capital of japan", ["tokyo"]),
    ("what is the capital of france", ["paris"]),
    ("how many days are in a week", ["7", "seven"]),
    ("how many continents are there", ["7", "seven"]),
    ("who wrote romeo and juliet", ["shakespeare"]),
    ("who painted the mona lisa", ["leonardo", "da vinci"]),
    ("what color is the sky", ["blue"]),
    ("how many legs does a spider have", ["8", "eight"]),
    ("what is the largest planet in the solar system", ["jupiter"]),
    ("what is the boiling point of water in celsius", ["100"]),
    ("what year did world war 2 end", ["1945"]),
    ("what is the chemical symbol for gold", ["au"]),
    ("how many sides does a triangle have", ["3", "three"]),
    # regression: this hit a Wikipedia disambiguation page ("Bees Make Honey
    # may refer to:"), which is a list of names, never an answer
    ("what do bees make", ["honey"]),
    # "who is <person>" is the single most likely thing anyone types first
    ("who is steve jobs", ["apple"]),
    ("who is albert einstein", ["physicist", "relativity"]),
    ("who is taylor swift", ["singer", "songwriter", "musician"]),
    ("who was abraham lincoln", ["president"]),
]

DECLINED_MARKERS = ("couldn't reach", "don't have that pinned down", "not going to guess")


def main():
    verbose = "--verbose" in sys.argv
    minimum = None
    for i, arg in enumerate(sys.argv):
        if arg == "--min" and i + 1 < len(sys.argv):
            minimum = int(sys.argv[i + 1])

    right = declined = wrong = 0
    for i, (question, accepted) in enumerate(CASES):
        # Pacing exists because Wikidata and Wikipedia both rate-limit, and
        # a self-throttled run is not a measurement: identical code scored
        # 16/19 and then 9/20 purely on 429s. ask.py now caches successful
        # lookups to disk for a day, so a rerun makes no requests at all and
        # only genuinely new questions ever reach the network. That made the
        # 3s pace mostly dead time, so it is 1s now, enough to stay polite
        # on a cold first run.
        if i:
            time.sleep(1.0)
        answer = (ask(question)[0] or "").strip()
        low = answer.lower()
        if any(a.lower() in low for a in accepted):
            right += 1
            status = "RIGHT"
        elif any(m in low for m in DECLINED_MARKERS) or not answer:
            declined += 1
            status = "DECLINED"
        else:
            wrong += 1
            status = "WRONG"
        if verbose or status != "RIGHT":
            print(f"[{status}] {question}")
            print(f"          {answer[:160]}")

    total = len(CASES)
    print(f"\n{right}/{total} right, {wrong} confidently wrong, {declined} honestly declined")
    if minimum is not None and right < minimum:
        print(f"REGRESSION: {right} right is below the required minimum {minimum}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
