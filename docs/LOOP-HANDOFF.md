# Turing loop handoff (2026-10-01, late; v4.17.9, round 16 shipped)

## What the loop is

Joshua's call 2026-10-02: loop toward v10.0.0 if the budget allows, one major at a time in roadmap order (5.0 her own head, then 7.0, 6.0, 8.0, 9.0, 10.0). Hard stop and /checkpoint at 90% usage, never mid-round. Work the Turing roadmap toward v5.0.0 first: her own tool-calling head, better picker accuracy, and research beyond Wikipedia. One round at a time, measured against held-out sets. Watch usage and taper on overage; hard stop at 90% session usage. This checkpoint saves the resume point; it does not restart training or the loop.

## Where things stand

v4.17.9 (2026-10-01 late): round 16 shipped. Fresh writer built heldout4.jsonl (455 rows, readable dev set mirroring heldout3); deictic "trash this file" / "crop this image" now asks "Which file?" / "Which image?" instead of refusing (tools_registry.needs_target). Standard test 22→10 wrong past guard, heldout2 20→6. Blind heldout3: 12 past guard, 26 refused, 7 ask-which. v5.0 gate is under 10 past guard, 0 refused on heldout3. Lesson from round 15: guard rules tuned on dev misses no longer move the blind set; training is needed, mainly argument shape (tab pairs for copy/move/translate/append_note). Fast loop: dump an adapter's raw picks once, rescore guard edits in seconds. Voice at Eleven v4 (1.49s→1.22s). 127 tools, knowledge 62/65, picker 395/484 unseen.


## v5.0 reality check (2026-10-02, Joshua set the goal to v5)

Round 22 (same recipe, fresh template data) was worse and less safe: 19 past the guard against 7 on standard. Nothing swapped. Two things stand between her and 5.0. (1) The picker: the sealed judge reads 12 wrong past the guard and 11 right picks refused, and the bar is under 10 and 0; a 0.5B model is at about 65 percent of phrasings right. (2) The architecture: `tools.act()` is still the exact regex router and it answers first, the model only sees what the router misses; 5.0 says nothing goes through the router. Removing it today would drop her well below what she does now. The notes say bigger bases crashed training on this Mac (Qwen3.5-0.8B twice), so a bigger head needs training off this machine, which is Joshua's call (cost). The free lever left is data from her own live misses, not templates.

## Next, in order

v4.18.1: screen bench on the Mac 11/15 (dead button fixed; login, cookies, search, form: the 1.7B stops early, try qwen3:8b for screen jobs or a nudge when no tool call comes). Then multi-hop deep research, then video as 4.19.

v4.18.0 shipped long work (planner.work: rounds, re-plan from her own record, carry the rest, journal in ~/.samantha/work) and a simpler badge that changes only at majors. Next: screen_bench real failures (search, form stop early; dead button claims success), then multi-hop deep research, then video (4.19). The 5.0 judge (sealed heldout6) still reads 12 past guard, 11 refused.

Round 20 shipped as v4.17.13. heldout3 is retired and open (a dev set now); eval/heldout6.jsonl is the sealed 5.0 judge: never print or read its rows, totals only, once per final candidate. Judge now: 12 past guard, 11 refused, 16 asked. Dev sets: standard, heldout2, heldout3, heldout4, heldout5.

Round 19 shipped as v4.17.12 (guard only; hands-adapter-round19 trained, more accurate on fresh wording but less safe, kept on disk). Blind heldout3: 9 past guard (under 10, first time), 23 refused. Round 20: guard-tune to round19's own dev mistakes until it is no less safe than shipped on standard, heldout2, heldout4, then check untouched heldout5, then heldout3 once. Refusals are the whole 5.0 gap.

Round 18 shipped as v4.17.11 (code-side argument shape, plain folder names resolve under home). Blind heldout3: 11 past guard, 23 refused, 7 asked. Round 19: training on argument shape, scored on standard, heldout2, heldout4, heldout5, then heldout3 once.

Round 17 shipped as v4.17.10: eval/heldout5.jsonl is a second readable dev set. Blind heldout3: 11 past guard, 26 refused, 7 asked (read twice in round 17, totals only, see BAKEOFF). The 26 refusals do not appear on any dev set, so round 18 is training: argument shape (tab pairs, paths copied verbatim), scored on standard, heldout2, heldout4, heldout5, then heldout3 once.

1. Read heldout4's remaining 6 refusals and 7 wrong picks, fix them (never train on heldout3).
2. Retrain argument shape via pick-dump scoring: generate with current adapter, rescore guard edits in seconds.
3. Score on standard and heldout2 only; read heldout3 once at the end if no worse.
4. If it clears 5.0 (under 10 wrong, 0 refused on heldout3), ship it with major-release docs pass (WHITEPAPER, landing, README, badge motif). If worse, write short BAKEOFF entry and plan round 18 from dev misses.
5. After training: run screen_bench.py on the Mac (needs qwen3:1.7b), paint one photo per style to see real ImageMagick output.
6. Cloud-side file splits: web/samantha.js (893) and web/demo.js (736) one per round, lowering Law 8 ceiling after each.

## Restart prompt

Paste this in a new session:

```
/loop work the Turing roadmap until v5.0.0, one round at a time (read docs/LOOP-HANDOFF.md), then /checkpoint.

Start here: round 16 shipped as v4.17.9. Read docs/LOOP-HANDOFF.md. Next round 17: read heldout4's 6 refusals and 7 wrong picks, fix them. Train argument shape (tab pairs for copy/move/translate/append_note) via pick-dump scoring: dump raw picks once with current adapter, rescore guard edits in seconds, never train on heldout3 rows. Score on standard (1959) and heldout2 (500) only. If no worse than round 16, read heldout3 once and report totals. If it clears 5.0 gate (under 10 wrong past guard, 0 refused on heldout3), ship it: mv hands-adapter hands-adapter-old && mv hands-adapter-round17 hands-adapter, then ./release.sh 5.0.0, major-release docs pass. If worse, BAKEOFF entry (totals only), keep shipped adapter, plan round 18.

Deploys are automatic after green push. TLDR only when reporting.
```
