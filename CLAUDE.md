# Turing

Pipeline for building small language models on-device. First model: Samantha-1.
Turing is the project name (fixed), Samantha-1/Samantha-1b are model names (change as
new ones ship), same relationship as Anthropic and Claude.

- `.venv/` holds mlx-lm. `python3 prep_data.py` rebuilds `data/train.jsonl`
  and `data/valid.jsonl` from the Obsidian wiki + fleet READMEs/roadmap.md/
  CLAUDE.md files. Never commit `data/` or `*-adapter/`, they're gitignored
  on purpose (derived from private notes, and just weights).
- `ada-1-adapter/` (Qwen2.5-0.5B) is the real Samantha-1. A second base
  (Qwen3.5-0.8B, `ada-1b-adapter/`) was tried for Phase 3 comparison but
  pushed the machine into near-OOM twice and got paused, this Mac Mini
  is memory-tight (2GB) once a second model download + training pass
  stacks on top of everything else running. Never run two mlx_lm.lora
  jobs at once. Check free memory before starting any run.
- `scratch/` is a second, unrelated track: a genuine from-scratch
  character-level transformer with zero borrowed weights, kept deliberately
  tiny. It will not be fluent. That's the point, it proves we can build one
  from nothing without repeating the earlier Arthur gibberish failure.
- `parse_log.py` regenerates `web/status.json` from `train.log` after every
  run, landing page reads it live (loss chart + roadmap tracker share the
  same file on purpose).
- Landing page deploys via `npx wrangler deploy` (Workers assets, not Pages,
  matches weather/keyrate). `web/` is the asset root.
- No daemon, no cron, training is invoked by hand every time.
