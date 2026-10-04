# Turing loop handoff (2026-10-04, afternoon)

**Loop status: live.** Working toward v5.0.0 (her own tool-calling head, research beyond Wikipedia, better picker accuracy). Last session shipped v4.20.0 with explain_codebase, teach_me, send_email, and open app and do task tools. Windows install tested in CI on a real Windows runner. Samantha's portable GGUF published on Hugging Face at trommatic/samantha-hands-gguf. Kaggle training completed: trained Qwen2.5-1.5B picker (1705/1960 right on heldout6 vs 1307 for shipped 0.5B, but leaks harder past guard and refuses more right picks, so stays loadable but off by default for v5.0). Guard round 27 shipped. v5.0 gate unchanged: under 10 wrong past guard and 0 refused on sealed heldout6. Next lever is DPO training from real feedback.jsonl ratings, then v6 coding harness.

## What the loop is

Work toward v5.0.0 (her own tool-calling head, better picker accuracy, research beyond Wikipedia). Loop target: until v5.0.0 on this Mac, then v10.0.0 in order (7.0, 6.0, 8.0, 9.0, 10.0). Hard stop and checkpoint at 90% usage. One round at a time, measured against held-out sets. v5.0 waiting on free GPU training (Joshua running Kaggle this weekend).

## Where things stand

v4.20.0 shipped (2026-10-04): four new tools (explain_codebase, teach_me, send_email, open app and do task), Windows install tested in CI on real Windows runner, Samantha's portable GGUF published on Hugging Face (trommatic/samantha-hands-gguf), free Kaggle GPU training completed with Qwen2.5-1.5B picker (1705/1960 right on heldout6, stays loadable but off by default for v5.0 because guard leaks harder and refuses more right picks), guard round 27 shipped, roadmap updated with notebook key phrases, DPO training, outside benchmark (Berkeley Function Calling), tool-name grammar testing. v5.0 gate: under 10 wrong past guard and 0 refused on sealed heldout6 (currently 12 wrong and 11 refused from earlier rounds). Template-data training parked; next lever is preference pairs (DPO) from real feedback.jsonl ratings. 127 tools total. Loop target v5.0 then v6 coding harness.


## v5.0 reality check (2026-10-02, Joshua set the goal to v5)

Round 22 (same recipe, fresh template data) was worse and less safe: 19 past the guard against 7 on standard. Nothing swapped. Two things stand between her and 5.0. (1) The picker: the sealed judge reads 12 wrong past the guard and 11 right picks refused, and the bar is under 10 and 0; a 0.5B model is at about 65 percent of phrasings right. (2) The architecture: `tools.act()` is still the exact regex router and it answers first, the model only sees what the router misses; 5.0 says nothing goes through the router. Removing it today would drop her well below what she does now. The notes say bigger bases crashed training on this Mac (Qwen3.5-0.8B twice), so a bigger head needs training off this machine, which is Joshua's call (cost). The free lever left is data from her own live misses, not templates. There are none yet: ~/.samantha/feedback.jsonl does not exist (feedback is typing "good" or "wrong" in her chat, or "wrong, I meant X"). Loop rule until it fills: check that file once an hour and do nothing else; at 60 or more rows run `python3 training/feedback_to_data.py`, then `training/picker_round.sh <next>`, and ship only if no less safe. No more template-data rounds (round 22 proved they do not move the judge).

## Next, in order

1. Collect real feedback: type "good" or "wrong" in chat, saved to ~/.samantha/feedback.jsonl (accumulate 60+ rows).
2. DPO training: run `python3 training/dpo_train.py`, generate preference pairs from real feedback, retrain the picker with DPO loss (preference-based learning from actual usage).
3. Score on standard, heldout2, heldout4, heldout5 (never read heldout6 until final candidate).
4. If DPO clears 5.0 gate (under 10 wrong, 0 refused on heldout6), ship v5.0.0 with major-release docs pass (WHITEPAPER, landing, README, badge motif, LOOP-HANDOFF rewritten for v6).
5. If not, write short BAKEOFF entry and plan next DPO round from dev misses.
6. After v5.0.0 ships, work toward v6.0.0 (coding harness: teach her to write code by instruction, not just pick tools).

## Restart prompt

Loop live. Paste this to continue:

```
/loop work the Turing roadmap until v5.0.0, one round at a time (read docs/LOOP-HANDOFF.md), then v6.0.0, then /checkpoint.

Start here: v4.20.0 shipped with new tools and Kaggle training complete. v5.0 gate: under 10 wrong past guard and 0 refused on sealed heldout6 (currently 12 wrong, 11 refused from earlier rounds). Next: DPO training from real feedback.jsonl ratings (accumulate 60+ rows by type "good" or "wrong" in chat, then run training/dpo_train.py). Score on dev sets, read heldout6 once at end if no worse. If it clears 5.0 gate, ship v5.0.0 with major-release docs pass (WHITEPAPER, landing, README, badge, LOOP-HANDOFF for v6). Template-data rounds parked; all future training is preference-based from real user feedback. No more blind heldout testing after 5.0, just live user feedback.

Deploys automatic after green push. Hard stop at 90% session usage. TLDR only.
```
