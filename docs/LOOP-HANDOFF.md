# Turing loop handoff (2026-09-21, late night)

The live `/loop` for this repo. Checkpoint rewrites this file every run. A new session reads it and picks up where the last one stopped.

## What the loop is
Samantha to a 1.0.0 release, landing page to A+, and a standing gap hunt. Each iteration: look at what comparable assistants do that she cannot (Siri and Shortcuts, Apple Intelligence, Claude and ChatGPT desktop with MCP, Open Interpreter, Raycast AI, local Ollama agents), write the biggest real gap into `docs/GAPS.md` with where it was seen, then build the smallest honest fix. Every fix ships with its tests, `eval/laws.py` green, docs at 100 percent, the phone-size QA on the landing page, and CI green before the next iteration. `roadmap.md` "Road to 1.0.0" is the floor, the gap list is the ceiling.

## Rules
Headless always: `SAMANTHA_HEADLESS=1`, never pop Chrome or any app. Fix at the root cause, never edit a test to pass. **Check free disk and free memory before any training or eval, 6GB disk minimum. One heavy job at a time, `ollama stop` first.** On 2026-09-21 training plus an eval filled swap, swap filled the disk, and the shell died. Never block in a foreground wait loop: start slow jobs in the background and end the turn. Haiku subagents, one at a time. Stop at 90% usage.

## Where things stand
v0.10.0 is out, Apache 2.0. Samantha has 30 tools: the first 20 plus ten image tools that drive Pixelmator Pro (`tools_image.py`). She paints photos in Pixelmator (`pixelmator/pxm.py paint`), her own 0.5B picker chooses the tool (394/501 unseen, 9 wrong picks past the guard, 0 right picks refused), and PaintBar puts painting in the menu bar (`menubar/`). A build lock stops two Pixelmator jobs colliding. `./gate.sh --full` runs every eval against `eval/baseline.json` and `./release.sh X.Y.Z "note"` refuses to ship on a red CI, a worse score or a dirty tree, then tags, publishes and deploys. Landing: the chat demo types its own commands, paints on the stand-in Mac, has native autocomplete, a privacy page and an ember accent. Docstrings 92 percent, every source file cited in `docs/ARCHITECTURE.md`. Blender 5.2 LTS is installed and unused.

## Next, in order
1. Live smoke run for the nine Pixelmator image tools. Only `image_info` has run for real.
2. Two-step picking (family, then tool) and retrain the picker, BEFORE adding tools in bulk. `roadmap.md` "100 tools" has the families and the rules.
3. Blender family, then the Shortcuts bridge, then MCP both ways.
4. The harness for 1.0: one conversation that holds tool results, shows a live tool log and asks before anything that writes, sends or deletes.
5. Finish docstrings: 11 left outside `pixelmator/`, 28 inside `pixelmator/pxm.py`.
6. Painting is clear now: `pxm.py paint --engine magick` draws 40000 squares in about a second, and paint_image uses it (Pixelmator is the fallback and the watch-it-build showcase). Run the 5000 layer Pixelmator paint again only if the layered file is wanted.
7. Run ./release.sh with a patch bump and the full gate once Pixelmator is free.
8. Still open from before: re-run `eval/basic_questions.py`, score Ternary-Bonsai-4B as a borrowed head, score `voice-adapter`.

Lessons from 2026-09-21, keep them: helpers (Haiku agents) ship fast but need checking. One made the guard refuse "mute", one claimed 100 percent at 77, one left orphan builds running in Pixelmator. Read the diff, rerun the numbers, and wait for the real CI result before calling anything done.

## Restart prompt
```
/loop Drive Samantha (~/Documents/Code/turing) to 1.0.0 and the landing page to A+. Read docs/LOOP-HANDOFF.md, roadmap.md "Road to 1.0.0" and docs/GAPS.md first. Each iteration: find the biggest real gap between her and comparable assistants (search the web, cite where seen), log it in docs/GAPS.md, build the smallest honest fix with tests, run ./gate.sh and eval/laws.py, QA the landing page on a phone size, push, wait for CI green, release as you go with ./release.sh, refresh the landing page, README and CLAUDE.md. SAMANTHA_HEADLESS=1 always, docs 100 percent, disk 6GB and memory checked before heavy jobs, one at a time, watch Claude usage. Stop at v1.0.0 and send a notification.
```
