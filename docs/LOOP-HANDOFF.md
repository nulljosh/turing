# Turing loop handoff (2026-09-23, late night)

## What the loop is

One ability per minor release, a major when a whole roadmap family completes, until version 10. Each round: a frontier check first (ChatGPT, Claude, Gemini, Apple Intelligence, Operator-style agents; any real gap goes under "Gaps found by the loop" in roadmap.md with where it was seen), then the easiest, most relevant open gap, built, dogfooded for real on this Mac (the new ability plus one old one), full gate plus every file in tests/ green, docs and landing page in the same commit, push, CI checked, a line in docs/PROGRESS.md. Celebrate at 5.0.0 and 6.0.0 (4.0.0 and 100 tools are done). Every version gets a tag and a GitHub release from release.yml.

## Where things stand

v4.3.0 cutting on main, 105 tools, docs 100%, laws hold, CI green. Merged: #69 mark redrawn every release (sanity gate: ink fraction, margin, no blob, must differ); #70 engraving centered above footer (A- by Joshua); #72 loss chart simplified (90 train, 0.316 val), picker from eval/baseline.json 75% unseen; #73 image tools to ImageMagick (10/10 smoke), Pixelmator retired; #74 CI fix (mark test skips without ImageMagick). In flight: constrained decoding. Site deploys, v4.3.0 auto-releases.

## Next, in order

1. Constrained decoding: logits processor limits picker to real tool names copied from sentence.
2. Picker round seven: teach "how many X is N Y" as literal copy (template fix), retrain, score vs round six.
3. Research beyond Wikipedia: arxiv, GitHub, Hacker News, search APIs.
4. Multi-step GUI flows: detect agent planning, ask yes or no per step before acting.

## Restart prompt

```
/loop until version 5 or 5.5. ultrathink
read docs/LOOP-HANDOFF.md first.
```
