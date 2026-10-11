# Turing loop handoff (2026-10-11, afternoon, v5.11.7 shipped, v6.0 in progress)

## What the loop is

Work toward 6.0, one round at a time: integrate Joshua Tree tools and Pi hardware. A round ends with a feature or an honest "not yet". Hard stop and checkpoint at 90 percent usage. Every version gets a tag and a release.

## Where things stand

- **Live:** v5.11 (training run 20, shipped 2026-10-11 08:10; run 19 was v5.6, run 13 v5.1). Sealed 619-sentence test: 351 right picks (v5.0 had 317), 79 wrong (126), 27 past guard (30), about 4 percent refusals. Under-2 percent goal still open, documented honestly. Weights: https://huggingface.co/trommatic/samantha-hands-1.5b-mlx (the 0.5B GGUF for Windows and Linux stays at trommatic/samantha-hands-gguf).
- **Run 13 (3,260 hand-written sentences), sureness rule on:** the guard rule `SURE_SKIPS_CUES = 0.95` lets very confident non-writing picks run without their cue word, asking for the missing piece instead of refusing. Sealed heldout (619 fresh sentences from a writer who sees only the tool list): 351 right, 79 wrong, 27 past guard. Tried Qwen2.5-3B and Qwen3-1.7B bases; both matched run 13's sealed score, stay as next experiments.
- **Tools built:** `eval/misses.py` (every leak and refusal, sealed sets only), `training/dev_to_data.py` (retired blind sets into training rows), `training/extra_to_data.py` (hand-written batches, drops tool-name echoes).
- **Sealed sets:** heldout4, heldout7, heldout9, heldout12 (414 fresh sentences) are never read as text. Heldout6, 8, 10, 11 are dev sets (run 11 trained on 6 and 8).
- **Training plateau:** Run 16 (heldout9 and 11 folded in) is not better than v5.1. Heldout12: 372 of 414 right, 10.9 percent undone (v5.1: 364, 10.4); heldout4: 388 right, 6.8 percent (v5.1: 385, 5.9). Not shipped. More sentences stopped paying; misses are a long tail across about 28 tools (roughly half missing cue words, half arguments). Loop paused. Next lever: guard tuning, argument engineering, or Qwen3-1.7B (Apache, needs rope_theta config patch).
- Weights and dumps: `/Volumes/LaCie/turing-v10`, `-v11`, `-v12`, `-v13`, `-v16` (each has fetch_and_score.sh). Rescore with `./.venv/bin/python eval/hands.py --rescore <dump>`.

## 2026-10-11 night loop (running)

- Shipped today: v5.2.0 jt_status, v5.3.0 saved chats in the Mac app, v5.4.0 interrupt her (new message or "shh" stops her talking). Signed app re-uploaded.
- heldout13 (360 fresh dev sentences, writer saw only the tool list; arg hints trimmed where the label was the whole tail): live run-13 picker 310/360, 2 past guard, 6 refused. Real gaps: morse_code, shout, word_count, define_word, current_date, write_document drafts, teach_me, find_in_document, and inventing tools that do not exist (book_flight, send_text) for null requests.
- Run 17 result, not shipped: heldout13 334/360 0 past (run 13: 310, 2); sealed heldout4 395/455 9 past 14 refused (385, 8, 17); sealed heldout12 370/414 11 past 28 refused (364, 11, 28); standard 1773/1960 but 31 past (19). 11 of the 12 new standard leaks are "tldr this page"/"gist of this tab" picking summarize where standard wants agent (a label question to settle before any ship), the rest are screen-family drift (see_screen, read_screen, close_tab, type_text). Weights at /Volumes/LaCie/turing-v17/mlx.
- Coverage (first measured 2026-10-11, `coverage run --source=app` over every tests/test_*.py plus actions, laws, tools.py, tools_util.py): 76 percent of app/. Holes: serve.py 97 (test_serve.py, v5.4.2), tools_files 59 (was 17, test_files.py added with v5.4.1), tools_mail_send 96 (was 44), robot.py 45, chat.py 48. mcp_server's 32 is a measurement artifact: test_mcp.py drives it as a subprocess and covers every branch. tools_coder 84 (was 49, v5.4.4). ask_web 52 to about 95 (test_ask_web.py). ask.py 59 to about 95 (test_ask.py). ask_local and ask_faq covered by test_ask_local.py. Next test slices: chat.py (48, mostly the interactive loop), robot.py (45, needs the Pi); then back to features.
- Run 18 result, not shipped: heldout13 324/360 2 past 4 refused; heldout4 377/455 10 past; standard 1734/1962, 45 past (41 with the read_page cue). Lighter weighting scored below run 17 everywhere, so run-to-run noise is bigger than the data change. Most of the extra standard leaks in 17 and 18 were a label contradiction ("tldr this page" trained as agent, scored as agent, but it is summarize), fixed in gen_hands_data with v5.4.3; the standard set is a fresh sample now, so old dumps do not compare directly. Run 19 = run 16 data with those labels patched plus the 441 rows once.
- Run 19 shipped as v5.6.0: heldout13 323/360 1 past 3 refused; sealed heldout4 380/455 7 past 13 refused; heldout12 373/414 12 past 27 refused; standard (fresh sample) 19 past. Weights uploaded to trommatic/samantha-hands-1.5b-mlx and copied to models/samantha-hands-1.5b-mlx. Numbers in docs/BAKEOFF.md. Fair standard comparison: run 13 re-picked on the fresh sample leaks 10, run 19 leaks 19 (all read-only or confirm-gated picks); the next run's standard bar is 10.
- Run 18 (was): same as 17 but the targeted rows counted once, not twice, to see if the drift was the weighting.
- Run 17 (was): run 16's Kaggle data (/Volumes/LaCie/turing-v17/data, 12,673 rows) plus a targeted Haiku batch (scratchpad batch17.jsonl through training/extra_to_data.py) for those tools and 100 null requests. Ship only if it beats run 13 on heldout13 and does not get worse on sealed heldout4/12 (counts only). Pushed as Kaggle kernel version 17 at about 01:40 on 2026-10-11. Resume: read /Volumes/LaCie/turing-v17/score.out; if empty, run /Volumes/LaCie/turing-v17/fetch_and_score.sh. Run 13 baselines: heldout13 310/360, 2 past, 6 refused; heldout4 385/455, 8 past, 17 refused; heldout12 364/414, 11 past, 28 refused.

