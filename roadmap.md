# Roadmap

Anthropic spends billions of dollars and years with thousands of GPUs on foundation models. That's not this. Transformers themselves are only from 2017 (the "Attention Is All You Need" paper), the whole field is young enough that a lot of useful ground is still coverable by one person on a Mac Mini, as long as the goal is calibrated to the hardware.

### Phase 0: Pipeline proof (now, days)
LoRA fine-tune of a small open base (Qwen2.5-0.5B-Instruct) on our own Obsidian wiki + project READMEs. 588 lines of data, 200 iterations, runs in minutes on the M4. Goal: prove the loop works end to end (data → train → adapter → serve), not quality. Done, no gibberish (unlike Arthur).

### Phase 1: More data, same model (weeks 1-3)
Feed it everything: journal entries, commit messages, project READMEs/WHITEPAPERs, roadmap.md files, notes vault, even old Slack/iMessage exports if we want the voice right. Thousands of chunks instead of hundreds. Re-run LoRA. This is the single highest-leverage step, small models improve far more from 10x the data than from 10x the iterations.

### Phase 2: Evaluate like it matters (weeks 2-4, parallel with Phase 1), started
`eval/prompts.jsonl` has 28 real prompts, `eval/run_eval.py` generates against any adapter. See `eval/` for run-by-run results. A model that "trains" but never gets graded is a number going down, not progress.

### Phase 3: Bigger base, same recipe (month 2)
Once the pipeline is boring and repeatable, try a bigger base. Candidates as of Sept 2026: `Qwen3.5-0.8B` (direct successor to what we're using now), `SmolLM2-1.7B` (fully open training recipe, worth it if transparency matters to us), `Llama-3.2-1B-Instruct` (solid middle ground, ~1GB at Q4). Bigger model = slower training, more memory, better baseline fluency. Compare quality per minute of training against the 0.5B, there's a real chance the 0.5B fine-tuned on great data beats a bigger base fine-tuned on so-so data.

Started early, blocked on this hardware: `Qwen3.5-0.8B-4bit` caused three crashes in a row (two system-memory, one Metal/GPU OOM mid-backprop even with plenty of free RAM). That last one is the real signal, it's a genuine fit problem, not a "too many things running" problem. `ada-1b-adapter/` sits unfinished. Revisit with a smaller batch size / gradient accumulation tuned down, or on different hardware, not a blind retry.

### Phase 4: Retrieval instead of memorization (month 2-3)
Don't try to cram every project fact into model weights, that's what causes hallucination and stale knowledge. Wire it to `brain` (the existing RAG-over-notes setup) so the model reasons over live retrieved context instead of "remembering" it. Small fine-tuned model + good retrieval beats a bigger model with neither. This is the actual production architecture, not a toy.

### Phase 5: Give it a job (month 3+)
Once retrieval works, point it at concrete, boring, checkable tasks:
- **In-voice drafting**, journal entries, commit messages, README sections in house style (no em dash, no AI voice, sans-serif brain already enforced elsewhere, teach the model the same rules)
- **Project Q&A**, "what's the status of Epiphany", answered from the wiki instead of us re-reading MEMORY.md
- **Local autocomplete**, a tiny always-available model that doesn't hit the network, for quick text expansion
- **A judge/filter model**, small models are cheap enough to run on every commit or PR as a first-pass linter before anything hits a bigger model

### Phase 6: Distillation, not scale (month 4+, optional/ambitious)
Instead of chasing bigger bases, use a frontier model (Claude) to generate high-quality synthetic training examples in our exact style, then distill that into Samantha. This is literally how most useful small models are built today, nobody pretrains from raw internet text anymore if they can help it.

### What we will never do on this budget
Pretrain a foundation model from raw text at frontier scale. That needs a data-center, a research team, and normally $10M+ in compute even for a "small" frontier-adjacent model. Not the plan, the plan is a small model that's genuinely ours and genuinely useful, which is a completely different (and completely reachable) goal.

### Win condition
Not "beat GPT." Win condition is: ask it to draft something in our voice, or answer a question about one of our own projects, and the answer is actually good enough to use without rewriting it.

## Progress log

- **2026-09-13, run 1:** 588 lines (wiki + READMEs), 200 iters, raw-text format. Loss bounced 2.2-3.4, no clean convergence, too little data. Proved the pipeline works end to end, no gibberish (unlike Arthur).
- **2026-09-13, run 2:** widened sources to roadmap.md + CLAUDE.md across the fleet, 2054 lines, 500 iters, still raw-text format. Val loss down from 3.66 → 2.99 by iter 200. Eval score: 1/8.
- **2026-09-13, run 3:** switched to chat-formatted data, 500 iters. Eval score: ~1/28, and the failure mode got worse in a telling way, it started answering in *other fleet projects'* README voice, because the training data globbed the whole ~50-repo fleet with no weighting toward Turing's own docs.
- **2026-09-13, run 4:** oversampled own docs 10x (only 17 unique chunks) on top of run 3's weights, 500 more iters. Overfit hard, train loss 0.5-0.6 vs val loss 1.26, output degraded into verbatim doc parroting and garbled tokens regardless of prompt. Real lesson: neither more repeats of a small pool nor more iterations substitute for more distinct real content.
- **2026-09-13, run 5:** fresh start from base (not resumed on the overfit run 4 weights), `OWN_REPEATS` 10→3, 200 iters instead of 500. Fixed the collapse, fluent English again, no garbled tokens or verbatim parroting. But still only ~1/28 factually correct, confidently invents plausible wrong facts. Confirms across five runs tonight: format and data-subject fixes were both real and necessary, but none of them substitute for more distinct real content about this project. Stopping hyperparameter tweaking here, next real lever is genuinely writing more, not resampling the same ~50 paragraphs differently.
