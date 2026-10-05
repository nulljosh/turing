# Turing loop handoff (2026-10-05, v5.1 shipped, v6.0 in progress)

## What the loop is

Work toward 6.0, one round at a time: integrate Joshua Tree tools and Pi hardware. A round ends with a feature or an honest "not yet". Hard stop and checkpoint at 90 percent usage. Every version gets a tag and a release.

## Where things stand

- **Live:** v5.1 (training run 13). Sealed 619-sentence test: 351 right picks (v5.0 had 317), 79 wrong (126), 27 past guard (30), about 4 percent refusals. Under-2 percent goal still open, documented honestly. Weights: https://huggingface.co/trommatic/samantha-hands-1.5b-mlx (the 0.5B GGUF for Windows and Linux stays at trommatic/samantha-hands-gguf).
- **Run 13 (3,260 hand-written sentences), sureness rule on:** the guard rule `SURE_SKIPS_CUES = 0.95` lets very confident non-writing picks run without their cue word, asking for the missing piece instead of refusing. Sealed heldout (619 fresh sentences from a writer who sees only the tool list): 351 right, 79 wrong, 27 past guard. Tried Qwen2.5-3B and Qwen3-1.7B bases; both matched run 13's sealed score, stay as next experiments.
- **Tools built:** `eval/misses.py` (every leak and refusal, sealed sets only), `training/dev_to_data.py` (retired blind sets into training rows), `training/extra_to_data.py` (hand-written batches, drops tool-name echoes).
- **Sealed sets:** heldout4, heldout7, heldout9, heldout12 (414 fresh sentences) are never read as text. Heldout6, 8, 10, 11 are dev sets (run 11 trained on 6 and 8).
- **Training plateau:** Run 16 (heldout9 and 11 folded in) is not better than v5.1. Heldout12: 372 of 414 right, 10.9 percent undone (v5.1: 364, 10.4); heldout4: 388 right, 6.8 percent (v5.1: 385, 5.9). Not shipped. More sentences stopped paying; misses are a long tail across about 28 tools (roughly half missing cue words, half arguments). Loop paused. Next lever: guard tuning, argument engineering, or Qwen3-1.7B (Apache, needs rope_theta config patch).
- Weights and dumps: `/Volumes/LaCie/turing-v10`, `-v11`, `-v12`, `-v13`, `-v16` (each has fetch_and_score.sh). Rescore with `./.venv/bin/python eval/hands.py --rescore <dump>`.

## Next, in order

1. Raspberry Pi hardware (arriving today): app/robot.py on real Pi first boot. Network, UART serial, screen framebuffer drawing, then 0.5B GGUF picker inference. app/install.sh, then python3 app/robot.py.
2. Joshua Tree driving tools: spawn processes, call methods, poll status from chat (replacing FAQ asks with real tool calls).
3. Signed SamanthaGUI.zip installer with new icon (needs Joshua's Developer ID keychain).
4. Training: if plateau holds, guard and argument engineering, or Qwen3-1.7B base with rope_theta patch.
5. Turing app: saved chats, full-screen voice mode that can be interrupted, video mode with camera.

## Restart prompt

```
/loop until v6 (read docs/LOOP-HANDOFF.md first).

Start here: v5.1 live with run 13. Run 16 hit plateau; loop paused on training (misses long tail across 28 tools). Joshua has Pi today: app/robot.py on real hardware first, then Joshua Tree driving tools. Next: install.sh, robot.py, processes/methods/status from chat. Do the handoff's Next list in order. Never weaken a guard. Hard stop at 90 percent usage. TLDR only.
```
