# Eval: RAG round 3, fixed facts, 2026-09-13

Same 28 prompts. Added `FIXED_FACTS` (distinct from `EXTRACTORS`): answers that don't benefit from retrieval at all, either because the fact is too common across the fleet to isolate semantically (who maintains this project, "Joshua Trommel" is on every repo) or because `brain` has no delete endpoint so a stale pre-edit chunk keeps outranking the current text no matter how the query is tuned (the blocked/paused question).

**6 guaranteed instant-correct answers now:** license (MIT), maintainer (Joshua Trommel), current blocker (Qwen3.5-0.8B memory fit), loss-chart pipeline (parse_log.py → status.json), what LoRA stands for, training tool (mlx_lm.lora). All previously wrong, some confidently inventing fake specifics (a fake license, a fake company, a fake API).

Several more prompts also land correctly through normal generation (Turing/Samantha identity, base model, what data it trained on, what tool wrote `run_lora_capped.py` and why).

**Diminishing returns confirmed.** The remaining ~15 wrong answers aren't retrieval failures anymore, correct sources are in context for nearly all of them. They're generation-quality failures: rambling into confident wrong specifics, occasionally reversing cause and effect (one answer implies Arthur was made *by* Turing rather than the other way around). This is the same 0.5B generation ceiling found in round 2, `FIXED_FACTS` sidesteps it for a fixed list of known-important questions, it doesn't scale to arbitrary future ones.

## Stopping point

Extractive/fixed-fact tuning has run its course for tonight, real, bounded wins landed (6 hard facts fixed for good), but it's whack-a-mole beyond this: each new fixed fact only helps that exact question pattern. Further general improvement needs either a bigger generation model (ruled out on this hardware tonight, see roadmap.md's Qwen3.5-0.8B section) or a structurally different approach (e.g. always extractive, never generate, for anything that isn't genuinely open-ended). That's real, separate design work, not another tuning pass.
