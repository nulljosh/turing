# Turing

Turing is the project; Samantha is its first model, a small on-device assistant. A future model gets a new name, never "Samantha-2".

## Layout
`app/` her code (router `tools.py`, `tools_*`, `harness.py`, `chat.py`, `voice.py`), `eval/` checks, `scripts/` stats and publishing, `tests/` (`python3 tests/test_x.py` from the root), `training/` data and Kaggle, `web/` the landing (turing.jaybulb.com, `worker.js`), `gui/` the Mac app, `install/` Windows and Linux. Markdown lives in `docs/` (ARCHITECTURE, TRAINING, SAFETY, FAQ, roadmap, PROGRESS, LOOP-HANDOFF). No loose files at the root. Never commit `data/`, `models/` or adapters.

## Talking to Joshua
TLDR only. Speak up when something is done, broken, or needs him. Every shipped round adds one line, newest first, to `docs/PROGRESS.md`, then the `python3 eval/scorecard.py` line.

## Shipping
Work on main. Before a push run every check CI runs (`./gate.sh`, or `git config core.hooksPath .githooks` once so the pre-push hook does it). Semver is honest: patch for a fix or a landing change, minor for a new ability, major when a roadmap family completes. To release: bump `VERSION`, `python3 scripts/stats.py`, PROGRESS line, commit `Release vX.Y.Z: what shipped`. `release.yml` tags it, `deploy.yml` deploys the landing and checks the live `/stats.json` version. Check every workflow after a push; a red check is fixed first. A check that cannot run yet skips green, never red.

## Rules the checks enforce
- `eval/laws.py`: anything that writes, sends or deletes is in `WRITES` and asks first; hidden tools stay in `NOT_FOR_MODELS`; every `app/` and `scripts/` file has a row in `docs/ARCHITECTURE.md`; no em dashes in docs people read; no Python file over `MAX_LINES` (lower it after a split, never raise it).
- `scripts/stats.py --check`: every function and class has a docstring.
- `eval/util_diff.py`: every utility has a matching JavaScript twin in `web/samantha.js`.
- A new tool needs a docstring, a route, its JS twin, a `util_diff` case and its ARCHITECTURE row.
- A broken tool is a reply in chat, never a crash.

## Training
Free GPU on Kaggle, no Claude needed: `.github/workflows/train.yml` runs `training/kaggle/nightly.py` every 8 hours, logging each round to the `train-log` branch. Details in `docs/TRAINING.md`. The token lives in `~/.kaggle/access_token` and the `KAGGLE_API_TOKEN` secret; never print or commit it. Locally, never run two MLX training jobs at once and check free memory first.

## Landing
Tokens at the top of `web/index.html`. One accent, terracotta (#b5502c light, #e0825a dark), no gradients, no yellow. Every section keeps its `<h2>`. Stats come from `stats.json`. `eval/a11y.py` must stay clean. The logo is `web/logo.svg`.

## After a ship
Keep these in step: the landing, README, `docs/TRAINING.md` (at minors), `docs/ARCHITECTURE.md`, and her Hugging Face card (`./scripts/hf_publish.sh`, card at `scripts/hf_card.md`). The Mac download is the permanent `mac-app` release: `./gui/package.sh` then `gh release upload mac-app gui/dist/SamanthaGUI.zip --clobber`.

## The loop
`docs/LOOP-HANDOFF.md` holds the live `/loop` and its restart prompt. Read it before resuming.
