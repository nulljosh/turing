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
- Landing page deploys itself: `.github/workflows/deploy.yml` runs `wrangler deploy`
  (Workers assets, not Pages, matches weather/keyrate) after CI passes on main, then
  checks the live page serves the new VERSION. `web/` is the asset root. Needs the
  CLOUDFLARE_API_TOKEN repo secret; `npx wrangler deploy` from the Mac still works.
- No daemon, no cron, training is invoked by hand every time.

## Talking to Joshua
TLDR only. A few lines at most, plain words, no walls of text, no play-by-play. Only speak up when something is done, broken, or needs him.

## CI
Every check on main and on every PR stays green, including the release and deploy workflows. Check all workflow runs after every push and merge, not just `test`. A check that cannot do its job yet (a missing secret) skips green with a notice, never red. A red check is fixed before anything else.

## File size
No god files. Past about 500 lines a file gets split by what it does, with the old module re-exporting the moved names so nothing that imports it breaks. Targets now: ask.py, tools_util.py, tools.py, web/demo.js, web/samantha.js. One split per loop round, each behind the full check set.

## Pull requests
Claude handles its own PRs end to end: open one only when it will be merged, never leave one for the user to handle. Once CI passes on the head commit, merge it right away (merge commit), then restart the working branch from the new main. A red CI is fixed and re-pushed, not handed back.

## Releases
Releases cut themselves. Bump `VERSION` (patch for a fix, minor for a new ability), run `python3 stats.py` to refresh `web/stats.json`, and commit as `Release vX.Y.Z: what shipped`. When that lands on main and CI passes, `.github/workflows/release.yml` tags it and publishes the GitHub release. Nobody runs anything by hand. `./release.sh X.Y.Z "what shipped"` on the Mac still adds the full gate (her real model, Pixelmator, the live page) and the site deploy, whenever the Mac is used. Never leave a day's work untagged: on 2026-09-21 76 commits piled up past v0.7.4 before anyone noticed.

## After every ship
Update together, in the same pass: the landing page (abilities text and the demo), README, this file, `docs/ARCHITECTURE.md` (a row for every new file, checked by `eval/laws.py`), `architecture.svg` (the `architecture-svg` skill) and `progress.svg` (`python3 ~/Documents/Code/scripts/progress-svg.py .`, which reports files ARCHITECTURE.md does not name, and must say 100 percent documented). Docs coverage stays at 100 in the gate.

## The gate
`./gate.sh` runs the docs-coverage rule, then five fast checks (chat, actions, parity, pixelmator, tools) and compares against eval/baseline.json. `./gate.sh --full` also runs hands.py and the live web demo. Release.sh runs the full gate, so a release cannot ship on a worse number. Use `./gate.sh --update-baseline` to set new baselines only when all checks pass.

## Tools and the harness
`tools.py` is the router and the first 30 tools. `tools_util.py` adds 48 utilities (math, time, dates, chance, text, this Mac's vitals, Shortcuts) and their `ROUTES` table, which `tools.py` appends. Every one has a JavaScript twin in `web/samantha.js`, generated from the same table; `eval/util_diff.py` diffs the two word for word and must stay green. A new tool needs: the function with a docstring, a route, the JS route (regenerate the block from the Python table), a case in `eval/util_diff.py`, and its row in `docs/ARCHITECTURE.md`. The trained picker only knows the first 30 tools; new ones work through the router until it is retrained. The image tools have exact routes too (`tools_image.ROUTES`, ahead of the utilities so "convert cat.png to jpg" is never a unit conversion). A tool that breaks, or a missing answer model, is a reply in chat, never a crash: `harness.Session.ask`, `ask.local_answer` and `chat.safe_turn` catch it.
Anything that writes, sends or leaves a file goes in `tools.WRITES` and asks first through `harness.py`. Tools that fire a side effect nobody sees coming (`NOT_FOR_MODELS`) never reach a model's menu and are not served over MCP (`mcp_server.py`).
The landing demo draws anything: `/api/draw` in `worker.js` runs an image model on Workers AI (5 a minute per visitor, cached a day), and `web/paint.js` rebuilds the picture from 30,000 squares. `eval/web_demo.py` covers it live.
Logos: `make_logo` always makes an icon, never text. Three modes: golden spiral (the default; her model picks palette, cell count, shape and how many glow), complex (say "complex"), and simple (say "simple" or "minimal": ring, spark, bars or dot). The icon in `web/icon.svg` came from the spiral; rebuild it from `pixelmator/examples/turing-bloom.json`.
Painting: `pixelmator/pxm.py paint --engine magick` draws the quadtree with ImageMagick in about a second for 40,000 squares; `paint_image` uses it and falls back to Pixelmator. Merging every 500 layers keeps the Pixelmator engine linear.

## Laws
`LAWS.md` lists the rules the repo never breaks and `eval/laws.py` checks them against every tool. The gate and CI run it first. A new tool that leaves a mark goes in `WRITES` or `NOT_FOR_MODELS`, and `eval/laws.py` fails until it is classified.

## Accessibility
`eval/a11y.py` runs axe-core against the live page in desktop, phone, light and dark, and `./gate.sh --full` fails on any violation. Keep a `<main>`, a skip link, text at 4.5:1 contrast, 44px tap targets and visible focus. Dog food it after any landing change.

## Docs rule
100 percent of functions and classes have a docstring, in the top folder, `eval/` and `pixelmator/`. `python3 stats.py --check` fails otherwise, `./gate.sh` runs it first and CI runs it. Nothing gets pushed under 100.

## Design system
The landing page's tokens live at the top of `web/index.html`. True white in light mode, true black in dark. One accent, ember (`--ember` #E8A96A), lifted from her icon. Decor uses `--ember`, text uses `--ember-ink` so it stays readable in both themes. Ember goes on heading dots, link underlines, the slider and the "now" bars. The Send button is neutral, solid text color on the page color, so it is black in light mode and white in dark mode. Nothing else gets color. No gradients, no second accent. Radius and spacing come from `--r-*` and `--s-*`.
Page order is demo, what she can do, results, chart. Long text sits inside `details.more` so the page stays visual. Every section keeps its `<h2>`, because her page-control demo finds sections by heading. Results tiles read `stats.json`, never hardcode them.

## The loop
`docs/LOOP-HANDOFF.md` holds the live `/loop`: what it is, where things stand, what is next, and the restart prompt. Checkpoint rewrites it. Read it before resuming.
