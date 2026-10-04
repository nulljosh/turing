# Turing loop handoff (2026-10-04, evening)

**Loop status: live.** Working toward v5.0.0 (her own tool-calling head, better picker accuracy). Shipped v4.20.0 with explain_codebase, teach_me, send_email, open app and do task; Windows install tested in real CI runner; Samantha's GGUF on Hugging Face with auto-refresh on every release. Kaggle training: Qwen2.5-1.5B trained (1705/1960 right vs 1307 for 0.5B, but leaks harder, stays off by default). Guard rounded 23 to 27. Teacher training generated 720 labeled commands; 1.5B made 41 mistakes, converted to DPO preference pairs; Kaggle version 8 training DPO stage (results pending). Router-off trial: 1.5B alone without phrase router scored 168 of 231 everyday commands (73 percent); most misses NOT_FOR_MODELS tools. Changed v5 design: model picks every tool it may pick; phrase-only tools stay law-routed; numeric gate unchanged (under 10 past guard, 0 refused on sealed heldout6). Helper building v6's first slice (code a feature: plan, show diffs, ask, apply, run tests). Estimates: v5 roughly 3-10 days (depends on sealed heldout6 zero refuses), v6 roughly 1-2 weeks after v5.

## What the loop is

Work toward v5.0.0 (her own tool-calling head, better picker accuracy, research beyond Wikipedia). Loop target: until v5.0.0 on this Mac, then v10.0.0 in order (7.0, 6.0, 8.0, 9.0, 10.0). Hard stop and checkpoint at 90% usage. One round at a time, measured against held-out sets. v5.0 waiting on free GPU training (Joshua running Kaggle this weekend).

## Where things stand

v4.20.0 shipped (2026-10-04): four new tools, Windows install tested in real CI runner, Samantha's GGUF on Hugging Face with auto-refresh on every release, free Kaggle GPU training completed with Qwen2.5-1.5B picker (1705/1960 right vs 1307 for 0.5B, stays loadable off by default). Guard rounded 23 to 27. Teacher training generated 720 labeled commands; 1.5B made 41 mistakes, converted to DPO preference pairs; Kaggle version 8 training DPO stage (results pending). Router-off trial: 1.5B alone scored 168 of 231 everyday commands (73 percent); most misses NOT_FOR_MODELS tools. Changed v5 design: model picks every tool it may pick, phrase-only tools stay law-routed. Helper building v6's first slice. v5.0 gate: under 10 wrong past guard and 0 refused on sealed heldout6 (currently 12 wrong, 11 refused from earlier rounds). Template-data training parked; DPO stage now active. 127 tools total. Estimates: v5 roughly 3-10 days, v6 roughly 1-2 weeks after v5.


## v5.0 reality check (2026-10-02, Joshua set the goal to v5)

Round 22 (same recipe, fresh template data) was worse and less safe: 19 past the guard against 7 on standard. Nothing swapped. Two things stand between her and 5.0. (1) The picker: the sealed judge reads 12 wrong past the guard and 11 right picks refused, and the bar is under 10 and 0; a 0.5B model is at about 65 percent of phrasings right. (2) The architecture: `tools.act()` is still the exact regex router and it answers first, the model only sees what the router misses; 5.0 says nothing goes through the router. Removing it today would drop her well below what she does now. The notes say bigger bases crashed training on this Mac (Qwen3.5-0.8B twice), so a bigger head needs training off this machine, which is Joshua's call (cost). The free lever left is data from her own live misses, not templates. There are none yet: ~/.samantha/feedback.jsonl does not exist (feedback is typing "good" or "wrong" in her chat, or "wrong, I meant X"). Loop rule until it fills: check that file once an hour and do nothing else; at 60 or more rows run `python3 training/feedback_to_data.py`, then `training/picker_round.sh <next>`, and ship only if no less safe. No more template-data rounds (round 22 proved they do not move the judge).

## Next, in order

1. **v4.20.2 shipped (2026-10-04): rounds 30 and 31.** Guard rules plus a data fix (one phrase, one tool). Kaggle v9 reads standard 1720/1960 L7 R0, heldout2 L8 R2, heldout4 L9 R17, heldout5 L3 R4. Kaggle v10 trains on the fixed data (dataset now carries test.jsonl, kernel scores 200 rows itself). Next: score v10 on the dev sets with `--dump`, then keep cutting refusals on heldout2 and heldout5 (never tune on heldout4 text; heldout6 stays sealed until dev refusals are near 0). In zsh pass `--test file` as two words.
2. Once Kaggle finishes, fetch the trained adapter (uvx kaggle kernels output, see docs/KAGGLE.md).
3. Score on standard, heldout2, heldout4, heldout5 (never read heldout6 until final candidate).
4. If DPO clears 5.0 gate (under 10 wrong, 0 refused on heldout6), ship v5.0.0 with major-release docs pass (WHITEPAPER, landing, README, badge, LOOP-HANDOFF for v6).
5. If not, write short BAKEOFF entry and plan next DPO round from dev misses.
6. After v5.0.0 ships, work toward v6.0.0: helper building first slice (code a feature: plan, show diffs, ask, apply, run tests).

## Restart prompt

Loop live. Paste this to continue:

```
/loop work the Turing roadmap until v5.0.0, one round at a time (read docs/LOOP-HANDOFF.md), then v6.0.0, then /checkpoint.

Start here: v4.20.0 shipped with new tools and Kaggle training in progress (version 8 training DPO stage with 720 labeled commands and 41 mistakes converted to preference pairs). Router-off trial showed 1.5B alone scores 73 percent on everyday commands; v5 design changed to have model pick every tool it may pick, phrase-only tools stay law-routed. v5.0 gate: under 10 wrong past guard and 0 refused on sealed heldout6. When Kaggle finishes, fetch the adapter and score on dev sets. If it clears 5.0 gate, ship v5.0.0 with major-release docs pass. Helper building v6's first slice (code feature harness). Template-data rounds parked; all training now preference-based. No more blind heldout testing after 5.0.

Deploys automatic after green push. Hard stop at 90% session usage. TLDR only.
```
