# Turing loop handoff (2026-09-27, evening)

## What the loop is

Work toward v5.0.0: her own tool-calling head, fewer than ten wrong picks past the guard, zero right picks refused. One round at a time, measured against held-out test sets. Watch usage and taper on overage; hard stop at 90% session usage.

## Where things stand

v4.17.0 is released and live. ElevenLabs voice (Sarah) with on-disk cache; face window shows idle loop, switches to talking with mouth frozen between words. Voice/Face/Customize toggles in Mac app. Computer use focus: looks at screen after click, finds buttons via accessibility tree, runs up to 25 steps. Test bench (eval/screen_bench.py) passed all, caught three bugs. Picker false refusals 16→7. Knowledge 62/65. Picker 395/484 on unseen. 127 tools. Docs 100%.

## Next, in order

1. Guard tuning: fewer than ten wrong past the guard, zero right picks refused (current: 17 wrong, 36 refused on heldout3.jsonl).
2. Recheck held-out sets after changes; do not tune on them.
3. Run `python3 eval/bench.py` after each release.
4. Use `python3 app/chat.py`, `python3 app/tools.py`, `python3 scripts/stats.py` from root. Read `CLAUDE.md` for pre-push checks.

## Restart prompt

```
/loop work the Turing roadmap until the next major version (5.0.0), one round at a time, watching Claude usage and tapering on overage; hard stop at 90% session usage.
```
