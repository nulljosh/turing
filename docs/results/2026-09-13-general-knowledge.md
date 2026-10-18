# General-knowledge fallback, 2026-09-13

Added `general_knowledge()` to `ask.py`, reusing nimble's exact DDG-instant-answer-then-Wikipedia-summary pattern (`nimble/docs/engine.js`), ported to Python, called server-side directly (nimble needs a CORS proxy in-browser, this doesn't). Goal: let Samantha answer things outside our own docs, "who's the president", "what's the capital of France", not just project facts.

## Real bugs found and fixed along the way

1. **Ordering bug**: initially tried general_knowledge before project retrieval, so questions containing "Turing" (also Alan Turing's real name) got hijacked by the Church-Turing thesis Wikipedia article instead of answering about this project. Fixed with an explicit `PROJECT_KEYWORDS` gate, if the question mentions any of our own known terms (Turing, Samantha, Arthur, ask.py, etc.), general_knowledge never fires, full stop. Tried a retrieval-score threshold first, didn't work, `search()`'s query-biasing prefix inflates every result's score roughly equally regardless of actual relevance, an explicit keyword list is more honest than a fragile threshold tuned to one example.
2. **Query filler noise**: "what is the capital of France" full-text-searched worse on Wikipedia than the stripped "capital of France", question-word filler dilutes relevance ranking. Added `normalize_query()` to strip leading "what is/who is/etc." before hitting either API.

## Real, confirmed limitation, not fixed tonight

Wikipedia's fulltext search picks the wrong disambiguation for ambiguous subjects sometimes: "who wrote Romeo and Juliet" returned Tchaikovsky's orchestral overture of that name, not Shakespeare's play. "Who's the president" returns the office's general Wikipedia summary, not the current officeholder, that needs a source with an explicit up-to-date incumbent field, which neither DDG's instant-answer API nor a plain Wikipedia summary reliably provides for free.

Quick manual spot-check: 2 of 4 test queries correct (capital of France, photosynthesis), 2 wrong (president, Romeo and Juliet author). Genuinely useful for clean factual/definitional queries, unreliable for ambiguous-subject or current-events queries. Ship it as real, working, imperfect, exactly like everything else built tonight, not as a solved problem.
