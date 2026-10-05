# Turing loop handoff (2026-10-05, v5.1 shipped, v6.0 in progress)

## What the loop is

Work toward 6.0, one round at a time: integrate Joshua Tree tools and Pi hardware. A round ends with a feature or an honest "not yet". Hard stop and checkpoint at 90 percent usage. Every version gets a tag and a release.

## Where things stand

- **Live:** v5.1 (training run 13). Sealed 619-sentence test: 351 right picks (v5.0 had 317), 79 wrong (126), 27 past guard (30), about 4 percent refusals. Under-2 percent goal still open, documented honestly. Weights: https://huggingface.co/trommatic/samantha-hands-1.5b-mlx (the 0.5B GGUF for Windows and Linux stays at trommatic/samantha-hands-gguf).
- **Run 13 (3,260 hand-written sentences), sureness rule on:** the guard rule `SURE_SKIPS_CUES = 0.95` lets very confident non-writing picks run without their cue word, asking for the missing piece instead of refusing. Sealed heldout (619 fresh sentences from a writer who sees only the tool list): 351 right, 79 wrong, 27 past guard. Tried Qwen2.5-3B and Qwen3-1.7B bases; both matched run 13's sealed score, stay as next experiments.
- **Tools built:** `eval/misses.py` (every leak and refusal, sealed sets only), `training/dev_to_data.py` (retired blind sets into training rows), `training/extra_to_data.py` (hand-written batches, drops tool-name echoes).
- **Sealed sets:** heldout7, heldout9, heldout (619) are never read as text until now, heldout6, 8, 10 are dev sets (run 11 trained on 6 and 8). The 619-sentence set is now in use.
- Weights and dumps: `/Volumes/LaCie/turing-v10`, `-v11`, `-v12`, `-v13` (each has fetch_and_score.sh). Rescore a dump with `./.venv/bin/python eval/hands.py --rescore <dump>`.

- **Run 16 (heldout9 and 11 folded in) is not better than 5.1:** heldout12 372 of 414 right, 10.9 percent undone, 10 leaks (5.1: 364, 10.4, 11); heldout4 388 right, 6.8 percent undone, 9 leaks (5.1: 385, 5.9, 8). Not shipped. More sentences have plateaued; the misses are one or two each across about 28 tools, half missing cue words and half arguments. Next lever is guard and argument engineering, or Qwen3-1.7B (Apache) with a patched config (add rope_theta at the top of config.json before mlx convert). Sealed: heldout4, heldout7, heldout12.

## Next, in order

1. Joshua Tree integration: she now answers questions about it; next are tools to spawn processes, call methods, poll status (driving its APIs from chat).
2. Raspberry Pi hardware: 4B 4GB arriving soon (docs/PI.md holds the plan). First boot, network, UART serial, screen framebuffer drawing, then inference of the 0.5B GGUF picker.
3. Signed SamanthaGUI.zip for the installer (needs Joshua's Developer ID keychain entry). Footer badge refresh if run 13 stays live.
4. Turing app: saved chats, full-screen voice mode that can be interrupted, video mode with camera.
5. If refusal rate stays near 4 percent, explore more base models (Phi 3.5, Smol LM) trained on the same data.

## Restart prompt

```
/loop until v6 (read docs/LOOP-HANDOFF.md first).

Start here: v5.1 is live with run 13 and the sureness rule. About 4 percent of right commands still undone; under-2 percent goal stays open. Next: Joshua Tree driving tools, Pi hardware, signed installer. Do the handoff's Next list in order. Never weaken a guard. Tag and release every version. Hard stop at 90 percent usage. TLDR only.
```