## 2026-10-11 pickup

Frontier check: Qwen4 unreleased; Qwen-Image-2.1-Turbo (Oct 9) is real but needs 12 to 16 GB here (see roadmap). Qwen3.5 small bases (0.8B/2B/4B) exist on Kaggle (qwen-lm/qwen-3-5) but are a hybrid multimodal architecture: needs a transformers version that supports it and an MLX converter check, and every other base tied run 13, so it is parked as a low-odds experiment. Guard cues widened for days_until, needs_attention, feedback_summary (dev refusals down 4, no new leaks). The rename "tab bug" was a model garble, not code; the guard is right to refuse it. Dev sets 6/8 are trained on, so they overstate; a fresh labeled dev set is still the missing piece.

## Run 21 (2026-10-11 13:40): rejected

Worse on heldout13 (324 vs 325), heldout4 leaks 11 vs 7, heldout12 364 vs 375. Run 20 stays live. Details in docs/BAKEOFF.md. Files kept in /Volumes/LaCie/turing-v21.

## Run 22 (2026-10-11 15:10): rejected

Better on heldout13 (331, 0 past) and heldout14 (235), fewer leaks over the sealed pair (19 vs 20), but heldout12 366 vs 375 and heldout4 leaks 9 vs 7. Run 20 stays live. Table in docs/BAKEOFF.md. Files in /Volumes/LaCie/turing-v22 (mlx, all five dumps). Next training step: per-tool counts on heldout12 (eval/misses.py prints counts only for sealed sets) to see what the batch displaced, then a balanced run 23.

## Next, in order (2026-10-11 afternoon)

1. Run 22 verdict: score it with `bash /Volumes/LaCie/turing-v22/fetch_and_score.sh` and heldout14 with `--test eval/heldout14.jsonl`. Ship only if it beats run 20 (229 of 291 on heldout14) and does not add sealed leaks on heldout4/12 or heldout13. Otherwise run 20 stays and the next lever is guard and argument work.
2. Test slices by coverage hole: mcp_server (32), tools_mail_send (44), chat.py (48), tools_coder (49). One file per round, fix any bug it finds, patch release each.
3. Landing demo: every new tool gets a route in web/samantha.js, a STANDIN answer in web/demo.js, a REEL or MORE phrase, and an actions.py case (jt_status is the template).
4. Pi robot when the hardware is on the network. The Joshua Tree family from chat is complete (status, boot, type, log, screenshot, look, stop).
5. Image-generation experiment (Qwen-Image-2.1-Turbo Q4 via stable-diffusion.cpp, weights on the LaCie, everything else closed).

## Next, in order (older)

1. Raspberry Pi hardware (arriving today): app/robot.py on real Pi first boot. Network, UART serial, screen framebuffer drawing, then 0.5B GGUF picker inference. app/install.sh, then python3 app/robot.py.
2. Joshua Tree driving tools: spawn processes, call methods, poll status from chat (replacing FAQ asks with real tool calls).
3. Signed SamanthaGUI.zip installer with new icon (needs Joshua's Developer ID keychain).
4. Training: if plateau holds, guard and argument engineering, or Qwen3-1.7B base with rope_theta patch.
5. Turing app: saved chats, full-screen voice mode that can be interrupted, video mode with camera.

## Restart prompt

```
/loop until v6 (read docs/LOOP-HANDOFF.md first).

Start here: v5.11.7 live on run 20 picker. Run 21 rejected, run 22 in flight on Kaggle (/Volumes/LaCie/turing-v22). First: score run 22 on heldout13, heldout4/12 and heldout14, ship only if it beats run 20 with no more sealed leaks. Then the Next list in order. Never weaken a guard. Hard stop at 90 percent usage. TLDR only.
```
