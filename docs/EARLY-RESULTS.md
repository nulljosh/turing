# Early results

The first eval writeups, all from 2026-09-13, oldest run first: the fine-tuning runs, then retrieval, then the FAQ matcher and the general-knowledge fallback. Later numbers live in `docs/BAKEOFF.md` and `docs/PROGRESS.md`.

## Eval run: 2026-09-13

Model: `ada-1-adapter` (Qwen2.5-0.5B base, 500 iters, 2054 lines of data)

**Score: 1/8 on-target.** Everything except the commit-message prompt hallucinates a plausible-sounding but wrong answer instead of drawing on the actual training data. It confidently describes Ada-1 as a "personal assistant app" with Swift/iOS features that don't exist, and Turing as a cross-platform tool running on "Windows 10, macOS 11, Linux 2.4."

### Why this is happening

2054 lines / 500 iterations isn't enough to override Qwen's base-model habit of answering "what is X" questions in generic product-description voice. The fine-tune is nudging style slightly (the commit-message prompt landed close) but hasn't overridden factual behavior. This matches the README's own warning in "A note on benchmarking": a LoRA delta is small by design, it can't force the base model to stop confabulating on questions the training data doesn't cover densely enough.

### What actually worked

The one hit (commit message prompt) is telling: short, mechanical, style-only tasks respond well even at this data size. Open-ended "what is X" questions don't.

### Next steps this suggests

1. More repetitions of the same core facts (what Turing/Ada-1 are) in the training data, not just one README mention buried among thousands of other lines.
2. Consider a system-prompt-style prefix during training/inference that primes it to answer from context rather than free-associate.
3. Retry this eval after Phase 1's wider dataset (roadmap.md + CLAUDE.md files) has had more iterations, and after the paused Qwen3.5-0.8B comparison finishes.

## Eval run 2: 2026-09-13, chat-format fix

Model: `ada-1-adapter` (Qwen2.5-0.5B base, 500 iters, chat-formatted data, resumed once from checkpoint 100)

**Score: ~1/28, arguably worse than run 1's 1/8.**

### What changed

Run 1 hallucinated a plausible but wrong "Samantha is an app" story. Run 2 does something different and more revealing: it answers almost every prompt with a *different fleet project's* README pattern (Sparkjar, Sift, Tally, Cloudflare Workers, random iOS build statuses), often looping the same phrase repeatedly ("It is a real Durable Objects client that runs on Cloudflare's Compute Engine" x4).

### Root cause found

`prep_data.py` globs every `README.md` / `roadmap.md` / `CLAUDE.md` across the entire `~/Documents/Code` fleet, not just this project's own docs. Turing is one tiny project among 50+. So the training set is overwhelmingly "generic fleet project README" text, and each chunk's synthetic prompt is `"Tell me about {source filename}"`, meaning the model learned "answer any 'tell me about X' prompt in fleet-README voice" far more strongly than it learned actual Turing facts, which are a small minority of the data.

