# Turing loop handoff (2026-10-04, night)

## What the loop is

Work toward 5.1, one round at a time, measured on held-out sets. A round ends with a sealed read or an honest "not yet". Hard stop and checkpoint at 90 percent usage. Every version gets a tag and a release.

## Where things stand

- **Live:** v5.0.0. Her own 1.5B picker is the default on a Mac. Weights: https://huggingface.co/trommatic/samantha-hands-1.5b-mlx (the 0.5B GGUF for Windows and Linux stays at trommatic/samantha-hands-gguf).
- **v5 shipped with a miss, on Joshua's call.** Wrong picks past the guard are under 10 on every set. Right commands left undone are 5.0 percent on heldout4 and 4.2 on heldout6; the bar is under 2. Not done means refused, or asked although the sentence names its target (the written bar, with the questions on pointing sentences printed beside it by `eval/hands.py`).
- **Sealed set:** heldout7 (552 rows) is at `/Volumes/LaCie/turing-v10/h7/sealed/heldout7.filtered.jsonl`, outside the repo, never opened. Read it once, when heldout4 is clearly under 2 percent.
- **What the misses look like (counts only, no text):** heldout4's 14 refusals are 14 different tools, one each. Nine are the guard's cue-word check (the model was right, the sentence lacks a word the guard wants) and five are copied-argument drift. There is no cluster to train on, and a training round cannot fix the nine: the model already picked right. Loosening a cue word per tool is what round 35's review threw out, and tuning on heldout4's text would end its life as the blind reading.
- **Weights and scores:** the Kaggle v10 MLX copy is at `/Volumes/LaCie/turing-v10/mlx`, pick dumps beside it. Rescore a dump with `./.venv/bin/python eval/hands.py --rescore <dump>`.

## Next, in order

1. Do not start a Kaggle round for this. Write a fresh blind set (heldout8, a writer who sees only the tool list), then fix refusals on the dev sets one tool at a time, each with an adversarial review of what the loosened cue word lets through (one Haiku agent, never a workflow). Training only helps the five argument-drift cases (copy the sentence's words, not a rewording).
2. When heldout4 is clearly under 2 percent not done and leaks stay under 10, read heldout7 once. A pass is 5.1.
3. Refresh the footer badge: `tools_badge.step_for` gives 5.0.0 fewer motifs than 4.20 already has. Fix the step rule, then rebuild.
4. The Turing app: SamanthaGUI today is a chat window with Voice and Face toggles. Next are saved chats, a full-screen voice mode that can be interrupted, and a video mode with the camera. The app is Turing, Samantha is the model inside.
5. The coder (`code X in project`) is still untested against a real model. It needs her 9B server running.

## Restart prompt

```
/loop work the Turing roadmap toward 5.1, one round at a time (read docs/LOOP-HANDOFF.md first).

Start here: v5.0.0 is live with her 1.5B picker as the default. The bar was missed on purpose: about 5 percent of right commands are left undone on heldout4 (refused, or asked although the sentence names its target), the goal is under 2. Write heldout8 as a fresh blind set, fix dev-set refusals one tool at a time with a review each (the model is right, the guard's cue word is the stop), rescore every dev dump, and never read heldout4's text. Do not start a Kaggle round for this. Read the sealed set at /Volumes/LaCie/turing-v10/h7/sealed/heldout7.filtered.jsonl exactly once, when heldout4 is clearly under 2 percent. Then the badge, then the Turing app.

Never weaken a guard. Tag and release every version. Hard stop at 90 percent usage. TLDR only.
```
