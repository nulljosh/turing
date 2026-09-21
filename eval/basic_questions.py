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
    # 2026-09-20 QA sweep: people, places, things. Asked the way a person
    # types them, lowercase, no punctuation, several shapes per category.
    # people
    ("who is marie curie", ["radioactiv", "physicist", "chemist"]),
    ("who was isaac newton", ["physicist", "mathematician", "gravity"]),
    ("who is elon musk", ["tesla", "spacex"]),
    ("who is barack obama", ["president"]),
    ("who was cleopatra", ["egypt"]),
    ("who is lebron james", ["basketball"]),
    ("who was alan turing", ["mathematician", "computer"]),
    ("who is serena williams", ["tennis"]),
    ("who was nikola tesla", ["inventor", "engineer", "electric"]),
    ("who is oprah winfrey", ["talk show", "television", "host"]),
    ("who wrote 1984", ["orwell"]),
    ("who discovered penicillin", ["fleming"]),
    ("who invented the telephone", ["bell"]),
    ("who was the first person on the moon", ["armstrong"]),
    ("tell me about ada lovelace", ["mathematician", "babbage", "analytical engine"]),
    # places
    ("what is the capital of canada", ["ottawa"]),
    ("what is the capital of australia", ["canberra"]),
    ("what is the capital of brazil", ["bras"]),
    ("what is the capital of british columbia", ["victoria"]),
    ("where is the eiffel tower", ["paris"]),
    ("where is mount everest", ["nepal", "himalaya", "tibet"]),
    ("what is the longest river in the world", ["nile", "amazon"]),
    ("what is the largest country in the world", ["russia"]),
    ("what is the largest ocean", ["pacific"]),
    ("what country is vancouver in", ["canada"]),
    ("where is the great barrier reef", ["australia"]),
    ("what is the tallest mountain in the world", ["everest"]),
    ("tell me about tokyo", ["japan"]),
    ("what is the sahara", ["desert"]),
    ("where is machu picchu", ["peru"]),
    # things
    ("what is a black hole", ["gravity", "spacetime"]),
    ("what is photosynthesis", ["light", "plants"]),
    ("what is dna", ["genetic", "nucleic", "deoxyribonucleic"]),
    ("what is the speed of light", ["299", "300,000", "186"]),
    ("what is bitcoin", ["cryptocurrency", "currency"]),
    ("what is a transformer in machine learning", ["attention", "neural", "architecture"]),
    ("what is the internet", ["network"]),
    ("what is a volcano", ["magma", "lava", "erupt"]),
    ("what is the pythagorean theorem", ["triangle", "hypotenuse"]),
    ("what is an electron", ["particle", "negative", "charge"]),
    ("what is the great wall of china", ["wall", "fortification"]),
    ("what is jazz", ["music"]),
    ("what is a guitar", ["string", "instrument"]),
    ("how many planets are in the solar system", ["8", "eight"]),
    ("what is the freezing point of water in fahrenheit", ["32"]),
]

DECLINED_MARKERS = ("couldn't find anything", "couldn't reach", "don't have that pinned down", "not going to guess")


def main():
    """Test general knowledge questions and track correct, confidently wrong, and declined answers."""
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
