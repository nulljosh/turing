# Turing loop handoff (2026-10-12, 3 a.m.)

## What the loop is

A self-paced `/loop` that climbs the roadmap one earned major at a time: 7.0, 8.0, 9.0, 10.0. It runs inside a Claude Code session, wakes every 20 to 30 minutes, ships one small slice per wake, and goes quiet when there is nothing safe to do. It never uses cron, launchd or a cloud routine. The Mac stays awake because Amphetamine is holding it.

A major ships only when its roadmap family is finished and checked: the badge step, the whitepaper, the Hugging Face card. A number is never bumped to hit a target. 10.0 inside a week is a stretch goal, not a promise: 7.0 and 8.0 are realistic, 9.0 and 10.0 are each a week or more of work.

## Where things stand

- **Live:** v7.0.0, earned. Memory reads back on the Mac and the phone, the Mac morning brief, Shortcuts she writes (6.1), and memory in your own iCloud Drive on request. The Mac app with 7.0 is signed, notarized and uploaded. v6.0.0 put her on a real Pi 4; v5.14.0 gave her Samantha Sans; docs/BRAND.md and /brand.html hold the brand kit.
- **Joshua Tree PR 537** (list and read the card) is a draft behind main and needs a rebase by the Joshua Tree session. Do not touch it from here.
- **Pi shell:** the console should boot to zsh or bash with Samantha as a command (docs/PI.md). It changes the words Joshua tests with, so it waits for a go-ahead and lives in the Joshua Tree repo on a branch with a PR.
- **Disk:** about 12 GB free. Other sessions' builds eat it; only clean what this session made.
- **Sealed sets** heldout4, heldout7 and heldout12 are read as counts only, never as text.

## The ladder

**7.0, remembers and comes to you. Shipped 2026-10-12.** Left over for Joshua: the iPhone reading the iCloud copy needs an iCloud entitlement and a signed build.

**8.0, learns from the big ones.** Distillation: a frontier model writes the hard cases and she learns them. The bar, set before any run so it cannot be bent after: on the sealed heldout12, read once as counts, right picks go above run 19's 801 of 869 pooled rate, right picks refused fall below 2 percent (run 19: 40 of 869, 4.6 percent), and wrong picks past the guard stay at or under 19. Slices, one per wake, sealed sets never read as text:
1. Find the refusals on the dev sets (eval/hands.py on dev only) and group them by cause.
2. Teacher data: write hard, messy rows for those causes in this session (the frontier teacher), 100 to 150 per wake, never copying any test phrasing, into training/ as a new pool.
3. Round 24 on Kaggle (docs/KAGGLE.md, 1.5B, in-kernel SFT then gentle DPO), then eval/picker_round.sh against dev sets; reject any run that leaks more.
4. Read heldout12 once, as counts. If the bar is met: ship the picker, whitepaper, HF card with `--model`, 8.0.0. If not, say so and keep the rounds going; never move the bar.
Check the free memory before any local model run and never run two at once.

**9.0, in your pocket.** The iPhone as a thin client to the Mac over his own network, voice first. Needs a signed device build and the Yeti mic (the Mac mini has none). Joshua-gated.

**10.0, her own home.** Her picker in freestanding C on the Joshua Tree kernel, checked in QEMU with the network off. Joshua Tree repo, branches and PRs, draft until ci-local is green.

## Pace and stops

- Usage is read at the top of every wake with `~/.claude/scripts/usage.sh`. Weekly resets Saturday 22:00. At 59 percent on Monday morning, the budget to the 90 percent stop is about 5 points a day.
- Under 80 percent weekly: a wake every 20 to 30 minutes, one slice per wake.
- 80 to 89 percent: one wake an hour, CI fixes and checks only.
- 90 percent: run `/checkpoint` and stop. Never past it.
- One Haiku subagent at a time, never a fan-out, and only for a slice that is code. Main session plans and merges.
- A wake with nothing to do says so in one line and sleeps longer. Nothing is invented to look busy.

## Every wake

1. `git pull --rebase`, then `gh run list`: any red check is fixed before anything else.
2. Read the usage line and pick the pace above.
3. Take the next ladder item. Build it in the smallest slice that ships.
4. Gate every push on exit codes: `scratchpad/gate.sh` style, the full CI set, with `./.venv/bin/python` (the shell's python3 is 3.9). Write python output to a file, never through grep.
5. Commit by exact path, push, then check every workflow run (test, release, deploy) and the live `/stats.json`.
6. One line to Joshua only when something shipped, broke, or needs him.

## Needs Joshua

- Clicking any macOS permission prompt (she never does).
- The Pi shell flip, and a Pi re-test after it.
- iCloud entitlement, signed device build, App Store submission at $1 (name through the asc-name-creator skill, privacy URL, age rating, review notes).
- Anything that spends money or posts publicly.

## Restart prompt

```
/loop until v10, then keep going toward v100, overnight and all week: read docs/LOOP-HANDOFF.md first and follow its ladder, pace and wake steps. Versions are earned: a major only when a roadmap family or phase completes, never bumped to hit a number. Gate every push on exit codes. Hard stop and /checkpoint at 90 percent usage. Never weaken a guard, never kill a process she did not start.
```
