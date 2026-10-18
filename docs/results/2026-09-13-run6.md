# Eval run 6: 2026-09-13, FAQ.md added (~3x real content)

Model: `ada-1-adapter` (Qwen2.5-0.5B base, fresh start, own docs now 28 unique chunks x3 including new FAQ.md, 200 iters)

**Score: ~1/28 clean, flat with run 5.**

## What changed vs. run 5

More real content (FAQ.md roughly triples the unique own-project chunks, 19 → 28) did not move the eval score. Output is recognizably drawing fragments from the actual training docs now, phrases like "no daemon, no cron", "run_lora_capped.py", "TROUBLESHOOTING.md" appear, meaning the model is retrieving something real from its weights, but it stitches those real fragments together with confabulated ones (invented model names like "loom" and "Claude-Pilot", a fake maintainer name, a fake license blurb, fake app store metadata). Occasional garbled non-English tokens returned too, less severe than run 4's collapse but present.

## The real conclusion after six runs tonight

This is a genuine, structural limit, not a tuning problem:

- **Format**: fixed (run 2).
- **Data subject**: fixed (run 3).
- **Overfitting from oversampling**: fixed (runs 4→5).
- **More real content**: added, no measurable improvement (run 6).

A 0.5B-parameter LoRA fine-tune on roughly 150-300 training examples cannot reliably memorize and recall specific facts on demand. It can absorb *style* (the commit-message prompt has landed cleanly every single run) but not *facts*. This isn't a failure of this session's engineering, every actual bug found tonight was real and worth fixing. It's the roadmap's own Phase 4 rationale, confirmed empirically instead of just argued: "don't try to cram every project fact into model weights, that's what causes hallucination and stale knowledge." Small-model memorization for specific facts was never going to scale past a point, and six runs found that point.

## What actually changes the outcome from here

Not another data or hyperparameter pass on this same recipe. The next real lever is Phase 4: wire retrieval (the existing `brain` RAG setup) so the model answers from live retrieved context instead of trying to recall facts from LoRA weights. A small model with good retrieval beats a bigger model with none, that was already the plan, tonight just proved why it's the right plan rather than an optional nice-to-have.
