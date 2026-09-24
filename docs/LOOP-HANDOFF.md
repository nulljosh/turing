# Turing loop handoff (2026-09-23, late evening)

## What the loop is

One ability per minor release, a major when a roadmap family completes, until version 5.0 or 5.5. Each round: frontier check first (ChatGPT, Claude, Gemini, Apple Intelligence, Operator-style agents; gaps logged in roadmap.md), then build the easiest relevant item, dogfood on this Mac, full gate (docs 100%, tests green), land on main, tag, release. Loop targets version 5 (her own head to pick/research/remember) or 5.5 if intermediate milestones earn it.

## Where things stand

v4.2.0 on main, 105 tools, docs 100%, laws all hold, CI green. Roadmap restructured with majors section (5.0-8.0, each with one check). Recent PRs: #66 roadmap majors (versions 5.0 her own head, 6.0 everywhere, 7.0 remembers and comes to you, 8.0 learns from frontier teachers, each with single check); #67 gui/package.sh signed installer (waits on Developer ID Application cert); #68 mark centered above landing footer, deployed. Open PRs: #69 redraw mark at every release (junk filter adding before merge), constrained decoding for picker in flight, ImageMagick port in flight. New standing rule: image work through ImageMagick only, never Pixelmator Pro again (feedback_no_pixelmator_use_imagemagick.md). v4.3.0 auto-release waits for ImageMagick port to land.

## Next, in order

1. ImageMagick port lands (CLI wrapper, same results as Pixelmator but no UI needed; painting tools via tools_image.py subprocess).
2. v4.3.0 auto-cut once port passes CI.
3. Constrained decoding result (logits processor limits output to real tool names copied from sentence).
4. Picker round seven: teach "how many X is N Y" as literal copy, retrain, score vs round six (same matched test set).
5. Research beyond Wikipedia: arxiv, GitHub, Hacker News, search APIs where they exist.
6. Picker loop continues until 85+ matched on unseen.

## Restart prompt

```
/loop until version 5 or 5.5. ultrathink
read docs/LOOP-HANDOFF.md first. ImageMagick port is the blocker for v4.3.0.
```
