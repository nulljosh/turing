# Turing loop handoff (2026-09-21, late night)

The live `/loop` for this repo. Checkpoint rewrites this file every run. A new session reads it and picks up where the last one stopped.

## What the loop is
Samantha to a 1.0.0 release, landing page to A+. `roadmap.md` "Road to 1.0.0" is the queue.

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
6. A 20000 layer, --detail 512 Mona Lisa was building headless in Pixelmator to /tmp/pxmtest/m20k.png. Look at it. If crystal clear, raise paint defaults (--shapes, --detail) to match. If not, iterate.
7. Run ./release.sh with a patch bump and the full gate once Pixelmator is free.
8. Rebuild web/mona-lisa.gif and web/last-supper.gif at the new quality.
9. Still open from before: re-run `eval/basic_questions.py`, score Ternary-Bonsai-4B as a borrowed head, score `voice-adapter`.

Lessons from 2026-09-21, keep them: helpers (Haiku agents) ship fast but need checking. One made the guard refuse "mute", one claimed 100 percent at 77, one left orphan builds running in Pixelmator. Read the diff, rerun the numbers, and wait for the real CI result before calling anything done.

## Restart prompt
```
/loop Drive Samantha (~/Documents/Code/turing) to a 1.0.0 release and the landing page to A+. Read docs/LOOP-HANDOFF.md and roadmap.md "Road to 1.0.0" first. One item per iteration, in the order the handoff lists. SAMANTHA_HEADLESS=1 always. Check free disk (6GB) and memory before any heavy job, one at a time, never block in a foreground wait. Verify with tools.py, test_chat.py, eval/actions.py, eval/web_parity.py, eval/web_demo.py, eval/hands.py and eval/basic_questions.py. Fix at the root cause. Commit, push, npx wrangler deploy for site changes, self-grade honestly. Haiku subagents only, one at a time. Stop at 90% usage. One short ping per iteration.
```
