# Turing loop handoff (2026-09-20, late evening)

The live `/loop` for this repo. Checkpoint rewrites this file every run. A new session reads it and picks up where the last one stopped.

*Updated 2026-09-20, Sunday night.*

## What the loop is
Samantha to a 1.0.0 release, landing page to A+. `roadmap.md` "Road to 1.0.0" is the queue.

## Rules
Headless always: `SAMANTHA_HEADLESS=1`, never pop Chrome or any app. Fix at the root cause, never edit a test to pass. Check free memory before any training. Haiku subagents, one at a time. Stop at 90% usage. One short ping per iteration.

## Where things stand
Shipped tonight: 13 tools, actions eval 54 of 54, knowledge 47 to 57 of 65, confidently wrong 18 to 4, a 1.7B model for her hands at about 5 seconds, article reader with a grounding check, logos built live in Pixelmator, new icon, landing page rebuilt around the chat with idle autoplay and release-style results. Self-grade B+.

The voice retrain finished cleanly at 20:50 into `voice-adapter/`, log in `voice-train.log`. Not scored yet, so live Samantha still runs on `ada-1-adapter`.

## Next, in order
1. Click through the landing chat in a real headless browser. Check phone width on the new layout.
2. Replace the green left stripe on the older answer blocks.
3. Score `voice-adapter` against `ada-1-adapter`. Delete `.http_cache.json` first. Swap only if it wins. Then refresh the loss chart with `parse_log.py`.
4. Knowledge to 60 of 65 with zero confidently wrong. Eight misses left. Check for stale reader cache first: two of the wrong ones passed when asked directly.
5. `SECURITY.md` is the one house doc missing. Docstring coverage is 36 percent.
6. Global `core.hooksPath` overrides this repo's pre-commit hook, so the eval gate never runs on commit. Chain it.
7. Roadmap boxes: personal tools, music, browser tabs, a real harness, her own tool-calling model.

## Restart prompt
Paste this to pick the loop back up:

```
/loop Drive Samantha (~/Documents/Code/turing) to a 1.0.0 release and the landing page to A+. Read docs/LOOP-HANDOFF.md and roadmap.md "Road to 1.0.0" first. One item per iteration, in the order the handoff lists. SAMANTHA_HEADLESS=1 always, never pop Chrome or any visible app. Verify with tools.py self-check, test_chat.py, eval/score.py, eval/actions.py and eval/basic_questions.py. Fix at the root cause, never edit a test to pass. Check free memory before any training. Commit, push, npx wrangler deploy for site changes, self-grade honestly, clean finished items out of roadmap.md. Haiku subagents only, one at a time. Stop at 90% usage. One short ping per iteration.
```
