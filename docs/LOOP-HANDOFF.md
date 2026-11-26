# Turing loop handoff (2026-11-26, after v10.0.0)

## What the loop is

A self-paced `/loop` that works down the work list in this file, one small slice per wake, and goes quiet when there is nothing safe to do. It runs inside a Claude Code session, wakes every 20 to 30 minutes, and never uses cron, launchd or a cloud routine. The Mac stays awake because Amphetamine is holding it.

Every tick tests security, reliability, performance, stability and efficiency. A slice is not done until those five reach A+. "Fully shipped" means the tag, the GitHub release, the deploy and a live check.

The loop runs to the end of the work list, never to a version number. A version ships when its work is finished and checked. A number is never bumped to hit a target, and a bar never moves after a measurement.

**Status: stopped.** The last loop goal (v10.0.0, "her own home") was reached on 2026-11-26. Nothing runs until a new `/loop` is started with the restart prompt below.

## Where things stand

- **Live:** v10.0.0 (2026-11-26), tag, GitHub release and deploy green; turing.jaybulb.com/stats.json reports 10.0.0.
- **The picker in v10:** a small picker in freestanding C inside the Joshua Tree kernel. Parity is 297 of 297 with the Python reference, re-checked in QEMU with the network off. Accuracy is 81.2 percent right on 4,455 pooled dev rows (bar 80). False tool calls on not-a-command rows are 2.2 percent (bar: no worse than run 23's 5 percent). All three bars pass. Any new picker claim needs a fresh sealed set, since heldout12 and heldout15 are spent.
- **Icon and landing:** silver aluminum, no terracotta. New Icon Composer icon (graphite round glasses with a spark on silver), new favicons and logo, accent silver in dark mode and graphite in light. The engraved mark generator (`app/tools_logo.py`) puts her drawing on a silver tile.
- **CI:** `app/tools_logo.py` is back under its 650-line cap.
- **Video abilities, docs, trailer:** done as of 7.26. Docs are 7 files in docs/.
- **Training runs without Claude:** `.github/workflows/train.yml` and `training/kaggle/nightly.py` run every 8 hours and log to the `train-log` branch.
- **Disk:** keep at least 20 GB free on the internal disk. Check before any download over a gigabyte.
- **LaCie is gone.** The 9B model and its data are lost until a new drive. Sealed heldout7 is lost.
- **Roadmap:** docs/roadmap.md, 31 open items. Issues are in sync.

## Next, in order

1. **9.0, in your pocket (Joshua-gated).** The iPhone as a thin client to the Mac over his own network, voice first. Needs a signed device build and the Yeti mic. Nothing in this slice runs without him.
2. **Any picker claim (ongoing).** Before saying the picker is better than v10, write a fresh sealed set, written blind by a separate writer who has seen only the tool list, and read it once. Write the bar down before the read.
3. **Keep 20 GB free** on the internal disk. Re-check before a large download.
4. **Joshua's open calls:** lock the public `/api/speak` voice to text Turing's own chat produced (found in the 2026-11-21 security review), and the iCloud entitlement for the iPhone to read the iCloud copy.

## The ladder

**7.0, remembers and comes to you. Shipped 2026-10-12.** Left over for Joshua: the iPhone reading the iCloud copy needs an iCloud entitlement and a signed build.

**8.0, learns from the big ones. Shipped 2026-11-18.** Distillation: a frontier model writes the hard cases and she learns them. Work for later picker rounds is the teacher batches for every tool a model may pick (`training/extra_to_data.py`, never a sealed or dev phrasing), and her own misses (`~/.samantha/misses.jsonl`) labelled into rows. Check free memory before any local model run and never run two at once.

**9.0, in your pocket.** Open. Joshua-gated (see Next, item 1).

**10.0, her own home. Shipped 2026-11-26.** A small picker in freestanding C on the Joshua Tree kernel, checked in QEMU with the network off. The three bars were written before any measurement and all three passed. The numbering skipped 9.0 on purpose, so 9.0 stays open. Joshua Tree work goes in a worktree off fresh origin/main, a branch and a draft PR, with ci-local green before ready.

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
3. Take the next item from "Next, in order". Build it in the smallest slice that ships.
4. Gate every push on exit codes, with `./.venv/bin/python` (the shell's python3 is 3.9). Write python output to a file, never through grep.
5. Test the slice on the five bars and log the grade. A bar below A+ is the next slice.
6. Commit by exact path, push, then check every workflow run (test, release, deploy) and the live `/stats.json`.
7. Teach her what she missed: if `~/.samantha/misses.jsonl` or `~/.samantha/feedback.jsonl` grew since the last wake, label each new line as {"text","tool","arg"} in a scratchpad batch, run `training/extra_to_data.py BATCH --out training/teacher_batches/misses-DATE.jsonl`, and log the count here.
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
- A signed device build and the Yeti mic, for 9.0.
- iCloud entitlement and App Store submission at $1 (name through the asc-name-creator skill, privacy URL, age rating, review notes).
- A new drive for the LaCie data, if the 9B model is wanted back.
- The `/api/speak` lock decision.
- Anything that spends money or posts publicly.

## Restart prompt

```
/loop to next major semver! ultrathink
```
