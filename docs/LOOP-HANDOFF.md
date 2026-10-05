# Turing loop handoff (2026-10-04, night)

**Loop status: stopped by Joshua (wrap up), mid-round.** v4.20.16 is the live version. The loop is working toward v5.0.0: her own bigger picker (the Kaggle 1.5B) as the default. Nothing from this round is shipped yet.

## The v5 bar (set 2026-10-04, before heldout6 was read)

Joshua left the call to me. Zero refused is out of reach for a guard that must also stop composed arguments (heldout4 refuses 3 percent of right picks, mostly correctly). The v5 bar on a sealed set is under 10 wrong past the guard and under 1 percent of its right picks refused. Written down before the read so the number cannot move to fit the result. heldout6 was read once against it and missed on refusals (3.6 percent). The next sealed set is heldout7.

## What the loop is

Work toward v5.0.0, one round at a time, measured on held-out sets. A round ends with a sealed read or an honest "not yet". Hard stop and checkpoint at 90 percent usage. Every version gets a tag and a release.

## Where things stand

- **Live:** v4.20.16. Landing page A+, commercial 28 seconds with her voice and a ducked music bed, all checks green.
- **Picker candidate:** Kaggle v10 (Qwen2.5-1.5B, SFT plus a gentle DPO stage). The 4-bit MLX copy is at `/Volumes/LaCie/turing-v10/mlx` (the fp16 download is beside it in `hands-merged`). It is not in the repo and not uploaded anywhere. Convert on the CPU: the GPU timed out reading 3 GB off the spinning disk.
- **Round 35 is one commit on the local branch `round-35` (not pushed, not on main), kept there so `/ultrareview` has a branch to review:** `app/tools_registry.py` adds four narrow "which one?" families (a file to show in Finder, a reminder to tick off, a note to add to, a switch never told on or off). Each needs its own noun in the sentence. `eval/hands.py` now records how sure she was (`sure`) in dumps and checks soundness on the repaired argument, the way the live picker does. All local checks pass.
- **What the review caught:** the first version of round 35 loosened evidence for flip_image, open_in_editor, rename_file and append_note, rebuilt append_note arguments, and dropped the family noun in `needs_target`. Two independent reviewers reproduced wrong picks running and small talk drawing "Which file?". That version was thrown out (kept for reference at `/Volumes/LaCie/turing-v10/tools_registry.round35-loose.py`).
- **Scores with the round-35 guard (Kaggle v10):** standard 1707 of 1960, 6 past the guard, 0 refused, 1 asked. heldout2 415 of 500, 7 past, 1 refused. heldout4 (never tuned on) 356 of 455, 9 past, 14 refused, 23 asked. heldout5 404 of 507, 2 past, 2 refused, 7 asked. heldout6 was not rescored (scoring stopped at the wrap up; its dump is partial). Dumps are in `/Volumes/LaCie/turing-v10/*-picks.jsonl`.
- **What the measurement review said:** a right pick that ends in a question is still not done for the user, so moving refusals into "asked" is a relabel, not a fix; no gate reads "asked"; a wrong pick that ends in a question is counted nowhere; `sure` is written to dumps and read by nothing. All true. The honest number to watch is refused plus asked.
- **Sealed set:** a fresh writer wrote heldout7 from the tool list only. 552 rows after dropping 67 that duplicated existing data. It sits at `/Volumes/LaCie/turing-v10/h7/sealed/heldout7.filtered.jsonl`, outside the repo, never opened. Counts only until the one read.
- **My honest read:** with a guard that is not weakened, refusals land near 2 percent on unseen wording. The sealed read will likely miss the 1 percent bar. Closing that gap takes a training round (cleaner argument copying, more phrasings), not more guard rules.

## What a v5.0.0 release needs beyond the test

A code map of the swap found work that a passing test does not cover, and some of it is Joshua's call:

- Host the weights. Nothing 1.5B is uploaded. The MLX folder is about 850 MB; a GGUF for Windows and Linux is about 1.65 GB.
- Decide where the model lives on a user's Mac and who fetches it (the launcher at first run, or lazily on the first pick). The loader already looks for `models/samantha-hands-1.5b-mlx`.
- Decide whether Windows and Linux move to the 1.5B or stay on the 0.5B GGUF.
- Decide whether v5 also puts her model ahead of the phrase router in `tools.do()`, or is only the picker swap.
- Loader fixes in `app/tools_agent.py` (set the unsure threshold only after a good load, fall back to the 0.5B when the folder is broken), gate and baseline pointed at the default picker, a loader test, a speed and memory reading, UNSURE recalibrated on v10, then the major-release docs pass.

## Next, in order

1. Rescore heldout6 (rerun `/Volumes/LaCie/turing-v10/fetch_and_score.sh`, it skips the download and convert), then rescore every dump: `./.venv/bin/python eval/hands.py --rescore <dump>` (flags go before `--rescore`). Before round 35 the numbers were standard 7 past and 1 refused, heldout2 7 and 1, heldout4 9 and 14, heldout5 2 and 3, heldout6 8 and 13. Never read heldout4's text.
2. Add a count of wrong picks that get a question to the `eval/hands.py` summary, so a change that makes small talk draw a question is visible on the scoreboard. Check `gate.sh` and `training/picker_round.sh` still parse the line.
3. Read the review's eval-fidelity findings (journal under `~/.claude/projects/-Users-joshua/c9d3678a-e9f9-4f08-a486-a3d9de3a1d9c/subagents/workflows/wf_a4507fdb-7cd/`). Fix what is real.
4. Run every local check, commit round 35 as the next patch with a BAKEOFF entry that says what the review caught, push, confirm CI.
5. Copy the sealed set to `eval/heldout7.jsonl` and read it once with v10 against the bar. Pass: start the release work above with Joshua's decisions. Miss: log it in BAKEOFF, heldout7 becomes a dev set, plan the training round.
6. The coder (`code X in project`) is still untested against a real model. It needs her 9B server running.

## Restart prompt

```
/loop work the Turing roadmap toward v5.0.0, one round at a time (read docs/LOOP-HANDOFF.md first).

Start here: v4.20.16 is live. Round 35 is one commit on the local branch round-35, not on main (four narrow "which one?" families in app/tools_registry.py, confidence and repaired-argument scoring in eval/hands.py) and passes local checks. The Kaggle v10 1.5B is at /Volumes/LaCie/turing-v10/mlx with pick dumps beside it. Finish scoring and rescore all dev dumps, add the wrong-picks-asked count to eval/hands.py, commit round 35 as the next patch, then read the sealed set at /Volumes/LaCie/turing-v10/h7/sealed/heldout7.filtered.jsonl exactly once against the written bar (under 10 wrong past the guard, under 1 percent of right picks refused). Never open heldout7's rows before that read and never read heldout4's text. A pass starts the release work in the handoff, which needs Joshua's decisions on hosting the weights. A miss is logged honestly and the next step is a training round.

Never weaken a guard. Tag and release every version. Hard stop at 90 percent usage. TLDR only.
```
