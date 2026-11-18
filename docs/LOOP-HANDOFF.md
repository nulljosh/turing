# Turing loop handoff (2026-11-18, morning)

## What the loop is

A self-paced `/loop` that works down the work list in this file, one small slice per wake, and goes quiet when there is nothing safe to do. It runs inside a Claude Code session, wakes every 20 to 30 minutes, and never uses cron, launchd or a cloud routine. The Mac stays awake because Amphetamine is holding it.

Every tick tests security, reliability, performance, stability and efficiency. A slice is not done until those five reach A+. "Fully shipped" means the tag, the GitHub release, the deploy and a live check.

The loop runs to the end of the work list, never to a version number. A version ships when its work is finished and checked. A number is never bumped to hit a target, and a bar never moves after a measurement.

## Where things stand

- **Live:** v8.0.0 (2026-11-18): run 29 is the picker (nightly Qwen2.5-1.5B), the 7.27 guard refuses half as many right picks, sealed heldout15 read once and passed all three 8.0 bars. heldout12 and heldout15 are both spent; the next major needs a fresh sealed set. run 23 is kept at models/run23-mlx.
- **Video abilities: done.** compress_video (7.24.0), still_frame (7.25.0) and add_music (7.26.0). The roadmap's video track is closed.
- **Landing:** the trailer plays full-bleed behind the headline, with a Sound on button and her command bar at the bottom. Scrolling no longer kills the live demo on iPhone. The colour glow, the old "Watch her work" video and the "What she can do" list are gone. Three real dithered screenshots replace the Ada portrait. The README shows the new logo.
- **Docs:** 7 files in docs/ (ARCHITECTURE, TRAINING, SAFETY, FAQ, roadmap, PROGRESS, LOOP-HANDOFF). README and CLAUDE.md are a page each.
- **Trailer:** 30 seconds, 13 real things she did on this Mac, voiced in her own ElevenLabs voice. It shows no desktop test files and it boots Joshua Tree.
- **Versioning (Joshua's rule):** a landing change is a patch. Only a new ability gets a minor.
- **Releases:** v7.23.2 is the latest tag and release. No tag or GitHub release exists yet for v7.24.0, v7.25.0 or v7.25.1, and v7.26.0 and v7.26.1 have none either. Commit 3d9d02f is titled "Release v7.24.0" but it is the 7.25.0 change (still_frame).
- **Training runs without Claude:** `.github/workflows/train.yml` and `training/kaggle/nightly.py` run every 8 hours. Training is bf16 or fp32 only, and a round stops at the first NaN. The log goes to the `train-log` branch on origin (c9c6f9e). The latest round, Qwen3.5-2B, finished 2026-11-17 17:38 and scored 97.5% on its own 200-row check (sft and dpo both 97.5). It has not been compared with run 23 on the pooled dev sets.
- **Picker:** run 23 (4,052 of 4,455 pooled dev rows right) is still the shipped picker. Rounds 27 and 28 did not clearly beat it.
- **10.0 slice 1 is merged** (3.8.0, PR 577). The Python reference and kernel/picker.c match on all 297 golden sentences. The safety bar is missed: the small picker calls a tool on 26 percent of not-a-command rows, where run 23 manages 5 percent. It stays "a small picker distilled from her".
- **Joshua Tree 10.0 tag** still needs the docs and whitepaper refresh and Joshua's real-mic test.
- **Disk:** df read 34 GB available on the internal disk at the 2026-11-17 checkpoint. Check before any download over a gigabyte.
- **LaCie is gone.** The 9B model and the data on it are lost until a new drive. Sealed heldout7 is lost. heldout12 is still in eval/.
- **Roadmap:** docs/roadmap.md, 30 open items. Issues are in sync (issue #107 stays open for the Blender family).

## Next, in order

1. Done 2026-11-18: releases and tags exist for 7.24.0 to 7.26.1. (Was: backfill the GitHub releases and tags for v7.24.0 (commit 216280a) and v7.25.0 (commit 3d9d02f). If release.yml skipped them, create them by hand, then check v7.25.1, v7.26.0 and v7.26.1 the same way.
2. Done 2026-11-18: the nightly Qwen2.5-1.5B round beat run 23 on every pooled dev count (4069/168/83/117), then missed the 8.0 bar on sealed heldout12 (91.1 percent right, 9.3 percent refused). heldout12 is spent; write a fresh sealed set before the next 8.0 attempt and attack guard refusals first. (Was: score the Kaggle rounds logged on the `train-log` branch (eval/kaggle-nightly.log) against run 23 on the pooled nine dev sets. Start with the 2026-11-17 Qwen3.5-2B round. Report the pooled right, wrong, past-guard and refused counts next to run 23's, and never read a sealed set to break a tie.
3. Add a short video card per ability to the landing, only if the trailer alone does not carry compress, still frame and add music.
4. Keep at least 20 GB free on the internal disk. It read 34 GB at the checkpoint, so re-check before a large download.

## The ladder

**7.0, remembers and comes to you. Shipped 2026-10-12.** Left over for Joshua: the iPhone reading the iCloud copy needs an iCloud entitlement and a signed build.

**8.0, learns from the big ones.** Distillation: a frontier model writes the hard cases and she learns them. The bar was set before any run and cannot be bent after: on the sealed heldout12, read once as counts, right picks go above run 19's 801 of 869 pooled rate, right picks refused fall below 2 percent (run 19: 4.6 percent), and wrong picks past the guard stay at or under 19. Work for 8.0 is the Kaggle rounds in item 2 above, the teacher batches for every tool a model may pick (`training/extra_to_data.py`, never a sealed or dev phrasing), and her own misses (`~/.samantha/misses.jsonl`) labelled into rows each wake. Check free memory before any local model run and never run two at once.

**9.0, in your pocket.** The iPhone as a thin client to the Mac over his own network, voice first. Needs a signed device build and the Yeti mic. Joshua-gated.

**10.0, her own home.** A small picker in freestanding C on the Joshua Tree kernel, checked in QEMU with the network off. The three bars were written before any measurement: (1) parity, the C picks match the Python reference on every golden sentence; (2) accuracy, at least 80 percent tool-level right on the pooled nine dev sets (4,455 rows), reported next to run 23's 4,052; (3) safety, a sentence the reference calls out of scope is never turned into a tool call at a higher rate than run 23, reported as counts. If a bar is missed, say so and keep the name "small picker". Next slice: teach it to abstain, re-measure all three bars, keep the 80 percent right rate. Joshua Tree work goes in a worktree off fresh origin/main, a branch and a draft PR, with ci-local green before ready.

## Pace and stops

- Usage is read at the top of every wake with `~/.claude/scripts/usage.sh`.
- Under 80 percent weekly: a wake every 20 to 30 minutes, one slice per wake.
- 80 to 84 percent: one wake an hour, CI fixes and checks only.
- 85 percent weekly: stop the loop, run /save, and never go past it.
- One Haiku subagent at a time, never a fan-out, and only for a slice that is code. The main session plans and merges.
- A wake with nothing to do says so in one line and sleeps longer. Nothing is invented to look busy.

## Every wake

1. `git pull --rebase`, then `gh run list`. Any red check is fixed before anything else.
2. Read the usage line and pick the pace above.
3. Take the next item from "Next, in order", then the next ladder slice. Build it in the smallest slice that ships.
4. Gate every push on exit codes, with `./.venv/bin/python` (the shell's python3 is 3.9). Write python output to a file, never through grep.
5. Test the slice on the five bars and log the grade. A bar below A+ is the next slice.
6. Commit by exact path, push, then check every workflow run (test, release, deploy) and the live `/stats.json`.
7. Teach her what she missed: if `~/.samantha/misses.jsonl` or `~/.samantha/feedback.jsonl` grew since the last wake, label each new line as {"text","tool","arg"} in a scratchpad batch, run `training/extra_to_data.py BATCH --out training/teacher_batches/misses-DATE.jsonl`, and log the count here. Never label a sealed or dev-set phrasing.
8. Rewrite "Where things stand" and "Next, in order" in this file so a fresh session can pick up cold.
9. One line to Joshua only when something shipped, broke, or needs him.

## Hard-won rules

- A Kaggle output download of the 3 GB model breaks with IncompleteRead about half the time. Fetch only the merged model, in a retry loop: `uvx kaggle kernels output OWNER/KERNEL -p DIR -o -q --file-pattern 'hands-merged/'`, up to six tries with a 20 second sleep, and trust only "DL rc=0" plus a 3.1 GB `model.safetensors`.
- Compare rounds on the pooled nine dev sets, never one set, and treat anything under about 25 rows as noise.
- Joshua Tree PRs: work in a worktree off fresh `origin/main` (no "samantha" in the path). `VERSION`, `landing/version.txt` and `landing/index.html` conflict on every main move, so take main's side and set the new number. Regenerate `docs/TESTING.md` with `tools/gen/testing-doc.py`. New check scripts use `mktemp -d`, never a fixed /tmp path. Every new source file gets an ARCHITECTURE row. `tools/ci-local.sh` must pass before `gh pr ready`.
- Before `ci-local`, run `pgrep -fl "ci-suite|ci-local|qemu-system"`. Another session's QEMU is not mine: never kill it. Kill only processes whose cwd is my own worktree.
- Python in a pipeline: write results to a file. numpy in-place masking through the builtin `abs()` once flipped signs silently, so use `np.where(np.abs(x) < t, 0, x)`.
- The kernel's room is shared: `tools/checks/bss-margin-check.py` wants 16KB free. The picker may use about 40KB of it; say the number in the PR.
- When a bar is missed, write the miss in this file the same day. Never move a bar after a measurement.

## Needs Joshua

- Clicking any macOS permission prompt (she never does).
- The Pi shell flip, and a Pi re-test after it.
- iCloud entitlement, signed device build, App Store submission at $1 (name through the asc-name-creator skill, privacy URL, age rating, review notes).
- A new drive for the LaCie data, if the 9B model is wanted back.
- Anything that spends money or posts publicly.

## Restart prompt

```
/loop Turing toward 8.0, run to the end of the work list in docs/LOOP-HANDOFF.md (never a version target). Each tick QA'd and fully shipped. Stop at 85% weekly usage and /save.
```
