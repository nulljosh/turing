# Turing loop handoff (2026-09-23, evening)

## What the loop is

One ability per minor release, a major when a whole roadmap family completes, until version 10. Each round: a frontier check first (ChatGPT, Claude, Gemini, Apple Intelligence, Operator-style agents; any real gap goes under "Gaps found by the loop" in roadmap.md with where it was seen), then the easiest, most relevant open gap, built, dogfooded for real on this Mac (the new ability plus one old one), full gate plus every file in tests/ green, docs and landing page in the same commit, push, CI checked, a line in docs/PROGRESS.md. Celebrate at 5.0.0 and 6.0.0 (4.0.0 and 100 tools are done). Every version gets a tag and a GitHub release from release.yml.

## Where things stand

v4.2.0 on main, 105 tools, docs 100%, laws all hold, CI green. Six items landed since last handoff: picker round six (PR #55, 77 of 105 tools matched on unseen); run_code sandboxed Python (PR #57); see_camera for vision (PR #59); GGUF plus llama.cpp backend for Windows/Linux via Modelfile (PR #60); Pixelmator race condition fixed (PR #61); landing refreshed (PR #62); voice barge-in and wake word (PR #63); Samantha drew her own mark, an engraved 1970s portrait (PR #64). All merged main, tagged, released, deployed live. README trimmed to essentials. Picker template bug found: "how many miles is 5 km" stays unfixed, she still writes "5 km to miles".

## Next, in order

1. Item 6 research half: pages beyond Wikipedia, follow-up questions, cite the sources.
2. Item 7 install: a signed, notarized SamanthaGUI.app that fetches models on first run, not on demand in the middle of a chat.
3. Picker round seven: teach "how many X is N Y" as a literal copy via template fix, retrain, same matched scoring as round six.
4. Research loop: turn follow-ups into a fresh search, return only new facts (not repeats from the first brief).
5. Multi-step GUI flows: detect when Samantha plans a flow, ask yes/no per step before acting.
6. Beyond Wikipedia: arxiv, GitHub, Hacker News, search APIs where they exist.

## Restart prompt

```
/loop until version 10. ultrathink
keep close watch on usage. read docs/LOOP-HANDOFF.md first.
```
