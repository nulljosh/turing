# Turing loop handoff (2026-09-21, late evening)

The live `/loop` for this repo. Checkpoint rewrites this file every run. A new session reads it and picks up where the last one stopped.

## What the loop is
Samantha to a 1.0.0 release, landing page to A+. `roadmap.md` "Road to 1.0.0" is the queue.

## Rules
Headless always: `SAMANTHA_HEADLESS=1`, never pop Chrome or any app. Fix at the root cause, never edit a test to pass. **Check free disk and free memory before any training or eval, 6GB disk minimum. One heavy job at a time, `ollama stop` first.** On 2026-09-21 training plus an eval filled swap, swap filled the disk, and the shell died. Never block in a foreground wait loop: start slow jobs in the background and end the turn. Haiku subagents, one at a time. Stop at 90% usage.

## Where things stand
Shipped and all pushed/deployed: music and personal tools (19 tools, actions 77/77). Landing page is a working demo: her router runs in the browser, a stand-in Mac reacts, she can change the page itself, a model picks tools the rules miss behind a guard, lookups are live via wttr.in JSON (1200 char cap per reply). Security pass: CSP, JSON-only same-origin API, no eval, injection tests in `eval/web_demo.py`, SECURITY.md written. Live QA passed: web_demo.py tests weather, bad places, every chip, idle-reel lines (0 failures, 0 console errors); web_parity.py passes 77/77. Fixed complex logo routing (no adjectives allowed before "logo"). Knowledge 62/65 (one regression in code, not re-run yet). Her own tool picker trained twice: 395/484 on unseen phrasings against 30/463 for the regex. Self-grade A on the site and evals.

## Next, in order
1. Train round three of the picker, alone: the command is in `gen_hands_data.py`'s docstring neighbourhood, data is in `hands-data/`. 600 iters, batch 8, lr 1e-4, `--mask-prompt`. Then `eval/hands.py --adapter hands-adapter --verbose`.
2. Re-run `eval/basic_questions.py` to confirm the sky fix and zero confidently wrong.
3. Score Ternary-Bonsai-4B as a borrowed head: `eval/hands.py --model prism-ml/Ternary-Bonsai-4B-mlx-2bit` with `HF_HOME=/Volumes/LaCie/llm/huggingface`.
4. Update the landing page Limitations text and `web/stats.json` with the new knowledge and picker numbers. README too.
5. Score `voice-adapter` against `ada-1-adapter`. Still unscored.
6. Roadmap boxes left: browser tabs, a real harness that asks before writes, the rest of her own head.
7. Idea parked: train the tiny from-scratch model in `scratch/` with three-value weights, the Bonsai trick at a size this Mac can do.

## Restart prompt
```
/loop Drive Samantha (~/Documents/Code/turing) to a 1.0.0 release and the landing page to A+. Read docs/LOOP-HANDOFF.md and roadmap.md "Road to 1.0.0" first. One item per iteration, in the order the handoff lists. SAMANTHA_HEADLESS=1 always. Check free disk (6GB) and memory before any heavy job, one at a time, never block in a foreground wait. Verify with tools.py, test_chat.py, eval/actions.py, eval/web_parity.py, eval/web_demo.py, eval/hands.py and eval/basic_questions.py. Fix at the root cause. Commit, push, npx wrangler deploy for site changes, self-grade honestly. Haiku subagents only, one at a time. Stop at 90% usage. One short ping per iteration.
```
