# Turing loop handoff (2026-10-01, evening; v4.17.7, live)

## What the loop is

Work the Turing roadmap toward v5.0.0: her own tool-calling head, better picker accuracy, and research beyond Wikipedia. One round at a time, measured against held-out sets. Watch usage and taper on overage; hard stop at 90% session usage. This checkpoint saves the resume point; it does not restart training or the loop.

## Where things stand

v4.17.7 (2026-10-01 evening, shipped live): voice moved to ElevenLabs' Eleven v4 model via Text to Dialogue endpoint (faster: 1.49s→1.22s to first sound); Mac app voice.py still on flash v2.5. Picker round 14 trained but lost—candidate 1308/1959 right (88 wrong past guard, 7 refused) vs shipped 1312/1959 (22 past guard, 0 refused)—not shipped; hands-adapter-round14 held for reference. Gen_hands_data.py improvements ship: richer training templates for two-argument tools, guard evidence for old phrasings, null-ratio 0.163. Computer use: screen jobs look at frontmost app after every action (accessibility tree, OCR fallback), click by accessibility first, run up to 25 steps. eval/screen_bench.py all pass in the cloud but needs qwen3:1.7b on the Mac (Escape kill switch works, law 12 own-words check for screen clicks in place). define_word reads the Mac dictionary offline. Landing follows Astra. Headless never writes Desktop. Face animates on /face command (list_voices, set_voice, restyle, keep_look each priced before running; default: twee, strawberry blonde, glasses, cardigan). Worker /api/speak voices text for Joshua Tree, which speaks her Chat replies through its own sound card. Next: her face inside Joshua Tree's Chat (in progress), then landing demo.

## Next, in order

Round 16 shipped as v4.17.9: eval/heldout4.jsonl is the new readable dev set (mirrors heldout3); deictic "trash this file" asks which (tools_registry.needs_target). Blind heldout3 now 12 past guard, 26 refused, 7 asked. 5.0 needs under 10 and 0. Next: read heldout4's remaining 6 refusals and 7 past guard, then train argument shape for what guard rules cannot fix.

Round 15 shipped as v4.17.8, guard only: standard 22 to 10 past guard, heldout2 20 to 6, blind heldout3 flat (16 past, 32 refused). Guard tuning no longer moves the blind set. Round 16 is training: teach argument shape (tab pairs for copy/move/translate/append_note, paths copied verbatim), since most of the 32 refusals are the right tool with a malformed argument. Rescore fast with a one-time pick dump (`picks.py dump`, then rescore guard edits in seconds), never on heldout3 rows.

Round 14 is done and lost. Next round 15: retrain from dev-set misses only (new training data + guard in app/tools_registry.py), never from heldout3.

1. Run screen_bench.py on the Mac with qwen3:1.7b (fix what fails).
2. Split web/samantha.js (893 lines) and web/demo.js (736 lines) one per round behind the full check set; lower Law 8 ceiling after each.
3. The v5.0 gate is fewer than ten wrong past the guard and zero right picks refused on the blind heldout3 set. Current best: round 13 guard (heldout3 only) is 350/500 right, 19 wrong past guard, 16 refused. Round 14 training made it worse. Training from dev misses in round 15 is the next attempt.
4. Use `python3 app/chat.py`, `python3 app/tools.py`, and `python3 scripts/stats.py` from the repo root. Tests and eval commands keep their existing paths. Read `CLAUDE.md` for the full pre-push checks.

## Needs Joshua (the Mac)

Round 14 is done on the Mac. Next:

- `python3 eval/screen_bench.py` (needs qwen3:1.7b in Ollama) and press Escape once during a screen job.
- Painting styles (v4.17.4) were previewed with Pillow in the cloud (its ImageMagick blocks `-draw @file`). Paint one photo per style on the Mac once to see real magick output. They are a minor-release ability; 4.18.0 waits for its badge motif (magick, potrace, OCR on the Mac).

## Cloud work (round 15)

Retrain the picker from dev-set misses only (new training templates in gen_hands_data.py, guard evidence in tools_registry.py), no blind heldout3 reads. Use the shipped recipe (900 iterations, batch 8, learning rate 1e-4, 16 layers). Score on standard (1959) and heldout2 (500) only. If no less safe than round 13 on both, run heldout3 read once and report totals. If worse, write BAKEOFF entry (totals only) and plan round 16 from dev misses again.

Next after round 15 passes, cloud-side splits: web/samantha.js (893) and web/demo.js (736), one per round behind the full check set, lowering Law 8 ceiling after each. Then eval/gen_heldout2.py (647).

## Restart prompt

Paste this in a new session:

```
/loop work the Turing roadmap until 5.0.0, one round at a time, watching Claude usage (taper to CI checks and red fixes on overage or an allowed_warning status; hard stop at 90% session usage).

Start here: round 14 has finished (lost). Read docs/LOOP-HANDOFF.md and docs/BAKEOFF.md. Next round 15: retrain from dev-set misses only (training data + guard in app/tools_registry.py), shipped recipe (900 iter, batch 8, lr 1e-4, 16 layers), score on standard (1959) and heldout2 (500) only. Never read heldout3 rows or train on them.

After round 15:
1. If round 15 is no less safe than round 13 on both standard and heldout2, read heldout3 once and report totals. If it clears 5.0 (under 10 wrong past guard, 0 refused), ship it (mv hands-adapter hands-adapter-old && mv hands-adapter-round15 hands-adapter, then ./release.sh 5.0.0) and do the major-release docs pass (WHITEPAPER, landing, README, badge motif).
2. If round 15 is worse, write a short BAKEOFF.md entry (totals only), keep shipped adapter, plan round 16 from dev misses.
3. After training: run screen_bench.py on the Mac (fix what fails), paint one photo per style to see real ImageMagick output.
4. Cloud-side splits after round 15 passes: web/samantha.js and web/demo.js one per round, lowering Law 8 ceiling after each.

Deploys are automatic after green push. TLDR only when reporting.
```
