# Turing loop handoff (2026-09-26, evening)

## What the loop is

Work the Turing roadmap toward v5.0.0: her own tool-calling head, better picker accuracy, and research beyond Wikipedia. One round at a time, measured against held-out sets. Watch usage and taper on overage; hard stop at 90% session usage. This checkpoint saves the resume point; it does not restart training or the loop.

## Where things stand

v4.16.3 is released and live. The repository root went from 64 tracked files to 20: Python code in `app/`, helpers in `scripts/`, supporting documents in `docs/`. Imports, resource paths, launchers and CI follow those folders. The native GUI rebuilt. All local checks and GitHub test, release and deploy workflows passed; docs coverage is 100 percent. Model files and private data stayed in place.

The picker is unchanged: the third blind set (`eval/heldout3.jsonl`, 465 rows) measured 343 right, 17 wrong past the guard, and 36 right picks refused. Benchmarks remain router 10 microseconds, picker 194 milliseconds, answers 111 tokens/sec. Knowledge is 62/65 with zero confidently wrong; 126 tools. The last training loop stopped at 86% session usage.

## Next, in order

1. Improve guard refusals and wrong tool picks using training examples and development cases. Do not tune on the blind held-out cases or copy them into training.
2. Recheck the held-out sets after changes. The v5.0 gate remains fewer than ten wrong past the guard and zero right picks refused; the existing numbers do not meet it.
3. Run `python3 eval/bench.py` after each release and keep the reported measurements current.
4. Use `python3 app/chat.py`, `python3 app/tools.py`, and `python3 scripts/stats.py` from the repo root. Tests and eval commands keep their existing paths. Read `CLAUDE.md` for the full pre-push checks.

## Restart prompt

```
/loop work the Turing roadmap until the next major version (5.0.0), one round at a time, watching Claude usage and tapering on overage; hard stop at 90% session usage.
```
