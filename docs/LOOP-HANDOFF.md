# Turing loop handoff (2026-10-05, early morning, 5.1 in progress)

## What the loop is

Work toward 5.1 (then 6.0), one round at a time: write sentences, train on Kaggle, score on a fresh blind set, fix the guard, repeat. A round ends with a score or an honest "not yet". Hard stop and checkpoint at 90 percent usage. Every version gets a tag and a release.

## Where things stand

- **Live:** v5.0.0 (training run 10). Weights: https://huggingface.co/trommatic/samantha-hands-1.5b-mlx (the 0.5B GGUF for Windows and Linux stays at trommatic/samantha-hands-gguf).
- **Run numbers are not app versions.** Run 12 is the newest Kaggle training; it ships inside 5.1 only if it clears the bar.
- **Run 12 (3,260 hand-written sentences added), sureness rule on:** heldout9 (fresh) 10.2 percent undone, 17 leaks; heldout4 (sealed) 5.1 percent, 8 leaks; heldout10 8.4 percent, 23 leaks. The bar is under 2 percent undone and under 10 leaks. Not met.
- **Run 11 vs 10:** right picks up everywhere, wrong picks roughly halved.
- **New this round:** `app/tools_registry.py` `SURE_SKIPS_CUES = 0.95` lets a very sure pick of a non-writing tool run without its cue word (calibrated on heldout10). Tests in `tests/test_guard_probes.py`.
- **Tools built:** `eval/misses.py` (every leak and refusal, counts only for sealed sets heldout4, 7, 9), `training/dev_to_data.py` (retired blind sets into training rows), `training/extra_to_data.py` (hand-written batches into rows, drops tool-name echoes).
- **Sealed:** heldout4, heldout7, heldout9 are never read as text. heldout6, 8, 10 are dev sets (run 11 trained on 6 and 8).
- **Label noise:** many "leaks" on Haiku-written sets are sibling tools (read_file vs read_document, research vs web_search). Treat a fresh set's leak count as an upper bound.
- Weights and dumps: `/Volumes/LaCie/turing-v10`, `-v11`, `-v12` (each has fetch_and_score.sh). Rescore a dump with `./.venv/bin/python eval/hands.py --rescore <dump>`. Kaggle kernel `joshuatrommel/samantha-hands-train`, dataset `joshuatrommel/samantha-hands` (the scratchpad copy of the data folder is the newest train.jsonl).

## Next, in order

1. Run 13: fold heldout10 and the last guard fixes into training, write a new fresh blind set (heldout11) first, then fetch and score.
2. Guard review: one Haiku agent per loosened rule, never a workflow; add every confirmed leak to `tests/test_guard_probes.py`.
3. If undone commands plateau near 5 percent, try a different base model (Llama 3.2, Gemma) on the same data.
4. When heldout4 is clearly under 2 percent undone with leaks under 10, read heldout7 once. A pass is 5.1: bump VERSION, tag, release, upload the weights.
5. 6.0: Samantha knows Joshua Tree (notes and tools), and runs on a Raspberry Pi as a desk robot (the 0.5B GGUF path).
6. Footer badge (`tools_badge.step_for`), the signed SamanthaGUI.zip with the new icon, the Turing app.

## Restart prompt

```
/loop until v6 (read docs/LOOP-HANDOFF.md first).

Start here: run 12 is scored and not yet at the bar. Do round 13 from the handoff's Next list. Never weaken a guard, never read a sealed set's text, one Haiku agent at a time. Tag and release every version. Hard stop at 90 percent usage. TLDR only.
```
