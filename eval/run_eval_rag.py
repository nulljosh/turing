"""Run the eval prompts through ask.py's retrieval-augmented path instead
of raw generation, for a real comparison against the memorization-only runs.
"""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ask import ask

D = os.path.dirname(__file__)
PROMPTS = f"{D}/prompts.jsonl"


def main():
    prompts = [json.loads(l) for l in open(PROMPTS)]
    for p in prompts:
        try:
            answer, sources = ask(p["prompt"])
        except Exception as e:
            answer, sources = f"[error: {e}]", []
        print(f"PROMPT: {p['prompt']}")
        print(f"EXPECT: {p['expects']}")
        print(f"GOT:    {answer}")
        print(f"SOURCES: {sources}")
        print("-" * 60)


if __name__ == "__main__":
    main()
