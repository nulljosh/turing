# Eval: FAQ-matcher (structural fix), 2026-09-13

Model: Samantha via `ask.py`, now with `faq_match()` checked first, before retrieval or generation. Parses `FAQ.md`'s `## Question` / answer pairs, fuzzy-matches the incoming question against them (`difflib.SequenceMatcher`, threshold 0.55), returns the real FAQ answer verbatim when confident, falls through to retrieval+generation only when nothing matches well enough.

**Score: ~22-23/28 correct or largely correct.** Up from ~10/28 in the previous round (`rag2`/`rag3`). This is the real jump of the night.

## Why this worked where hand-written `FIXED_FACTS` didn't scale

`FIXED_FACTS` fixed 6 individual questions, one line of code each, whack-a-mole. `faq_match()` fixes everything `FAQ.md` already covers, in one pass, because `FAQ.md` was already written as Q&A pairs, no new authoring needed beyond what already existed for humans to read. It also answers with the *complete, correct, real* text instead of a one-line extracted fragment, better than `FIXED_FACTS` for the overlapping questions (blocked/paused, who maintains, license, LoRA definition, training tool) too.

## What's still wrong

Task-style prompts (write a commit message, write a journal entry) correctly don't FAQ-match, they're not factual questions, that's expected and correct behavior, still hit the generation-quality ceiling. A couple of close-paraphrase questions ("Why doesn't Turing pretrain from scratch at full scale") didn't clear the 0.55 threshold despite a real FAQ entry existing for that exact topic, worth a lower threshold or synonym expansion as a follow-up, not chased tonight.

## Real conclusion

This is the honest "basic working LLM" result for tonight: any question whose answer already lives in `FAQ.md` gets that real answer, verbatim, sourced, essentially instantly (often skipping the network call to `brain` entirely). Anything else still depends on retrieval + a 0.5B model's generation quality, unchanged from before. The lesson: for a small model like this, a well-maintained FAQ beats fancier retrieval or training tricks for the questions people actually ask most.
