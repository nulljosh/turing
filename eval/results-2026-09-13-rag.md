# Eval: retrieval-augmented (Phase 4), 2026-09-13

Model: Qwen2.5-0.5B + Samantha's LoRA adapter, answering through `ask.py` (retrieves from `brain`'s live index, generates from retrieved context) instead of raw memorized generation.

**Score: ~14/28 correct or largely correct.** Every prior memorization-only run tonight scored ~1/28-1/8. This is the real result the whole session was building toward.

## Clean hits
What is Turing?, What is Samantha?, What went wrong with Arthur?, Turing vs Samantha, LoRA vs full fine-tuning, summarize Turing in one sentence, license, win condition, what LoRA stands for, what tool runs training, Phase 5 (verbatim correct quote).

## Real remaining failures
Some searches retrieve the wrong sources entirely (wrong project's docs), which then poisons the answer even though the generation itself is following instructions correctly ("answer from context, don't guess"). Examples: "What's blocked or paused" retrieved `blocked-on-joshua.md` (a different, generic tracking doc) instead of `roadmap.md`'s specific Qwen3.5-0.8B blocker. "How does the landing page get its loss chart data" retrieved nimble/epiphany docs, invented a "stock market API" answer.

## What this proves

Retrieval beats memorization for this model size, decisively, not marginally. The failure mode also changed for the better: wrong answers now come from wrong *retrieval*, a debuggable, fixable problem (better search queries, more specific indexing, reranking), not from the model's weights being fundamentally unable to hold facts. That's a solvable engineering problem, not a hardware ceiling.

## Real next step

Retrieval query tuning: the raw question text isn't always the best search query. A query-rewriting step, or hybrid keyword+semantic search, would likely fix most of the wrong-source failures above.
