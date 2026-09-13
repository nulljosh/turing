# Eval: RAG round 2, terser prompt, 2026-09-13

Same 28 prompts, `ask.py` tuned for shorter answers (1-2 sentences, less filler) and query-biasing toward Turing's own docs (added previous round). All 28 now correctly retrieve from `~/Documents/Code/turing/` sources, the wrong-source problem from round 1 is fully fixed.

**Score: ~10/28 clean, ~8/28 partially right, ~10/28 wrong.** Roughly flat vs round 1's ~14/28 looser count, prompt-tuning alone has hit diminishing returns. One new failure mode appeared: confident invention of plausible-but-fake specifics (a fake commenter name "@DavidElli", a fake "Unhandled exception" error) even with correct sources in context, small-model generation quality itself is now the bottleneck, not retrieval.

## What's reliably correct now
Identity and architecture questions: what Turing/Samantha are, their relationship, the base model, what data trained it, LoRA definition, what tool runs training, why `run_lora_capped.py` exists. These are exactly the questions a real user would actually ask first.

## What's still wrong
Anything requiring precise recall of a specific fact buried in a longer document (license, exact blocker, exact file names for the loss-chart pipeline) still gets confidently wrong or invented answers, even with the right source in context. This is a generation-quality limit of a 0.5B model summarizing retrieved text, not a retrieval problem anymore.

## Honest conclusion for tonight

This is a real, working, basic RAG-backed assistant for this project's core facts. Not reliable enough yet for anything requiring precision (won't trust it on exact filenames or exact status without checking). Further gains need either a bigger generation model (the actual retrieval and training data work is done) or structured/extractive answering instead of free-form generation for precision-sensitive questions. Stopping tuning passes here, this is the honest stopping point for "basic working LLM."
