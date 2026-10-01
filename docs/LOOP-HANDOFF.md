# Turing loop handoff (2026-10-01, late; v4.17.9, round 16 shipped)

## What the loop is

Work the Turing roadmap toward v5.0.0: her own tool-calling head, better picker accuracy, and research beyond Wikipedia. One round at a time, measured against held-out sets. Watch usage and taper on overage; hard stop at 90% session usage. This checkpoint saves the resume point; it does not restart training or the loop.

## Where things stand

v4.17.9 (2026-10-01 late): round 16 shipped. Fresh writer built heldout4.jsonl (455 rows, readable dev set mirroring heldout3); deictic "trash this file" / "crop this image" now asks "Which file?" / "Which image?" instead of refusing (tools_registry.needs_target). Standard test 22→10 wrong past guard, heldout2 20→6. Blind heldout3: 12 past guard, 26 refused, 7 ask-which. v5.0 gate is under 10 past guard, 0 refused on heldout3. Lesson from round 15: guard rules tuned on dev misses no longer move the blind set; training is needed, mainly argument shape (tab pairs for copy/move/translate/append_note). Fast loop: dump an adapter's raw picks once, rescore guard edits in seconds. Voice at Eleven v4 (1.49s→1.22s). 127 tools, knowledge 62/65, picker 395/484 unseen.

## Next, in order

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
