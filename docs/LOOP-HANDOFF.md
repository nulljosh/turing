# Turing loop handoff (2026-09-24, night, back on the Mac)

## What the loop is

One ability per minor release, a major when a whole roadmap family completes, until version 10. Each round: a frontier check first (ChatGPT, Claude, Gemini, Apple Intelligence, Operator-style agents; any real gap goes under "Gaps found by the loop" in roadmap.md with where it was seen), then the easiest, most relevant open gap, built, dogfooded for real on this Mac (the new ability plus one old one), full gate plus every file in tests/ green, docs and landing page in the same commit, push, CI checked, a line in docs/PROGRESS.md. Celebrate at 5.0.0 and 6.0.0 (4.0.0 and 100 tools are done). Every version gets a tag and a GitHub release from release.yml.

## Where things stand

v4.6.0 cutting (edit any file, write code to disk), 109 tools, docs 100 percent, laws hold. The loop runs on Joshua's Mac again: the cloud session was killed 2026-09-24 night; the jt-chat branch, PR #94 and two stale /private/tmp worktrees were retired, all already on main. main is branch-protected (2 required checks), so every round ships as a PR with auto-merge, not a push to main; CLAUDE.md's "no PRs" line is older than that rule. Joshua's rule for rounds: the main session delegates each build to a subagent (max 3 Haiku/Sonnet, or max 2 Opus) and keeps the checks, PR and CI itself. Weekly usage 79 percent at this write, resets Saturday 22:00.

## Next, in order

0. Dogfood 4.6 for real with the 9B warm: edit_file on a Desktop note, write_code to a .py, run it.

1. Constrained decoding: logits processor limits picker to real tool names copied from sentence.
2. Picker round seven: teach "how many X is N Y" as literal copy (template fix), retrain, score vs round six.
3. Research beyond Wikipedia: arxiv, GitHub, Hacker News, search APIs.
4. Multi-step GUI flows: detect agent planning, ask yes or no per step before acting.

## Restart prompt

```
/loop until version 5 or 5.5. ultrathink
read docs/LOOP-HANDOFF.md first.
```
