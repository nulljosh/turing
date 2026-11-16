# Turing loop handoff (2026-11-16)

## What the loop is

A self-paced `/loop` that climbs the roadmap one earned major at a time: 8.0 now, then 9.0 and 10.0. It runs inside a Claude Code session, wakes every 20 to 30 minutes, ships one small slice per wake, and goes quiet when there is nothing safe to do. It never uses cron, launchd or a cloud routine. The Mac stays awake because Amphetamine is holding it.

Every tick also tests security, reliability, performance, stability and efficiency. The loop does not call a major done until those five reach A+. "Fully shipped" means the tag, the release, the deploy and a live check.

A major ships only when its roadmap family is finished and checked. A number is never bumped to hit a target, and a bar never moves after a measurement.

## Where things stand

- **Live:** v7.22.3 (on origin/main; CI test run was still in progress at this update), 166 tools. v7.22.3 makes a missing local model a plain reply in write_code and edit_file, never file content.
- **Training runs without Claude:** `.github/workflows/train.yml` plus `training/kaggle/nightly.py` run every 8 hours. Each run logs the finished Kaggle round to `eval/kaggle-nightly.log` and starts the next one, rotating Qwen3.5-2B, Qwen2.5-1.5B and Qwen3.5-0.8B. The KAGGLE_API_TOKEN secret is set and the workflow is green. Next base to add: Gemma 4 E2B.
- **Trailer:** three takes of Samantha driving the real Mac with screen recording. Take 3 was cut and sent to Joshua; not graded yet.
- Previous live: v7.22.2, 166 tools. v7.22.0 added caption_video: an .srt or .vtt beside a video becomes a captions track, nothing burned in (Homebrew's ffmpeg has no libass or drawtext). v7.22.1 fixed the landing chat typing and queues messages behind a Send now button. v7.22.2 brought the footer engraving, the orb logo and the diner painting in the demo reel.
- **Parked:** caption_video writing its own .srt from her Whisper transcript (7.23.0) is uncommitted in the working tree: app/tools_video.py, app/voice.py, tests/test_video.py. It needs one real Whisper run before it ships. Leave those files uncommitted until then. The older copy sits in git stash `caption-transcript`; take it with `git stash apply` by name. Never pop or drop it.
- **Kaggle works again** (password reset and a new API token, 2026-11-16). The nightly workflow keeps rounds running; a Qwen3.5-2B round is the latest. Score each finished round against run 23 when it lands in eval/kaggle-nightly.log.
- **LaCie is gone.** The uv cache, the repo's .venv and Ollama's models point at real folders on the internal disk now. The 9B model and the other LaCie data are lost until a new drive. Sealed heldout7 lived only on the LaCie and is lost. heldout12 is in eval/. The internal disk is at 13 GB free after cleanup (target was 20 GB), so check free space before anything over a gigabyte.
- **Picker:** run 23 (4,052 of 4,455 pooled dev rows) is still the shipped picker. Rounds 27 and 28 did not clearly beat it. The local q35r1 MLX run is superseded by the Kaggle round. 8.0 restarts only with a new idea: a newer base such as the Qwen3.5-2B round, relabeled dev sets, or a different model.
- **10.0 slice 1 is merged** (3.8.0, PR 577). The Python reference and kernel/picker.c match on all 297 golden sentences. The safety bar is missed: the small picker calls a tool on 115 of 434 not-a-command rows (26 percent), where run 23 manages 22 (5 percent). It stays "a small picker distilled from her". The next slice teaches it to abstain.
- **Joshua Tree 10.0 tag** still needs the docs and whitepaper refresh and Joshua's real-mic test. Caveat to say every time: the chat rows were written after reading the dev sets' mistakes, so the numbers are tuned to dev; the sealed sets are unread.
- **9.0 is Joshua's:** it needs his signed iPhone build and the Yeti mic.
- **Pi shell:** the boot-to-shell flip (docs/PI.md) still waits for Joshua's go-ahead.
- **Hero reel:** the web-demo cut was rejected. Three real-Mac takes exist; take 3 is with Joshua for grading.
- **Roadmap:** docs/roadmap.md, which the checkpoint's issue sync reads. Issue #107 (Blender family) stays open for "a simple 3D object" and "a logo as 3D text".
- **Sealed sets** heldout4, heldout7 and heldout12 are read as counts only, never as text.

## Next, in order

1. Score each finished Kaggle round (logged in eval/kaggle-nightly.log) against run 23 on the pooled dev sets, never a sealed set. Ship only if it clears the 8.0 bar below. A miss gets written here the same day.
2. Add Gemma 4 E2B to the nightly rotation in training/kaggle/nightly.py.
3. Ship 7.23.0: finish the uncommitted caption files (or the `caption-transcript` stash by name), run one real Whisper transcript, then release.
4. Teach from her misses (every wake, step 6). ~/.samantha/misses.jsonl is still absent (no real chats since 7.21.1).
5. Read heldout12 once, as counts, only if the round clears the bar.
6. Grade trailer take 3 to A+ and put it in the landing hero. It is the real-Mac reel: her driving it, 12 abilities in 30 seconds.
7. Video family leftovers, then the next roadmap minor, one ability per minor.
8. Audio (Yeti) waits on Joshua clicking the microphone prompt once.

## The ladder

**7.0, remembers and comes to you. Shipped 2026-10-12.** Left over for Joshua: the iPhone reading the iCloud copy needs an iCloud entitlement and a signed build.

**8.0, learns from the big ones.** Distillation: a frontier model writes the hard cases and she learns them. The bar, set before any run so it cannot be bent after: on the sealed heldout12, read once as counts, right picks go above run 19's 801 of 869 pooled rate, right picks refused fall below 2 percent (run 19: 40 of 869, 4.6 percent), and wrong picks past the guard stay at or under 19. Slices, one per wake, sealed sets never read as text:
1. Done 2026-10-12 on dev set heldout2 (the 844 MB picker fits in free memory): 452 of 500, 15 wrong picks, 7 past the guard, 6 right picks refused (1.9 percent), and the misses are single cases with no common cause (a book-a-call phrasing, "how far away is halloween", "whats inside notes.md"). The sealed refusal rate is higher (4.6 percent) because nobody tuned to those sentences, so the lever is breadth of fresh phrasings across every picker-eligible tool, not a patch for one cause.
2. Teacher data: write fresh, messy phrasings for every tool a model may pick (not NOT_FOR_MODELS), about 25 tools and 150 rows per wake, as {"text","tool","arg"} batches in the scratchpad, then `training/extra_to_data.py BATCH --out OUT.jsonl` drops anything an eval owns, any tool-name echo and any argument the guard would not run. Never read a sealed set; never copy test phrasing.
3. Round 24 (Kaggle v24, 2026-10-12) was rejected: heldout2 dev 445 of 500 against the shipped 452, one more wrong pick past the guard, same refusals. The flat teacher batch did not help; the next round should try weighting the teacher rows, or teaching only the tools the dev sets miss, and keep everything else equal. Round on Kaggle (docs/KAGGLE.md), then eval/picker_round.sh against dev sets; reject any run that leaks more.
4. Read heldout12 once, as counts. If the bar is met: ship the picker, whitepaper, HF card with `--model`, 8.0.0. If not, say so and keep the rounds going; never move the bar.
Check the free memory before any local model run and never run two at once. Kaggle outputs are about 6 GB and merged models 3 GB, so check the internal disk before a download. Only the converted 844 MB MLX picker needs to be local, and only to be scored.

**9.0, in your pocket.** The iPhone as a thin client to the Mac over his own network, voice first. Needs a signed device build and the Yeti mic (the Mac mini has none). Joshua-gated.

**10.0, her own home.** Her picker in freestanding C on the Joshua Tree kernel, checked in QEMU with the network off. Joshua Tree repo, branches and PRs, draft until ci-local is green.

The 10.0 bar, written 2026-10-12 before any measurement. A 1.5B model cannot run in the i386 kernel, so what ships is a small picker distilled from her: integer-only weights trained on training rows alone (never a dev or sealed row), run by freestanding C. It earns the name "her picker in C" only if all three hold. (1) Parity: the C picks match the Python reference on every golden sentence, 100 percent, checked headless in QEMU with the network off (`-nic none`), the check failing when the C is reverted. (2) Accuracy: on the pooled nine dev sets (4,455 rows) the tool-level right rate is at least 80 percent (3,564 rows), reported next to run 23's 4,052. Arguments stay with the guarded path, only the tool is picked. (3) Safety: a sentence the reference calls out of scope (tool null) is never turned into a tool call at a higher rate than run 23 manages, reported as counts. If a bar is missed, say so and keep the name "small picker"; never move the bar. Slices: a Python reference and its dev score, the C port with its QEMU check, then the Joshua Tree shell command and docs. Joshua Tree work goes in a worktree off fresh origin/main (no "samantha" in the path), a branch and a draft PR, ci-local green before ready.

10.0 slice 1 done 2026-10-12: Joshua Tree PR 577 (draft, 3.8.0). Python reference `training/smallpicker/ref.py` (hashed words and letter triples, 2048 buckets, margin perceptron, int8 weights pruned to 15,571, 119 classes) scores 3,820 of 4,455 tool picks on the nine dev sets, 85.8 percent against the 80 percent bar (run 23, tool and argument together, got 4,052). The C in `kernel/picker.c` matches it on all 297 golden sentences in QEMU with `-nic none`, and the check fails when the C is changed. It costs about 57KB of the kernel's room (30KB left). Merged as 3.8.0 (PR 577, ci-local green). The safety bar (3) is MISSED, as above. Next slice: teach it to abstain (a null margin tuned on training rows only, or more not-a-command rows in training), re-measure the three bars, keep the 80 percent right-rate. The 10.0 tag waits on the whole family.

## Pace and stops

- Usage is read at the top of every wake with `~/.claude/scripts/usage.sh`.
- Under 80 percent weekly: a wake every 20 to 30 minutes, one slice per wake.
- 80 to 84 percent: one wake an hour, CI fixes and checks only.
- 85 percent weekly: stop the loop, run /save, and never go past it.
- One Haiku subagent at a time, never a fan-out, and only for a slice that is code. Main session plans and merges.
- A wake with nothing to do says so in one line and sleeps longer. Nothing is invented to look busy.

## Every wake

1. `git pull --rebase`, then `gh run list`: any red check is fixed before anything else.
2. Read the usage line and pick the pace above.
3. Take the next ladder item. Build it in the smallest slice that ships.
4. Gate every push on exit codes: `scratchpad/gate.sh` style, the full CI set, with `./.venv/bin/python` (the shell's python3 is 3.9). Write python output to a file, never through grep.
5. Test the slice on the five bars: security, reliability, performance, stability and efficiency. Log the grade. A bar below A+ is the next slice.
6. Commit by exact path, push, then check every workflow run (test, release, deploy) and the live `/stats.json`.
7. Teach her what she missed: if `~/.samantha/misses.jsonl` or `~/.samantha/feedback.jsonl` grew since the last wake, label each new line as {"text","tool","arg"} (the tool she should have used, or null when no tool fits) into a scratchpad batch, run `training/extra_to_data.py BATCH --out training/teacher_batches/misses-DATE.jsonl`, and log the count here. Never label a sealed or dev-set phrasing. This is the recursive half of 8.0: her own misses become the next round's rows.
8. Rewrite "Where things stand" and "Next, in order" in this file so a fresh session can pick up cold.
9. One line to Joshua only when something shipped, broke, or needs him.

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
/loop Turing to v8.0: earn the 8.0 picker bar (Kaggle round on a newer base, sealed heldout12 read once as counts), ship 7.23.0, and each tick test for security, reliability, performance, stability and efficiency until A+; fully shipped (tag, release, deploy, live check). Stop at 85% weekly usage and /save.
```
