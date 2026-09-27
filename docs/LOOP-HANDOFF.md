# Turing loop handoff (2026-09-26, evening)

## What the loop is

Work the Turing roadmap toward v5.0.0 (her own tool-calling head, improved picker accuracy, research beyond Wikipedia). One round at a time: ship features, run evals, measure against blind held-out sets. Watch Claude usage and taper on overage; hard stop at 90% session usage.

## Where things stand

v4.16.2 shipped with third blind held-out set eval (heldout3.jsonl, 465 rows). Results: 343 right (74%), 36 right picks refused (guard conservative), 17 wrong past guard (8/5 vs baseline). Benchmarks stable: router 10 µs, picker 194 ms, 111 tokens/sec. Knowledge 62/65 correct (zero confidently wrong), tools at 126 total. Loop wrapped at 86% session usage Saturday evening.

## Next, in order

1. Attack the 36 refusals on heldout3 (guard layer only; never tune directly on heldout3 breakdown numbers, the set is blind).
2. Fix the 17 past-guard errors (picker refinement, ask template improvements, extraction shortcuts).
3. Run eval/bench.py after each release and report to README.
4. v5.0 gate: <10 wrong, 0 refused across all three held-out sets.

## Restart prompt

```
/loop work the Turing roadmap until the next major version (5.0.0), one round at a time, watching Claude usage and tapering on overage; hard stop at 90% session usage.
```