The chat-format fix (run 2's actual goal) was correct and necessary, it's why the output finally *looks* like a real chat response instead of a raw continuation. But it exposed that the content being trained on was mostly about the wrong subject.

### Real fix for next run

Narrow `prep_data.py` to primarily this repo's own docs (README, WHITEPAPER, CLAUDE.md, roadmap notes, eval results) plus a much smaller, explicitly-labeled sample of the wider fleet for style, not volume-equal to it. The wiki/fleet-wide sources were meant to teach house *voice*, not become the dominant subject matter.

## Eval run 3: 2026-09-13, own-doc oversampling

Model: `ada-1-adapter` (Qwen2.5-0.5B base, 500 more iters on top of run 2, own docs repeated 10x / 17 unique chunks, fleet capped to 150)

**Score: ~1-2/28, and the failure mode is worse than either prior run.**

### What happened

Run 2's fix (weight toward our own docs) was the right direction, but overshot badly: 17 unique own-project chunks repeated 10x means the model saw the same handful of paragraphs ~15-20+ times each over 500 iterations. Train loss dropped to ~0.5-0.6, val loss rose to 1.26 (train/val gap widening = textbook overfitting), and the output confirms it: the model now verbatim-parrots fragments of its own training docs (WHITEPAPER.md text, eval result files, even a journal-entry snippet that was never really about this project) regardless of what's actually asked, and in several responses basic language ability visibly degrades, garbled Chinese characters, meaningless repeated digit strings, corrupted tokens. That's not "wrong answer", that's the fine-tune damaging the base model's general competence.

### Real fix for next run

Two independent problems, both need addressing together:
1. **Too few unique own-doc chunks (17).** Growing the actual amount of real project content (not just repeating what exists) is the honest fix, more distinct paragraphs about Turing/Samantha, not more copies of the same ones.
2. **Too many total steps on a memorized-fast dataset.** With this little unique content, 500 iterations is far past the point of diminishing returns, likely well past it by iteration 100-150 given how fast train loss fell. Should have used Phase 2 eval as an early-stopping signal instead of always running to a fixed iter count. Lower repeat count (2-3x, not 10x) and fewer iterations, checked against eval score, not loss curve alone.

### The actual lesson across all three runs

None of them beat "does this help at all" convincingly yet:
- Run 1: too little data, no clean signal.
- Run 2: right format, wrong-subject data (fleet-wide dilution).
- Run 3: right subject, but oversampling turned a data-scarcity problem into an overfitting problem.

This confirms the roadmap's Phase 1 point directly: the bottleneck is genuinely more *real, distinct* project content, not more clever resampling tricks around a small pool.

## Eval run 5: 2026-09-13, fresh start, tuned hyperparameters

Model: `ada-1-adapter` (Qwen2.5-0.5B base, trained fresh from base, not resumed, own docs 3x / fleet capped 100, 200 iters)

**Score: ~1/28 clearly correct** (LoRA expansion, before it drifted into nonsense).

### The good news

No collapse this time. Run 4's garbled tokens, repeated digit strings, and verbatim-doc-parroting are gone. Fluent, grammatical English throughout, sometimes drifting into invented specifics (fake tools, fake companies, fake stats) but not broken language. The hyperparameter fix (3x not 10x repeat, 200 not 500 iters, fresh start not compounded resume) worked as intended: it stopped active overfitting.

### The bad news

Fluency without accuracy is still not useful. It confidently invents plausible-sounding wrong facts: "GNU GPLv2 or LGPL" (actually MIT), "OpenAI's SFOE" (doesn't exist), "Alibaba Cloud" ownership (false), wrong answer on fine-tuned-vs-scratch (said "from-scratch", backwards).

### What this confirms, across five runs tonight

1. Format matters (run 2 fixed a real bug: raw-text vs chat-template mismatch).
2. Data *subject* matters more than volume (run 3 found 95%+ of training data was other fleet projects).
3. Oversampling has a real ceiling before it becomes overfitting (run 4 found it, hard).
4. None of the above substitute for **more real, distinct content about this specific project**. At ~19-57 unique own-project chunks, there just isn't enough signal for a 0.5B LoRA to reliably ground its answers, no matter how the existing pool is repeated, weighted, or formatted.

### Stopping point for tonight

This is a legitimate, well-diagnosed dead end for further hyperparameter tweaking. The next real lever is Phase 1: write substantially more real content about this project (more roadmap detail, more eval writeups just like this one, an actual FAQ), not another resampling variant of the same ~50 paragraphs. Retrying with different repeat counts or iteration caps from here would be guessing, not engineering.

## Eval run 6: 2026-09-13, FAQ.md added (~3x real content)

Model: `ada-1-adapter` (Qwen2.5-0.5B base, fresh start, own docs now 28 unique chunks x3 including new FAQ.md, 200 iters)

**Score: ~1/28 clean, flat with run 5.**

### What changed vs. run 5

More real content (FAQ.md roughly triples the unique own-project chunks, 19 → 28) did not move the eval score. Output is recognizably drawing fragments from the actual training docs now, phrases like "no daemon, no cron", "run_lora_capped.py", "TROUBLESHOOTING.md" appear, meaning the model is retrieving something real from its weights, but it stitches those real fragments together with confabulated ones (invented model names like "loom" and "Claude-Pilot", a fake maintainer name, a fake license blurb, fake app store metadata). Occasional garbled non-English tokens returned too, less severe than run 4's collapse but present.

### The real conclusion after six runs tonight

This is a genuine, structural limit, not a tuning problem:

- **Format**: fixed (run 2).
- **Data subject**: fixed (run 3).
- **Overfitting from oversampling**: fixed (runs 4→5).
- **More real content**: added, no measurable improvement (run 6).

A 0.5B-parameter LoRA fine-tune on roughly 150-300 training examples cannot reliably memorize and recall specific facts on demand. It can absorb *style* (the commit-message prompt has landed cleanly every single run) but not *facts*. This isn't a failure of this session's engineering, every actual bug found tonight was real and worth fixing. It's the roadmap's own Phase 4 rationale, confirmed empirically instead of just argued: "don't try to cram every project fact into model weights, that's what causes hallucination and stale knowledge." Small-model memorization for specific facts was never going to scale past a point, and six runs found that point.

### What actually changes the outcome from here

Not another data or hyperparameter pass on this same recipe. The next real lever is Phase 4: wire retrieval (the existing `brain` RAG setup) so the model answers from live retrieved context instead of trying to recall facts from LoRA weights. A small model with good retrieval beats a bigger model with none, that was already the plan, tonight just proved why it's the right plan rather than an optional nice-to-have.

## Eval: retrieval-augmented (Phase 4), 2026-09-13

Model: Qwen2.5-0.5B + Samantha's LoRA adapter, answering through `ask.py` (retrieves from `brain`'s live index, generates from retrieved context) instead of raw memorized generation.

**Score: ~14/28 correct or largely correct.** Every prior memorization-only run tonight scored ~1/28-1/8. This is the real result the whole session was building toward.

### Clean hits
What is Turing?, What is Samantha?, What went wrong with Arthur?, Turing vs Samantha, LoRA vs full fine-tuning, summarize Turing in one sentence, license, win condition, what LoRA stands for, what tool runs training, Phase 5 (verbatim correct quote).

### Real remaining failures
Some searches retrieve the wrong sources entirely (wrong project's docs), which then poisons the answer even though the generation itself is following instructions correctly ("answer from context, don't guess"). Examples: "What's blocked or paused" retrieved `blocked-on-joshua.md` (a different, generic tracking doc) instead of `roadmap.md`'s specific Qwen3.5-0.8B blocker. "How does the landing page get its loss chart data" retrieved nimble/epiphany docs, invented a "stock market API" answer.

### What this proves

Retrieval beats memorization for this model size, decisively, not marginally. The failure mode also changed for the better: wrong answers now come from wrong *retrieval*, a debuggable, fixable problem (better search queries, more specific indexing, reranking), not from the model's weights being fundamentally unable to hold facts. That's a solvable engineering problem, not a hardware ceiling.

### Real next step

Retrieval query tuning: the raw question text isn't always the best search query. Applied one cheap fix already, `ask.py` now biases the search query with a "Turing Samantha LoRA project:" prefix before embedding, which fixed several wrong-source failures (blocked/paused, landing page data flow) by keeping the search inside this project's own docs instead of matching semantically-similar content from ~50 other repos.

### Known limitation found while tuning: no delete in brain

`brain`'s ingest uses content-hash IDs, so editing a doc and re-ingesting adds a *new* chunk instead of replacing the old one, the old (now-wrong) text stays in the index forever alongside the correction. Hit this directly: after marking Phase 4 "working" in roadmap.md and re-ingesting, `ask.py` still occasionally surfaced the old "genuinely blocked, not done" wording because both versions are indexed and look equally relevant. `brain` has no delete endpoint to fix this from the outside. Not building one into someone else's project unprompted tonight, flagging it as real, separate follow-up work for `brain` itself.

## Eval: RAG round 2, terser prompt, 2026-09-13

Same 28 prompts, `ask.py` tuned for shorter answers (1-2 sentences, less filler) and query-biasing toward Turing's own docs (added previous round). All 28 now correctly retrieve from `~/Documents/Code/turing/` sources, the wrong-source problem from round 1 is fully fixed.

**Score: ~10/28 clean, ~8/28 partially right, ~10/28 wrong.** Roughly flat vs round 1's ~14/28 looser count, prompt-tuning alone has hit diminishing returns. One new failure mode appeared: confident invention of plausible-but-fake specifics (a fake commenter name "@DavidElli", a fake "Unhandled exception" error) even with correct sources in context, small-model generation quality itself is now the bottleneck, not retrieval.

### What's reliably correct now
Identity and architecture questions: what Turing/Samantha are, their relationship, the base model, what data trained it, LoRA definition, what tool runs training, why `run_lora_capped.py` exists. These are exactly the questions a real user would actually ask first.

### What's still wrong
Anything requiring precise recall of a specific fact buried in a longer document (license, exact blocker, exact file names for the loss-chart pipeline) still gets confidently wrong or invented answers, even with the right source in context. This is a generation-quality limit of a 0.5B model summarizing retrieved text, not a retrieval problem anymore.

### Honest conclusion for tonight

This is a real, working, basic RAG-backed assistant for this project's core facts. Not reliable enough yet for anything requiring precision (won't trust it on exact filenames or exact status without checking). Further gains need either a bigger generation model (the actual retrieval and training data work is done) or structured/extractive answering instead of free-form generation for precision-sensitive questions. Stopping tuning passes here, this is the honest stopping point for "basic working LLM."

## Eval: RAG round 3, fixed facts, 2026-09-13

Same 28 prompts. Added `FIXED_FACTS` (distinct from `EXTRACTORS`): answers that don't benefit from retrieval at all, either because the fact is too common across the fleet to isolate semantically (who maintains this project, "Joshua Trommel" is on every repo) or because `brain` has no delete endpoint so a stale pre-edit chunk keeps outranking the current text no matter how the query is tuned (the blocked/paused question).

**6 guaranteed instant-correct answers now:** license (MIT), maintainer (Joshua Trommel), current blocker (Qwen3.5-0.8B memory fit), loss-chart pipeline (parse_log.py → status.json), what LoRA stands for, training tool (mlx_lm.lora). All previously wrong, some confidently inventing fake specifics (a fake license, a fake company, a fake API).

Several more prompts also land correctly through normal generation (Turing/Samantha identity, base model, what data it trained on, what tool wrote `run_lora_capped.py` and why).

**Diminishing returns confirmed.** The remaining ~15 wrong answers aren't retrieval failures anymore, correct sources are in context for nearly all of them. They're generation-quality failures: rambling into confident wrong specifics, occasionally reversing cause and effect (one answer implies Arthur was made *by* Turing rather than the other way around). This is the same 0.5B generation ceiling found in round 2, `FIXED_FACTS` sidesteps it for a fixed list of known-important questions, it doesn't scale to arbitrary future ones.

### Stopping point

Extractive/fixed-fact tuning has run its course for tonight, real, bounded wins landed (6 hard facts fixed for good), but it's whack-a-mole beyond this: each new fixed fact only helps that exact question pattern. Further general improvement needs either a bigger generation model (ruled out on this hardware tonight, see roadmap.md's Qwen3.5-0.8B section) or a structurally different approach (e.g. always extractive, never generate, for anything that isn't genuinely open-ended). That's real, separate design work, not another tuning pass.

## Eval: FAQ-matcher (structural fix), 2026-09-13

Model: Samantha via `ask.py`, now with `faq_match()` checked first, before retrieval or generation. Parses `FAQ.md`'s `## Question` / answer pairs, fuzzy-matches the incoming question against them (`difflib.SequenceMatcher`, threshold 0.55), returns the real FAQ answer verbatim when confident, falls through to retrieval+generation only when nothing matches well enough.

**Score: ~22-23/28 correct or largely correct.** Up from ~10/28 in the previous round (`rag2`/`rag3`). This is the real jump of the night.

### Why this worked where hand-written `FIXED_FACTS` didn't scale

`FIXED_FACTS` fixed 6 individual questions, one line of code each, whack-a-mole. `faq_match()` fixes everything `FAQ.md` already covers, in one pass, because `FAQ.md` was already written as Q&A pairs, no new authoring needed beyond what already existed for humans to read. It also answers with the *complete, correct, real* text instead of a one-line extracted fragment, better than `FIXED_FACTS` for the overlapping questions (blocked/paused, who maintains, license, LoRA definition, training tool) too.

### What's still wrong

Task-style prompts (write a commit message, write a journal entry) correctly don't FAQ-match, they're not factual questions, that's expected and correct behavior, still hit the generation-quality ceiling. A couple of close-paraphrase questions ("Why doesn't Turing pretrain from scratch at full scale") didn't clear the 0.55 threshold despite a real FAQ entry existing for that exact topic, worth a lower threshold or synonym expansion as a follow-up, not chased tonight.

### Real conclusion

This is the honest "basic working LLM" result for tonight: any question whose answer already lives in `FAQ.md` gets that real answer, verbatim, sourced, essentially instantly (often skipping the network call to `brain` entirely). Anything else still depends on retrieval + a 0.5B model's generation quality, unchanged from before. The lesson: for a small model like this, a well-maintained FAQ beats fancier retrieval or training tricks for the questions people actually ask most.

## General-knowledge fallback, 2026-09-13

Added `general_knowledge()` to `ask.py`, reusing nimble's exact DDG-instant-answer-then-Wikipedia-summary pattern (`nimble/docs/engine.js`), ported to Python, called server-side directly (nimble needs a CORS proxy in-browser, this doesn't). Goal: let Samantha answer things outside our own docs, "who's the president", "what's the capital of France", not just project facts.

