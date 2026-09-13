# Turing Technical Whitepaper

**v0.1** | September 2026

Turing is a pipeline for building small language models on consumer hardware. Its first model, Ada-1, is a LoRA fine-tune of a small open base, trained on this project's own notes and documentation instead of the open internet, so it inherits house voice instead of generic web text.

## The core mechanic

Pretraining a language model from raw text needs gigabytes of clean data and enough compute to make noise start looking like language — a prior attempt (project code name Arthur) tried exactly that on a single Mac and produced gibberish after days of training. Turing skips that step entirely.

Instead: start from an already-trained small open model (`Qwen2.5-0.5B-Instruct`), which already knows grammar, facts, and reasoning at a basic level. Apply LoRA (Low-Rank Adaptation) — a small set of trainable weight deltas layered on top of the frozen base — trained only on the target voice and knowledge. This is the same idea behind most consumer-facing fine-tunes: don't relearn language, adjust it.

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

Training runs entirely on-device via Apple's MLX framework — no cloud GPU, no API cost, no daemon. A run is invoked, not scheduled; more data beats more iterations for a corpus this size.

## Where this goes

Ada-1 alone won't out-argue a frontier model, and that was never the goal. The plan (see README roadmap) is retrieval-augmented: keep the model small and fast, wire it to the project's existing RAG system for facts, and let the fine-tune carry only voice and reasoning style. That combination — small trained model + good retrieval — is closer to how production small-model systems actually work than a bigger model with neither.

---
MIT License, 2026 Joshua Trommel.
