# Eval run 5: 2026-09-13, fresh start, tuned hyperparameters

Model: `ada-1-adapter` (Qwen2.5-0.5B base, trained fresh from base, not resumed, own docs 3x / fleet capped 100, 200 iters)

**Score: ~1/28 clearly correct** (LoRA expansion, before it drifted into nonsense).

## The good news

No collapse this time. Run 4's garbled tokens, repeated digit strings, and verbatim-doc-parroting are gone. Fluent, grammatical English throughout, sometimes drifting into invented specifics (fake tools, fake companies, fake stats) but not broken language. The hyperparameter fix (3x not 10x repeat, 200 not 500 iters, fresh start not compounded resume) worked as intended: it stopped active overfitting.

## The bad news

Fluency without accuracy is still not useful. It confidently invents plausible-sounding wrong facts: "GNU GPLv2 or LGPL" (actually MIT), "OpenAI's SFOE" (doesn't exist), "Alibaba Cloud" ownership (false), wrong answer on fine-tuned-vs-scratch (said "from-scratch", backwards).

## What this confirms, across five runs tonight

1. Format matters (run 2 fixed a real bug: raw-text vs chat-template mismatch).
2. Data *subject* matters more than volume (run 3 found 95%+ of training data was other fleet projects).
3. Oversampling has a real ceiling before it becomes overfitting (run 4 found it, hard).
4. None of the above substitute for **more real, distinct content about this specific project**. At ~19-57 unique own-project chunks, there just isn't enough signal for a 0.5B LoRA to reliably ground its answers, no matter how the existing pool is repeated, weighted, or formatted.

## Stopping point for tonight

This is a legitimate, well-diagnosed dead end for further hyperparameter tweaking. The next real lever is Phase 1: write substantially more real content about this project (more roadmap detail, more eval writeups just like this one, an actual FAQ), not another resampling variant of the same ~50 paragraphs. Retrying with different repeat counts or iteration caps from here would be guessing, not engineering.
