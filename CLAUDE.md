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

- `.venv/` holds mlx-lm. `python3 training/prep_data.py` rebuilds `data/train.jsonl`
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
- `training/parse_log.py` regenerates `web/status.json` from `train.log` after every
  run, landing page reads it live (loss chart + roadmap tracker share the
  same file on purpose).
- Landing page: the loop deploys it from this Mac after every release, no asking, no token hunting: `git worktree add --detach /tmp/turing-clean HEAD && (cd /tmp/turing-clean && npx wrangler deploy); git worktree remove --force /tmp/turing-clean`, then check the live `/stats.json` version. Always from a clean HEAD, never the working tree (a builder may have half-done edits there). wrangler's OAuth login on the Mac does the auth. `.github/workflows/deploy.yml` stays as a green no-op until a Workers-scoped CLOUDFLARE_API_TOKEN repo secret exists (the Pages deploy token in secrets.fish cannot deploy Workers; tried 2026-09-25).
- No daemon, no cron, training is invoked by hand every time.
- Layout: her code at the root (ask_*, tools_*, chat, harness, serve, mcp_server, library, voice), `tests/` (every test_*.py, run from the root: `python3 tests/test_x.py`), `training/` (prep_data, distill, gen_hands_data, harvest_voice, run_lora_capped, train_resilient, parse_log, TRAINING_EXAMPLES, TROUBLESHOOTING), `swift/` (ocr, pdf), `eval/`, `pixelmator/`, `gui/`, `menubar/`, `web/`, `docs/` (ARCHITECTURE, ABILITIES, HISTORY, PROGRESS, LOOP-HANDOFF). No loose files at the root: a new script goes in the folder that owns it.

## Talking to Joshua
TLDR only. Every round that ships something adds one line, newest first, to docs/PROGRESS.md, followed by the one-line `python3 eval/scorecard.py` (version, tools, tests, docs, laws, biggest file, router agreement). A few lines at most, plain words, no walls of text, no play-by-play. Only speak up when something is done, broken, or needs him. Every release gets celebrated: one upbeat line to Joshua (and a push notification when he is away) naming what she can do now, and a 🎉 on its line in docs/PROGRESS.md.

## CI
Every check on main and on every PR stays green, including the release and deploy workflows. Check all workflow runs after every push and merge, not just `test`. A check that cannot do its job yet (a missing secret) skips green with a notice, never red. A red check is fixed before anything else.

## File size
No god files. Past about 500 lines a file gets split by what it does, with the old module re-exporting the moved names so nothing that imports it breaks. Targets now: tools_util.py (700), pixelmator/pxm.py (620), tools_logo.py (582), tools.py (546, its regex router and text normalization in tools_routes.py, the organizer/system/dev registration and WRITES/NOT_FOR_MODELS/soundness guard in tools_registry.py, picker and agent in tools_agent.py), web/demo.js, web/samantha.js. Law 8 in eval/laws.py enforces a ceiling (MAX_LINES) on every Python file, CI included; lower it after each split, never raise it. One split per loop round, each behind the full check set.

## Usage
The loop watches Claude usage every round: the session's `rate_limit_info` (from `get_session`) and its running cost. While status is allowed and there is no overage, a round every 15 minutes or so. On overage or any status other than allowed, taper: one round an hour, CI checks and red fixes only, until the window resets. Say so in one line when tapering.

## Branches
Work happens on main, no side branches and no PRs for Joshua to handle. Before every push, run the full CI check set locally (every test file, `tools.py`, `tools_util.py`, eval/actions.py, eval/web_parity.py, eval/util_diff.py, eval/laws.py, `stats.py --check`); push only when all pass. After the push, check every workflow run (test, release, deploy) and fix any red at once.

