# Turing loop handoff (2026-10-03, night)

**Loop status: stopped as of 2026-10-02.** Tonight's one live job: a Kaggle GPU run (1.5B base, `joshuatrommel/samantha-hands-train`, kernel version 5) trains a bigger picker. When it finishes, fetch it with `uvx kaggle kernels output`, then follow docs/KAGGLE.md to convert and score it on standard and heldout2. Restart prompt below for when to resume.

## What the loop is

Work toward v5.0.0 (her own tool-calling head, better picker accuracy, research beyond Wikipedia). Loop target: until v5.0.0 on this Mac, then v10.0.0 in order (7.0, 6.0, 8.0, 9.0, 10.0). Hard stop and checkpoint at 90% usage. One round at a time, measured against held-out sets. v5.0 waiting on free GPU training (Joshua running Kaggle this weekend).

## Where things stand

v4.19.1 shipped (2026-10-02): free GPU training package added (training/kaggle_train.py, docs/KAGGLE.md, hands-data/samantha-hands.zip). v5.0 gate unchanged: under 10 wrong past guard and 0 refused on sealed test heldout6. Currently 12 wrong and 11 refused. Template-data training rounds parked after round 22 proved less safe. Loop waits for real feedback: type "good" or "wrong" in chat, saved to ~/.samantha/feedback.jsonl. Retrain at 60+ rows via `python3 training/feedback_to_data.py`, then `training/picker_round.sh <next>`. Joshua runs Kaggle training this weekend; sealed test will move when that passes. 127 tools, knowledge 62/65, picker 395/484 unseen, voice Eleven v4.


## v5.0 reality check (2026-10-02, Joshua set the goal to v5)

Round 22 (same recipe, fresh template data) was worse and less safe: 19 past the guard against 7 on standard. Nothing swapped. Two things stand between her and 5.0. (1) The picker: the sealed judge reads 12 wrong past the guard and 11 right picks refused, and the bar is under 10 and 0; a 0.5B model is at about 65 percent of phrasings right. (2) The architecture: `tools.act()` is still the exact regex router and it answers first, the model only sees what the router misses; 5.0 says nothing goes through the router. Removing it today would drop her well below what she does now. The notes say bigger bases crashed training on this Mac (Qwen3.5-0.8B twice), so a bigger head needs training off this machine, which is Joshua's call (cost). The free lever left is data from her own live misses, not templates. There are none yet: ~/.samantha/feedback.jsonl does not exist (feedback is typing "good" or "wrong" in her chat, or "wrong, I meant X"). Loop rule until it fills: check that file once an hour and do nothing else; at 60 or more rows run `python3 training/feedback_to_data.py`, then `training/picker_round.sh <next>`, and ship only if no less safe. No more template-data rounds (round 22 proved they do not move the judge).

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

Loop paused. Paste this when ready to resume:

```
/loop work the Turing roadmap until v5.0.0, one round at a time (read docs/LOOP-HANDOFF.md), then /checkpoint.

Start here: v4.19.1 shipped with free GPU training package (training/kaggle_train.py, docs/KAGGLE.md). v5.0 gate blocked on sealed test: 12 wrong past guard and 11 refused, need under 10 and 0. Joshua running Kaggle training this weekend. Until that completes, watch ~/.samantha/feedback.jsonl for real user feedback (chat "good" or "wrong") and retrain at 60+ rows via training/feedback_to_data.py and training/picker_round.sh. On Kaggle success, run eval/hands.py --trained to confirm the new model moves the sealed test score. If it clears 5.0 gate, ship it with major-release docs pass (WHITEPAPER, landing, README, badge). Template-data rounds are parked; no more until feedback data drives training.

Deploys are automatic after green push. Hard stop at 90% session usage. TLDR only when reporting.
```
