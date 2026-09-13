# Turing Technical Whitepaper

**v0.5** | September 2026

Turing is a pipeline for building small language models on consumer hardware. Its first model, Samantha, is a LoRA fine-tune of a small open base, trained on this project's own notes and documentation instead of the open internet, so it inherits house voice instead of generic web text.

## The core mechanic

Pretraining a language model from raw text needs gigabytes of clean data and enough compute to make noise start looking like language, a prior attempt (project code name Arthur) tried exactly that on a single Mac and produced gibberish after days of training. Turing skips that step entirely.

Instead: start from an already-trained small open model (`Qwen2.5-0.5B-Instruct`), which already knows grammar, facts, and reasoning at a basic level. Apply LoRA (Low-Rank Adaptation), a small set of trainable weight deltas layered on top of the frozen base, trained only on the target voice and knowledge. This is the same idea behind most consumer-facing fine-tunes: don't relearn language, adjust it.

```
raw text (wiki, READMEs, notes)
        │  prep_data.py: chunk + JSONL
        ▼
   train.jsonl / valid.jsonl
        │  mlx_lm.lora: LoRA fine-tune on Apple Silicon (MLX)
        ▼
   ada-1-adapter/  (a few MB of weight deltas, not a full model copy)
        │  parse_log.py: loss history
        ▼
   status.json → landing page chart
```

Training runs entirely on-device via Apple's MLX framework, no cloud GPU, no API cost, no daemon. A run is invoked, not scheduled; more data beats more iterations for a corpus this size.

## What's actually working now

Six training runs proved the fine-tune alone learns style but not facts (see roadmap.md), so retrieval carries the facts instead: `ask.py`/`chat.py` pull real passages from `brain`, Turing's own RAG system, and answer from those instead of memorized weights. A fuzzy FAQ-matcher answers common questions straight from `FAQ.md`, no generation needed. A Wikidata lookup answers "who's the president/prime minister of X" with today's actual holder, not a description of the office. Every one of these is checked by real automated QA (`eval/score.py`, a held-out set, `test_chat.py`, CI), not eyeballed.

## Where this goes

Samantha alone won't out-argue a frontier model, and that was never the goal. Small trained model + good retrieval is closer to how production small-model systems actually work than a bigger model with neither, that combination is already running, not just planned.

---
MIT License, 2026 Joshua Trommel.