## Releases
Releases cut themselves. Bump `VERSION` (patch for a fix, minor for a new ability, major when a whole roadmap family or phase completes: the files family's write half is 4.0.0), run `python3 stats.py` to refresh `web/stats.json`, and commit as `Release vX.Y.Z: what shipped`. When that lands on main and CI passes, `.github/workflows/release.yml` tags it and publishes the GitHub release. Nobody runs anything by hand. `./release.sh X.Y.Z "what shipped"` on the Mac still adds the full gate (her real model, the image tools through ImageMagick, the live page) and the site deploy, whenever the Mac is used. Never leave a day's work untagged: on 2026-09-21 76 commits piled up past v0.7.4 before anyone noticed.

## After every ship
Update together, in the same pass: the landing page (abilities text and the demo), README, WHITEPAPER.md (at every minor or major release: version line, what she can do, the measured numbers, limits, in plain words anyone can read), this file, `docs/ARCHITECTURE.md` (a row for every new file, checked by `eval/laws.py`), `architecture.svg` (the `architecture-svg` skill) and `progress.svg` (`python3 ~/Documents/Code/scripts/progress-svg.py .`, which reports files ARCHITECTURE.md does not name, and must say 100 percent documented). Docs coverage stays at 100 in the gate.
Every minor or major release also refreshes the footer badge (`web/badge.svg`, her engraved SAMANTHA / TURING medallion): `python3 tools_badge.py --version X.Y.Z` rebuilds it from the original (`art/badge-source.svg`, never edited) plus every motif in its MOTIFS table up to that version's step: each minor adds a little more sky around her (4.8 was three constellations and loose stars), thin strokes in her own ink, in open field, never over her or the words, no blur. Joshua loves this logo: each step is small and tells her story, never a redesign. Design the new step's motif, look at it at 2x, send him the before and after, then ship; it only ships when OCR still reads both words.

## The gate
`./gate.sh` runs the docs-coverage rule, then four fast checks (chat, actions, parity, tools) and compares against eval/baseline.json. `./gate.sh --full` also runs hands.py and the live web demo. Release.sh runs the full gate, so a release cannot ship on a worse number. Use `./gate.sh --update-baseline` to set new baselines only when all checks pass.

## Tools and the harness
`tools.py` is the router and the first 30 tools. `tools_util.py` adds 49 utilities and `ask_llm` (from `tools_llm.py`, a hard question for another LLM on this Mac, by name or the biggest, oMLX then Ollama, no key: only by name, asks first, hidden from models and MCP) (math, time, dates, chance, text, this Mac's vitals, Shortcuts) and their `ROUTES` table, which `tools.py` appends. Every one has a JavaScript twin in `web/samantha.js`, generated from the same table; `eval/util_diff.py` diffs the two word for word and must stay green. A new tool needs: the function with a docstring, a route, the JS route (regenerate the block from the Python table), a case in `eval/util_diff.py`, and its row in `docs/ARCHITECTURE.md`. The trained picker only knows the first 30 tools; new ones work through the router until it is retrained. The image tools have exact routes too (`tools_image.ROUTES`, ahead of the utilities so "convert cat.png to jpg" is never a unit conversion). `tools_research.py` is deep research (Wikipedia, library, notes, a cited brief from the local 9B, unsupported sentences dropped). `tools_see.py` is her eyes (see_screen, see_image: Qwen2.5-VL 3B via mlx-vlm, private, asked first). `tools_gui.py` is her hands on the screen (click_text finds words with ocr.swift --boxes and clicks with cliclick; type_text; press_key; all WRITES). `voice.py` is voice in (`chat.py --voice`: sox records, Whisper on MLX transcribes, the harness answers, `say` speaks). `library.py` is her offline library (Wikipedia's vital articles and the fieldbook in SQLite FTS5 at ~/.samantha/library); `general_knowledge` falls back to it last, and it declines anything a page does not cover. A tool that breaks, or a missing answer model, is a reply in chat, never a crash: `harness.Session.ask`, `ask.local_answer` and `chat.safe_turn` catch it.
Anything that writes, sends or leaves a file goes in `tools.WRITES` and asks first through `harness.py`. Tools that fire a side effect nobody sees coming (`NOT_FOR_MODELS`) never reach a model's menu and are not served over MCP (`mcp_server.py`).
The landing demo draws anything: `/api/draw` in `worker.js` runs an image model on Workers AI (5 a minute per visitor, cached a day), and `web/paint.js` rebuilds the picture from 30,000 squares. `eval/web_demo.py` covers it live.
Logos: `make_logo` always makes an icon, never text. Three modes: golden spiral (the default; her model picks palette, cell count, shape and how many glow), complex (say "complex"), and simple (say "simple" or "minimal": ring, spark, bars or dot). The spiral has two styles: spiral (open cells) and flower (packed petals round one bright core, reads at 16px). Her model picks the dials, `tools_logo.py` lays out the layers and draws them straight to a PNG with ImageMagick (`-draw` MVG: `roundRectangle`, `ellipse`, `polygon` for stars), no Pixelmator anywhere in the path; the old Pixelmator spec at `pixelmator/examples/turing-flower.json` is history now, kept for reference only. The icon (`web/icon.svg`, `icon.svg`, `web/samantha-logo.png`) is her flower: `tools_logo.icon_svg()` rebuilds it byte for byte and `test_edges.py` fails if anyone hand-edits it. `tools_logo.layers_to_svg` draws any of her designs as an SVG, no ImageMagick needed either. `docs/icon-blueprint.svg` is generated by `tools_logo.icon_blueprint_svg()` and pinned by a test, as are the measured rules: mark 70 to 80 percent of the tile, dark ring at least a pixel at 16px, core and petals at least 7:1 on the tile.
Painting: `pixelmator/pxm.py paint --engine magick` draws the quadtree with ImageMagick in about a second for 40,000 squares; `paint_image` calls only that engine, never Pixelmator. The Pixelmator AppleScript engine still lives in `pixelmator/pxm.py` (`--engine pixelmator`) as an opt-in path nothing here calls by default.

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

## Before you push

Run `git config core.hooksPath .githooks` once per clone. The pre-push hook runs the same steps CI does, so a red build never reaches GitHub. Every worktree inherits it.
