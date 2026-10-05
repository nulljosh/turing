# Turing loop handoff (2026-10-04, started v5.1)

## What the loop is

Work toward 5.1, one round at a time, measured on held-out sets. A round ends with a sealed read or an honest "not yet". Hard stop and checkpoint at 90 percent usage. Every version gets a tag and a release.

## Where things stand

- **Live:** v5.0.0. Her own 1.5B picker is the default on a Mac. Weights: https://huggingface.co/trommatic/samantha-hands-1.5b-mlx (the 0.5B GGUF for Windows and Linux stays at trommatic/samantha-hands-gguf).
- **v5.1 in progress:** Guard cue-word fixes for eight core tools cut refusals from 5.2 to 2.6 percent on blind heldout8 test set (488 sentences). But 10 wrong picks still leak through; needs per-tool adversarial review to fix the guard without loosening it too far. heldout7 (552 rows) is sealed at `/Volumes/LaCie/turing-v10/h7/sealed/heldout7.filtered.jsonl`, never opened. Read it once when heldout4 is clearly under 2 percent and leaks stay under 10.
- **Weights and scores:** the Kaggle v10 MLX copy is at `/Volumes/LaCie/turing-v10/mlx`, pick dumps beside it. Rescore a dump with `./.venv/bin/python eval/hands.py --rescore <dump>`.

## Next, in order

1. Per-tool adversarial review of the eight guard fixes. For each tool, check what the loosened cue word lets through (one Haiku agent per tool, never a workflow). When heldout4 is clearly under 2 percent and leaks are under 10, move on.
2. Read heldout7 sealed set exactly once, when heldout4 is done. A pass is 5.1.
3. v6.0 target tomorrow morning: Samantha knows Joshua Tree OS and runs on Raspberry Pi as a desk robot. Joshua Tree port integration starts after 5.1 ships.
4. Refresh the footer badge: `tools_badge.step_for` gives 5.0.0 fewer motifs than 4.20 already has. Fix the step rule, then rebuild.
5. The Turing app: SamanthaGUI today is a chat window with Voice and Face toggles. Next are saved chats, a full-screen voice mode that can be interrupted, and a video mode with the camera. The app is Turing, Samantha is the model inside.

## Restart prompt

```
/loop until v5.1 ships, then ship when it /goal beats 5.0 (read docs/LOOP-HANDOFF.md first).

Start here: v5.1 guard work cut refusals to 2.6 percent on heldout8 (488 blind sentences), but 10 picks still leak. Review the eight guard fixes one tool at a time with a Haiku agent (what does each loosened cue word let through?). When heldout4 is clearly under 2 percent and leaks are under 10, read the sealed heldout7 set exactly once at /Volumes/LaCie/turing-v10/h7/sealed/heldout7.filtered.jsonl. A pass there is 5.1. v6.0 target is tomorrow: Samantha knows Joshua Tree and runs on Pi as a desk robot.

Never weaken a guard. Tag and release every version. Hard stop at 90 percent usage. TLDR only.
```
