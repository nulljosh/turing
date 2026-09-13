# Eval run 3: 2026-09-13, own-doc oversampling

Model: `ada-1-adapter` (Qwen2.5-0.5B base, 500 more iters on top of run 2, own docs repeated 10x / 17 unique chunks, fleet capped to 150)

**Score: ~1-2/28, and the failure mode is worse than either prior run.**

## What happened

Run 2's fix (weight toward our own docs) was the right direction, but overshot badly: 17 unique own-project chunks repeated 10x means the model saw the same handful of paragraphs ~15-20+ times each over 500 iterations. Train loss dropped to ~0.5-0.6, val loss rose to 1.26 (train/val gap widening = textbook overfitting), and the output confirms it: the model now verbatim-parrots fragments of its own training docs (WHITEPAPER.md text, eval result files, even a journal-entry snippet that was never really about this project) regardless of what's actually asked, and in several responses basic language ability visibly degrades, garbled Chinese characters, meaningless repeated digit strings, corrupted tokens. That's not "wrong answer", that's the fine-tune damaging the base model's general competence.

## Real fix for next run

Two independent problems, both need addressing together:
1. **Too few unique own-doc chunks (17).** Growing the actual amount of real project content (not just repeating what exists) is the honest fix, more distinct paragraphs about Turing/Samantha, not more copies of the same ones.
2. **Too many total steps on a memorized-fast dataset.** With this little unique content, 500 iterations is far past the point of diminishing returns, likely well past it by iteration 100-150 given how fast train loss fell. Should have used Phase 2 eval as an early-stopping signal instead of always running to a fixed iter count. Lower repeat count (2-3x, not 10x) and fewer iterations, checked against eval score, not loss curve alone.

## The actual lesson across all three runs

None of them beat "does this help at all" convincingly yet:
- Run 1: too little data, no clean signal.
- Run 2: right format, wrong-subject data (fleet-wide dilution).
- Run 3: right subject, but oversampling turned a data-scarcity problem into an overfitting problem.

This confirms the roadmap's Phase 1 point directly: the bottleneck is genuinely more *real, distinct* project content, not more clever resampling tricks around a small pool.
