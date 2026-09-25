# Turing loop handoff (2026-09-24, night, back on the Mac)

## What the loop is

One ability per minor release, a major when a whole roadmap family completes, until version 10. Each round: a frontier check first (ChatGPT, Claude, Gemini, Apple Intelligence, Operator-style agents; any real gap goes under "Gaps found by the loop" in roadmap.md with where it was seen), then the easiest, most relevant open gap, built, dogfooded for real on this Mac (the new ability plus one old one), full gate plus every file in tests/ green, docs and landing page in the same commit, push, CI checked, a line in docs/PROGRESS.md. Celebrate at 5.0.0 and 6.0.0 (4.0.0 and 100 tools are done). Every version gets a tag and a GitHub release from release.yml.

## Where things stand

v4.8.0 cutting (the system family: dark mode, running apps, quit an app, bluetooth status, Do Not Disturb through a Shortcut; the footer badge now modernizes one notch per minor via tools_badge.py), 120 tools, docs 100 percent, laws hold. The loop runs on Joshua's Mac. main takes direct pushes (the "2 of 2 required status checks" line on push is a notice, the push lands); the pre-push hook in .githooks runs the CI steps first, so run `git config core.hooksPath .githooks` once per clone. Rounds: the main session briefs one Sonnet subagent to build, then checks, commits, pushes and watches CI itself (Joshua's cap: 3 Haiku/Sonnet or 2 Opus at once). Pace slowly while weekly usage is in deficit: it was 80 percent used, reset Saturday 22:00. oMLX (the 9B) is a brew service: `omlx start` if ask_llm answers error 500.

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
