# Turing loop handoff (2026-09-26, evening)

## What the loop is

Work the Turing roadmap toward v5.0.0: her own tool-calling head, better picker accuracy, and research beyond Wikipedia. One round at a time, measured against held-out sets. Watch usage and taper on overage; hard stop at 90% session usage. This checkpoint saves the resume point; it does not restart training or the loop.

## Where things stand

v4.17.0 (2026-09-27): the guard refuses fewer right picks (heldout2 dev set 16 refused down to 7, standard set wrong-past-guard held at 9). Computer use is this week's focus: screen jobs look at the frontmost app after every action (accessibility tree, OCR fallback), click by accessibility first, run up to 25 steps, stop when stuck, and nudge a narrated step into a real call. eval/screen_bench.py drives a simulated app with the real qwen3:1.7b: all injection and failure scenarios pass; most tasks failed on the first run because of bugs it found (calls written as text, misnamed arguments), which are fixed, so rerun it for the new number. define_word reads the Mac dictionary offline. The landing page follows the Astra layout system. Headless runs never write to the Desktop. Name snapping was tried and dropped. GitHub issues went from 47 open to 27.

## Next, in order

1. Improve guard refusals and wrong tool picks using training examples and development cases. Do not tune on the blind held-out cases or copy them into training.
2. Recheck the held-out sets after changes. The v5.0 gate remains fewer than ten wrong past the guard and zero right picks refused; the existing numbers do not meet it.
3. Run `python3 eval/bench.py` after each release and keep the reported measurements current.
4. Use `python3 app/chat.py`, `python3 app/tools.py`, and `python3 scripts/stats.py` from the repo root. Tests and eval commands keep their existing paths. Read `CLAUDE.md` for the full pre-push checks.

## Next, in order (this week)

1. Rerun `eval/screen_bench.py` and fix what it finds until every task passes; then the kill switch (Escape stops a screen job) and law 12 for screen clicks.
2. Keep closing GitHub issues (27 open): each one shipped, merged into a duplicate, or moved to the roadmap with a reason.
3. Picker: v5.0 still needs fewer than ten wrong past the guard and zero refused on the blind third set.

## Restart prompt

```
/loop work the Turing roadmap until the next major version (5.0.0), one round at a time, watching Claude usage and tapering on overage; hard stop at 90% session usage.
```
