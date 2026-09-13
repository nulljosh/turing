<img src="icon.svg" width="80">

# Turing

![version](https://img.shields.io/badge/version-phase%201-blue)
![license](https://img.shields.io/badge/license-MIT-green) [![GitHub](https://img.shields.io/badge/GitHub-nulljosh%2Fturing-black?logo=github)](https://github.com/nulljosh/turing)
![base model](https://img.shields.io/badge/base-Qwen2.5--0.5B-blue)
![platform](https://img.shields.io/badge/platform-Apple%20Silicon%20(MLX)-lightgrey)
[![repo size](https://img.shields.io/github/repo-size/nulljosh/turing)](https://github.com/nulljosh/turing)
[![last commit](https://img.shields.io/github/last-commit/nulljosh/turing)](https://github.com/nulljosh/turing/commits/main)

Building small language models in the open. First model: **Ada-1**.

Live status page: [turing.heyitsmejosh.com](https://turing.heyitsmejosh.com)

**Turing vs. Ada-1:** Turing is the project, the pipeline, the repo, this whole effort. Ada-1 is a model Turing produces. Same relationship as Anthropic and Claude (or a Claude model like Haiku/Fable): the project name is fixed, model names change as new ones ship. Turing will likely produce more than one model over time; each gets its own name, Turing stays Turing.

## Why

Tried this before under the name Arthur, trained a model from scratch and it spat out gibberish after a few days. Wrong approach: from-scratch pretraining needs gigabytes of clean text and a lot of compute to stop being noise. Restarted as Turing with a different plan.

## What Ada-1 is

A LoRA fine-tune of `Qwen2.5-0.5B-Instruct-4bit` (small enough to train on-device on an M4), trained on this codebase's own Obsidian wiki and project READMEs, so it actually knows the projects and writes in house voice, instead of learning language from zero.

## Pipeline

```
prep_data.py    -> data/train.jsonl, data/valid.jsonl   (wiki + READMEs, chunked)
mlx_lm.lora     -> ada-1-adapter/                        (LoRA weights)
parse_log.py    -> status.json                           (loss history for the landing page)
```

Full diagram: [`architecture.svg`](architecture.svg) (includes the parallel from-scratch path under `scratch/`).

Rerun training for more iterations anytime:

```
./.venv/bin/mlx_lm.lora --model mlx-community/Qwen2.5-0.5B-Instruct-4bit \
  --train --data ./data --iters 200 \
  --resume-adapter-file ./ada-1-adapter/adapters.safetensors \
  --adapter-path ./ada-1-adapter
```

No daemon, no cron, training runs when invoked, not on a schedule.

## Status

See `index.html` / status.json for live loss numbers.

## Base model comparison (Phase 3, blocked on this hardware)

Tried running a second base (`Qwen3.5-0.8B-4bit`) alongside the 0.5B to compare quality before committing to one. Three failures in a row: two system-memory crashes, then a Metal (GPU) out-of-memory error mid-step even with plenty of free RAM. That last one is the real signal, it's not a "too many things running" problem, the model plus training state genuinely doesn't fit this machine's unified memory comfortably during backprop. Not retrying blind.

- `ada-1-adapter/` = LoRA on `Qwen2.5-0.5B-Instruct-4bit`, done and stable, this is the real Ada-1 for now.
- `ada-1b-adapter/` = LoRA on `Qwen3.5-0.8B-4bit`, abandoned on this hardware. Revisit only with a smaller batch size / gradient accumulation tuned down, or on different hardware, not a blind retry.

## Progress log

- **2026-09-13, run 1:** 588 lines (wiki + READMEs), 200 iters. Loss bounced 2.2-3.4, no clean convergence, too little data. Proved the pipeline works end to end, no gibberish (unlike Arthur).
- **2026-09-13, run 2:** widened sources to roadmap.md + CLAUDE.md across the fleet, 2054 lines, 500 iters, in progress. Val loss down from 3.66 → 2.99 by iter 200.

## A note on benchmarking

Ada-1's base model *is* Qwen2.5-0.5B, LoRA only adds a small trained delta on top of it. So "beat Qwen" isn't really a fair or even coherent bar; a LoRA fine-tune of Qwen can't outperform Qwen in general, only on the narrow thing it was fine-tuned for (writing in our voice, knowing our projects). The real benchmark is: does the fine-tuned version answer our own questions better than stock Qwen does. That's what Phase 2 (eval prompts) is for.

## Roadmap (honest version)

Anthropic spends billions of dollars and years with thousands of GPUs on foundation models. That's not this. Transformers themselves are only from 2017 (the "Attention Is All You Need" paper), the whole field is young enough that a lot of useful ground is still coverable by one person on a Mac Mini, as long as the goal is calibrated to the hardware.

### Phase 0: Pipeline proof (now, days)
LoRA fine-tune of a small open base (Qwen2.5-0.5B-Instruct) on our own Obsidian wiki + project READMEs. 588 lines of data, 200 iterations, runs in minutes on the M4. Goal: prove the loop works end to end (data → train → adapter → serve), not quality. This is where we are, loss bouncing between 2.2 and 3.4, which is expected on this little data.

### Phase 1: More data, same model (weeks 1-3)
Feed it everything: journal entries, commit messages, project READMEs/WHITEPAPERs, roadmap.md files, notes vault, even old Slack/iMessage exports if we want the voice right. Thousands of chunks instead of hundreds. Re-run LoRA. This is the single highest-leverage step, small models improve far more from 10x the data than from 10x the iterations.

### Phase 2: Evaluate like it matters (weeks 2-4, parallel with Phase 1)
Stop trusting loss numbers alone. Write 20-30 real prompts we'd actually ask it ("summarize this project", "write a commit message in our voice", "what's blocked on Joshua right now") and manually score outputs before/after each retrain. A model that "trains" but never gets graded is a number going down, not progress.

### Phase 3: Bigger base, same recipe (month 2)
Once the pipeline is boring and repeatable, try a bigger base. Candidates as of Sept 2026: `Qwen3.5-0.8B` (direct successor to what we're using now), `SmolLM2-1.7B` (fully open training recipe, worth it if transparency matters to us), `Llama-3.2-1B-Instruct` (solid middle ground, ~1GB at Q4). Bigger model = slower training, more memory, better baseline fluency. Compare quality per minute of training against the 0.5B, there's a real chance the 0.5B fine-tuned on great data beats a bigger base fine-tuned on so-so data.

### Phase 4: Retrieval instead of memorization (month 2-3)
Don't try to cram every project fact into model weights, that's what causes hallucination and stale knowledge. Wire it to `brain` (the existing RAG-over-notes setup) so the model reasons over live retrieved context instead of "remembering" it. Small fine-tuned model + good retrieval beats a bigger model with neither. This is the actual production architecture, not a toy.

### Phase 5: Give it a job (month 3+)
Once retrieval works, point it at concrete, boring, checkable tasks:
- **In-voice drafting**, journal entries, commit messages, README sections in house style (no em dash, no AI voice, sans-serif brain already enforced elsewhere, teach the model the same rules)
- **Project Q&A**, "what's the status of Epiphany", answered from the wiki instead of us re-reading MEMORY.md
- **Local autocomplete**, a tiny always-available model that doesn't hit the network, for quick text expansion
- **A judge/filter model**, small models are cheap enough to run on every commit or PR as a first-pass linter before anything hits a bigger model

### Phase 6: Distillation, not scale (month 4+, optional/ambitious)
Instead of chasing bigger bases, use a frontier model (Claude) to generate high-quality synthetic training examples in our exact style, then distill that into Ada-1. This is literally how most useful small models are built today, nobody pretrains from raw internet text anymore if they can help it.

### What we will never do on this budget
Pretrain a foundation model from raw text at frontier scale. That needs a data-center, a research team, and normally $10M+ in compute even for a "small" frontier-adjacent model. Not the plan, the plan is a small model that's genuinely ours and genuinely useful, which is a completely different (and completely reachable) goal.

### Win condition
Not "beat GPT." Win condition is: ask it to draft something in our voice, or answer a question about one of our own projects, and the answer is actually good enough to use without rewriting it.
