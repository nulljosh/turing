# Turing loop handoff (2026-10-12, early morning)

## What the loop is

A self-paced `/loop` that climbs the roadmap one earned major at a time: 7.0, 8.0, 9.0, 10.0. It runs inside a Claude Code session, wakes every 20 to 30 minutes, ships one small slice per wake, and goes quiet when there is nothing safe to do. It never uses cron, launchd or a cloud routine. The Mac stays awake because Amphetamine is holding it.

A major ships only when its roadmap family is finished and checked: the badge step, the whitepaper, the Hugging Face card. A number is never bumped to hit a target. 10.0 inside a week is a stretch goal, not a promise: 7.0 and 8.0 are realistic, 9.0 and 10.0 are each a week or more of work.

## Where things stand

- **Live:** v6.0.0. Samantha is an app on Joshua Tree on a real Raspberry Pi 4; "write hello world in c and save it as hello.c" wrote JT/HELLO.C on the board. v5.14.0 gave her Samantha Sans. The brand kit is docs/BRAND.md and /brand.html, the site icons are the mascot.
- **Joshua Tree PR 537** (list and read the card) is a draft behind main and needs a rebase by the Joshua Tree session. Do not touch it from here.
- **Pi shell:** the console should boot to zsh or bash with Samantha as a command (docs/PI.md). It changes the words Joshua tests with, so it waits for a go-ahead and lives in the Joshua Tree repo on a branch with a PR.
- **Disk:** about 12 GB free. Other sessions' builds eat it; only clean what this session made.
- **Sealed sets** heldout4, heldout7 and heldout12 are read as counts only, never as text.

## The ladder

**7.0, remembers and comes to you.** Memory read-back (4.19) and the Mac morning brief (5.13.0) are done. Left:
1. Memory audit (done 2026-10-12): the Mac app reads facts back into answers (chat_pipe to chat.py `build_prompt` with `memory_context`); the web demo keeps facts in the browser and deliberately never reads them back on the public page; the iPhone app's read-back is unchecked, so that is the one gap to confirm and close.
2. A Shortcut she writes herself: she drafts it, shows the steps in chat, and only on a yes saves the file and opens it, so Apple's own sheet is the final yes. Never on a timer. New tool, so it needs the route, the JS twin, the util_diff case, the laws entry and the ARCHITECTURE row.
3. Profile and memory in his own iCloud Drive folder, nothing of ours in a cloud. Start with the Mac (plain files under iCloud Drive); iPhone needs an iCloud entitlement and a signed build, which is Joshua's. Sign in with Apple only if a slice truly needs an identity.
4. When all three land: badge step, whitepaper, HF card, celebrate, 7.0.0.

**8.0, learns from the big ones.** Distillation raises the picker and the answers together. Training runs on Kaggle (docs/KAGGLE.md), 20 minutes of GPU per run; run 24 toward heldout12. Ship only if the sealed counts improve (right picks up, wrong past the guard down), read as numbers.

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
