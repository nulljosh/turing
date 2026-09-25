# Turing loop handoff (2026-09-23, late night)

## What the loop is

One ability per minor release, a major when a whole roadmap family completes, until version 10. Each round: a frontier check first (ChatGPT, Claude, Gemini, Apple Intelligence, Operator-style agents; any real gap goes under "Gaps found by the loop" in roadmap.md with where it was seen), then the easiest, most relevant open gap, built, dogfooded for real on this Mac (the new ability plus one old one), full gate plus every file in tests/ green, docs and landing page in the same commit, push, CI checked, a line in docs/PROGRESS.md. Celebrate at 5.0.0 and 6.0.0 (4.0.0 and 100 tools are done). Every version gets a tag and a GitHub release from release.yml.

v4.5.0 live on main, 107 tools, docs 100 percent, badge by Samantha live (CSS mask fixed for dark page). Loop to v5.0: next is 4.6 (edit any file, write code), then 5.0 her own head.

Rules from Joshua (2026-09-25): a TLDR progress report when the loop starts and after every round; log every change in docs/PROGRESS.md; each round goes up as a PR and the loop merges it into main once CI is green; stop new work when Claude usage nears its limit (`rate_limit_info.status` anything but `allowed`, e.g. `allowed_warning`): CI checks, red fixes and merging open PRs only, as CLAUDE.md's Usage section says.

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
