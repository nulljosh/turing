# Eval run 2: 2026-09-13, chat-format fix

Model: `ada-1-adapter` (Qwen2.5-0.5B base, 500 iters, chat-formatted data, resumed once from checkpoint 100)

**Score: ~1/28, arguably worse than run 1's 1/8.**

## What changed

Run 1 hallucinated a plausible but wrong "Samantha is an app" story. Run 2 does something different and more revealing: it answers almost every prompt with a *different fleet project's* README pattern (Sparkjar, Sift, Tally, Cloudflare Workers, random iOS build statuses), often looping the same phrase repeatedly ("It is a real Durable Objects client that runs on Cloudflare's Compute Engine" x4).

## Root cause found

`prep_data.py` globs every `README.md` / `roadmap.md` / `CLAUDE.md` across the entire `~/Documents/Code` fleet, not just this project's own docs. Turing is one tiny project among 50+. So the training set is overwhelmingly "generic fleet project README" text, and each chunk's synthetic prompt is `"Tell me about {source filename}"`, meaning the model learned "answer any 'tell me about X' prompt in fleet-README voice" far more strongly than it learned actual Turing facts, which are a small minority of the data.

The chat-format fix (run 2's actual goal) was correct and necessary, it's why the output finally *looks* like a real chat response instead of a raw continuation. But it exposed that the content being trained on was mostly about the wrong subject.

## Real fix for next run

Narrow `prep_data.py` to primarily this repo's own docs (README, WHITEPAPER, CLAUDE.md, roadmap notes, eval results) plus a much smaller, explicitly-labeled sample of the wider fleet for style, not volume-equal to it. The wiki/fleet-wide sources were meant to teach house *voice*, not become the dominant subject matter.