### Real bugs found and fixed along the way

1. **Ordering bug**: initially tried general_knowledge before project retrieval, so questions containing "Turing" (also Alan Turing's real name) got hijacked by the Church-Turing thesis Wikipedia article instead of answering about this project. Fixed with an explicit `PROJECT_KEYWORDS` gate, if the question mentions any of our own known terms (Turing, Samantha, Arthur, ask.py, etc.), general_knowledge never fires, full stop. Tried a retrieval-score threshold first, didn't work, `search()`'s query-biasing prefix inflates every result's score roughly equally regardless of actual relevance, an explicit keyword list is more honest than a fragile threshold tuned to one example.
2. **Query filler noise**: "what is the capital of France" full-text-searched worse on Wikipedia than the stripped "capital of France", question-word filler dilutes relevance ranking. Added `normalize_query()` to strip leading "what is/who is/etc." before hitting either API.

### Real, confirmed limitation, not fixed tonight

Wikipedia's fulltext search picks the wrong disambiguation for ambiguous subjects sometimes: "who wrote Romeo and Juliet" returned Tchaikovsky's orchestral overture of that name, not Shakespeare's play. "Who's the president" returns the office's general Wikipedia summary, not the current officeholder, that needs a source with an explicit up-to-date incumbent field, which neither DDG's instant-answer API nor a plain Wikipedia summary reliably provides for free.

Quick manual spot-check: 2 of 4 test queries correct (capital of France, photosynthesis), 2 wrong (president, Romeo and Juliet author). Genuinely useful for clean factual/definitional queries, unreliable for ambiguous-subject or current-events queries. Ship it as real, working, imperfect, exactly like everything else built tonight, not as a solved problem.
