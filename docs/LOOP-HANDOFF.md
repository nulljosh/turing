# Turing loop handoff (2026-10-18, late morning)

## What the loop is

A self-paced `/loop` that climbs the roadmap one earned major at a time: 7.0, 8.0, 9.0, 10.0. It runs inside a Claude Code session, wakes every 20 to 30 minutes, ships one small slice per wake, and goes quiet when there is nothing safe to do. It never uses cron, launchd or a cloud routine. The Mac stays awake because Amphetamine is holding it.

A major ships only when its roadmap family is finished and checked: the badge step, the whitepaper, the Hugging Face card. A number is never bumped to hit a target. 10.0 inside a week is a stretch goal, not a promise: 7.0 and 8.0 are realistic, 9.0 and 10.0 are each a week or more of work.

## Where things stand

- **Live:** v7.10.0 on turing.jaybulb.com (confirmed on /stats.json after the 18:08 UTC deploy). It adds convert_3d, which converts glb, gltf, obj, stl, ply and fbx through headless Blender, asks first and never overwrites. 153 tools, 890 tests. Before it, v7.9.1 put the engraved harbour footer on the landing page (the shader is ported from Atlin's).
- **Test run:** the post-deploy test run for the handoff commit (137456f) was still going at checkpoint; the release and deploy for v7.10.0 were green.
- **Shipped before that:** v7.9.0 notes every command she could not do in ~/.samantha/misses.jsonl for the teacher (the file is still empty). v7.8.0 adds check_page, a read-only page checker. v7.7.0 rebuilt the face as Samantha Sans on Inter (OFL kept), with one terracotta accent (#b5502c light, #e0825a dark) and gibberish as a decline again. v7.6.1 fixed how BFCL strings are scored: her picker passes 325 of 400 (81.3 percent) on the function-calling benchmark in eval/bfcl.py. v7.5.0 added video_info, trim_video and vertical_video through ffmpeg.
- **Roadmap:** docs/roadmap.md, which the checkpoint's issue sync reads. Issue #107 (Blender family) stays open for "a simple 3D object" and "a logo as 3D text".
- **Joshua Tree 10.0 (the picker in C):** PR 596 (3.9.2, the small picker leaves its own topics alone) is merged on GitHub, dated 2026-10-13. The 10.0 tag still needs the docs and whitepaper refresh and Joshua's real-mic test. Caveat to say every time: the chat rows were written after reading the dev sets' mistakes, so the numbers are tuned to dev; the sealed sets are unread.
- **8.0 picker rounds are at the noise floor:** run 23 stays shipped. A retrain moves about 25 of 4,455 pooled rows by itself, and the leftover mistakes are 3 or 4 rows each. Only a new idea (relabeled dev sets, a different model) restarts 8.0.
- **9.0 is Joshua's:** it needs his signed iPhone build and the Yeti mic; nothing to build until then except what he asks for.
- **Pi shell:** the boot-to-shell flip (docs/PI.md) still waits for Joshua's go-ahead.
- **Disk:** 11Gi free on the internal drive. Other sessions' builds eat it; only clean what this session made.
- **Room benchmark (side work, done):** ~/Documents/room-bench, not a git repo, private photos, never commit or copy them. Final scores out of 100 (rubric v2, which rewards listing objects, so the eye decides): Sonnet 99.3, Opus 97.3, Fable 97.3 (best by eye), Haiku 94.0, Samantha 51.1. Samantha's 9B cannot hold her own previous file inside oMLX's memory ceiling, so each self-fix round was a rewrite. COMPARISON.md there has the write-up.
- **Sealed sets** heldout4, heldout7 and heldout12 are read as counts only, never as text.

## Next, in order

1. Teach from her misses (every wake, step 6). misses.jsonl is empty so far; when it has rows, they are the first thing the next picker round trains on.
2. Blender family (#107): convert_3d and make_3d (simple shapes) are done. Next a logo as 3D text. Check each with a real Blender round trip, read back by blender_info.
3. 8.0 picker: the bar is unchanged. Round 25 tries weighting the teacher and miss rows, or teaching only the tools the dev sets miss, everything else equal.
4. Audio (Yeti record, transcribe, file to the vault) waits on Joshua clicking the microphone prompt once.

## The ladder

**7.0, remembers and comes to you. Shipped 2026-10-12.** Left over for Joshua: the iPhone reading the iCloud copy needs an iCloud entitlement and a signed build.

**8.0, learns from the big ones.** Distillation: a frontier model writes the hard cases and she learns them. The bar, set before any run so it cannot be bent after: on the sealed heldout12, read once as counts, right picks go above run 19's 801 of 869 pooled rate, right picks refused fall below 2 percent (run 19: 40 of 869, 4.6 percent), and wrong picks past the guard stay at or under 19. Slices, one per wake, sealed sets never read as text:
1. Done 2026-10-12 on dev set heldout2 (the 844 MB picker fits in free memory): 452 of 500, 15 wrong picks, 7 past the guard, 6 right picks refused (1.9 percent), and the misses are single cases with no common cause (a book-a-call phrasing, "how far away is halloween", "whats inside notes.md"). The sealed refusal rate is higher (4.6 percent) because nobody tuned to those sentences, so the lever is breadth of fresh phrasings across every picker-eligible tool, not a patch for one cause.
2. Teacher data: write fresh, messy phrasings for every tool a model may pick (not NOT_FOR_MODELS), about 25 tools and 150 rows per wake, as {"text","tool","arg"} batches in the scratchpad, then `training/extra_to_data.py BATCH --out OUT.jsonl` drops anything an eval owns, any tool-name echo and any argument the guard would not run. Never read a sealed set; never copy test phrasing.
3. Round 24 (Kaggle v24, 2026-10-12) was rejected: heldout2 dev 445 of 500 against the shipped 452, one more wrong pick past the guard, same refusals. The flat teacher batch did not help; the next round should try weighting the teacher rows, or teaching only the tools the dev sets miss, and keep everything else equal. Round 24 on Kaggle (docs/KAGGLE.md, 1.5B, in-kernel SFT then gentle DPO), then eval/picker_round.sh against dev sets; reject any run that leaks more.
4. Read heldout12 once, as counts. If the bar is met: ship the picker, whitepaper, HF card with `--model`, 8.0.0. If not, say so and keep the rounds going; never move the bar.
Check the free memory before any local model run and never run two at once.
Anything over a gigabyte (Kaggle outputs are about 6 GB, merged models 3 GB) goes to /Volumes/LaCie/turing-scratch, never the internal disk, which is at about 11 GB free. Only the converted 844 MB MLX picker may land on the internal disk, and only to be scored.

**9.0, in your pocket.** The iPhone as a thin client to the Mac over his own network, voice first. Needs a signed device build and the Yeti mic (the Mac mini has none). Joshua-gated.

**10.0, her own home.** Her picker in freestanding C on the Joshua Tree kernel, checked in QEMU with the network off. Joshua Tree repo, branches and PRs, draft until ci-local is green.

The 10.0 bar, written 2026-10-12 before any measurement. A 1.5B model cannot run in the i386 kernel, so what ships is a small picker distilled from her: integer-only weights trained on training rows alone (never a dev or sealed row), run by freestanding C. It earns the name "her picker in C" only if all three hold. (1) Parity: the C picks match the Python reference on every golden sentence, 100 percent, checked headless in QEMU with the network off (`-nic none`), the check failing when the C is reverted. (2) Accuracy: on the pooled nine dev sets (4,455 rows) the tool-level right rate is at least 80 percent (3,564 rows), reported next to run 23's 4,052. Arguments stay with the guarded path, only the tool is picked. (3) Safety: a sentence the reference calls out of scope (tool null) is never turned into a tool call at a higher rate than run 23 manages, reported as counts. If a bar is missed, say so and keep the name "small picker"; never move the bar. Slices: a Python reference and its dev score, the C port with its QEMU check, then the Joshua Tree shell command and docs. Joshua Tree work goes in a worktree off fresh origin/main (no "samantha" in the path), a branch and a draft PR, ci-local green before ready.

10.0 slice 1 done 2026-10-12: Joshua Tree PR 577 (draft, 3.8.0). Python reference `training/smallpicker/ref.py` (hashed words and letter triples, 2048 buckets, margin perceptron, int8 weights pruned to 15,571, 119 classes) scores 3,820 of 4,455 tool picks on the nine dev sets, 85.8 percent against the 80 percent bar (run 23, tool and argument together, got 4,052). The C in `kernel/picker.c` matches it on all 297 golden sentences in QEMU with `-nic none`, and the check fails when the C is changed. It costs about 57KB of the kernel's room (30KB left). Merged as 3.8.0 (PR 577, ci-local green). The safety bar (3) is MISSED: on the 434 not-a-command rows in dev sets heldout, 2, 3 and 5 the small picker makes a tool call on 115 (26 percent) against run 23's 22 (5 percent), so it stays "a small picker distilled from her", not "her picker". Next slice: teach it to abstain (a null margin tuned on training rows only, or more not-a-command rows in training), re-measure the three bars, keep the 80 percent right-rate. The 10.0 tag waits on the whole family.

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
6. Teach her what she missed: if `~/.samantha/misses.jsonl` or `~/.samantha/feedback.jsonl` grew since the last wake, label each new line as {"text","tool","arg"} (the tool she should have used, or null when no tool fits) into a scratchpad batch, run `training/extra_to_data.py BATCH --out training/teacher_batches/misses-DATE.jsonl`, and log the count here. Never label a sealed or dev-set phrasing. This is the recursive half of 8.0: her own misses become the next round's rows.
7. Rewrite "Where things stand" and "Next, in order" in this file so a fresh session can pick up cold.
8. One line to Joshua only when something shipped, broke, or needs him.

## Hard-won rules

- A Kaggle output download of the 3 GB model breaks with IncompleteRead about half the time. Fetch only the merged model, in a retry loop: `uvx kaggle kernels output OWNER/KERNEL -p DIR -o -q --file-pattern 'hands-merged/'`, up to six tries with a 20 second sleep, and trust only "DL rc=0" plus a 3.1 GB `model.safetensors`.
- Compare rounds on the pooled nine dev sets, never one set, and treat anything under about 25 rows as noise. Never read a sealed set to break a tie.
- Joshua Tree PRs: work in a worktree off fresh `origin/main` (no "samantha" in the path); `VERSION`, `landing/version.txt` and `landing/index.html` conflict on every main move, so take main's side and set the new number; regenerate `docs/TESTING.md` with `tools/gen/testing-doc.py`; new check scripts use `mktemp -d`, never a fixed /tmp path (tmp-paths-check); every new source file gets an ARCHITECTURE row; `git push` runs a fast hook only, `tools/ci-local.sh` must pass before `gh pr ready`.
- Before `ci-local`, run `pgrep -fl "ci-suite|ci-local|qemu-system"`. Another session's QEMU is not mine: never kill it. If it is there and Joshua says hurry, run anyway and rerun only a shard that fails; kill only processes whose cwd is my own worktree.
- Python in a pipeline: write results to a file; numpy in-place masking through the builtin `abs()` once flipped signs silently, so use `np.where(np.abs(x) < t, 0, x)`.
- The kernel's room is shared: `tools/checks/bss-margin-check.py` wants 16KB free. The picker may use about 40KB of it; say the number in the PR.
- When a major bar is missed, write the miss in this file the same day. Never move a bar after a measurement.

## Needs Joshua

- Clicking any macOS permission prompt (she never does).
- The Pi shell flip, and a Pi re-test after it.
- iCloud entitlement, signed device build, App Store submission at $1 (name through the asc-name-creator skill, privacy URL, age rating, review notes).
- Anything that spends money or posts publicly.

## Restart prompt

```
/loop until v10, then keep going toward v100, overnight and all week: read docs/LOOP-HANDOFF.md first and follow its ladder, pace, wake steps and hard-won rules. On every wake start with the usage line, then the state of open PRs and runs, then do exactly one slice and log it. Versions are earned: a major only when a roadmap family or phase completes and its written bar is met, never bumped to hit a number, never move a bar after measuring. Gate every push on exit codes and ci-local before a Joshua Tree PR leaves draft. Keep replies to Joshua to two lines. If nothing is safe to do, say so in one line and sleep 30 minutes; re-arm every time. Hard stop and /checkpoint at 90 percent usage. Never weaken a guard, never kill a process she did not start, never print a token.
```
