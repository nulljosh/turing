# Turing

Pipeline for building small language models on-device. First model: Samantha.
Turing is the project name (fixed). Each model release gets its own name,
not a version bump of the last one, same pattern as Claude's model names
(Haiku, Opus, Sonnet, Fable), not "Claude-2/Claude-3". First: Samantha
(the LoRA-on-Qwen2.5-0.5B model). Next release gets a new name, tied to
whatever it's actually built for (a feature set, a personality, a base
model swap), not "Samantha-2". The Qwen3.5-0.8B comparison base, if it
ever ships as its own real model, gets a name of its own too, not a
"-1b" suffix.

- `.venv/` holds mlx-lm. `python3 prep_data.py` rebuilds `data/train.jsonl`
  and `data/valid.jsonl` from the Obsidian wiki + fleet READMEs/roadmap.md/
  CLAUDE.md files. Never commit `data/` or `*-adapter/`, they're gitignored
  on purpose (derived from private notes, and just weights).
- `ada-1-adapter/` (Qwen2.5-0.5B) is the real Samantha. A second base
  (Qwen3.5-0.8B, `ada-1b-adapter/`) was tried for Phase 3 comparison but
  pushed the machine into near-OOM twice and got paused. This Mac Mini
  has 16GB total, but a second model's download plus a training pass,
  stacked on top of everything else running, was enough to drive free
  memory down to a couple GB and crash. Never run two mlx_lm.lora jobs
  at once. Check free memory before starting any run.
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

## Releases
Every shipped ability or fix ends with `./release.sh X.Y.Z "what shipped"`. It runs the checks, bumps `VERSION`, regenerates the landing stats, tags, pushes, publishes the GitHub release and deploys. Patch for a fix, minor for a new ability. Never leave a day's work untagged: on 2026-09-21 76 commits piled up past v0.7.4 before anyone noticed.

## Design system
The landing page's tokens live at the top of `web/index.html`. True white in light mode, true black in dark. One accent, ember (`--ember` #E8A96A), lifted from her icon. Decor uses `--ember`, text uses `--ember-ink` so it stays readable in both themes. Ember goes on heading dots, link underlines, the slider, the Send button and the "now" bars. Nothing else gets color. No gradients, no second accent. Radius and spacing come from `--r-*` and `--s-*`.
Page order is demo, hands, results, chart. Long text sits inside `details.more` so the page stays visual. Every section keeps its `<h2>`, because her page-control demo finds sections by heading. Results tiles read `stats.json`, never hardcode them.

## The loop
`docs/LOOP-HANDOFF.md` holds the live `/loop`: what it is, where things stand, what is next, and the restart prompt. Checkpoint rewrites it. Read it before resuming.
