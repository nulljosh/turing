# Turing loop handoff (2026-09-25, early morning)

## What the loop is

One ability per minor release, a major when a whole roadmap family completes, until version 10. Each round: a frontier check first (ChatGPT, Claude, Gemini, Apple Intelligence, Operator-style agents; any real gap goes under "Gaps found by the loop" in roadmap.md with where it was seen), then the easiest, most relevant open gap, built, dogfooded for real on this Mac (the new ability plus one old one), full gate plus every file in tests/ green, docs and landing page in the same commit, push, CI checked, a line in docs/PROGRESS.md. Celebrate at 5.0.0 and 6.0.0 (4.0.0 and 100 tools are done). Every version gets a tag and a GitHub release from release.yml.

## Where things stand

v4.13.0 cutting (plans: planner.py, law 11; badge step 6, a compass rose and a dotted route). Before that v4.12.0 (follows the conversation: followup.py, law 10; badge step 5, a Milky Way band). Before that v4.11.1 (tools.py split, MAX_LINES 700) and v4.11.0 (learns from you: feedback.py, ratings caught before routing; badge step 4, a ringed planet). Before that v4.10.0 (safe reading: law 9, untrusted.py fences every read result; badge step 3, a crescent moon). Before that v4.9.0 (the dev family: git status, recent commits, run a repo's tests, open PRs, open a repo in the editor; badge step 2, a shooting star), 125 tools. THE LIVE SITE DOES NOT DEPLOY ITSELF: the repo has no CLOUDFLARE_API_TOKEN secret and the deploy job goes green anyway. After every release, deploy by hand from a clean worktree of HEAD (never the working tree, it may hold a builder's half-done edits): `git worktree add --detach /tmp/turing-clean HEAD && cd /tmp/turing-clean && npx wrangler deploy`, then check stats.json on the live site says the new version, docs 100 percent, laws hold. The loop runs on Joshua's Mac. main takes direct pushes (the "2 of 2 required status checks" line on push is a notice, the push lands); the pre-push hook in .githooks runs the CI steps first, so run `git config core.hooksPath .githooks` once per clone. Rounds: the main session briefs one Sonnet subagent to build, then checks, commits, pushes and watches CI itself (Joshua's cap: 3 Haiku/Sonnet or 2 Opus at once). Pace slowly while weekly usage is in deficit: it was 80 percent used, reset Saturday 22:00. oMLX (the 9B) is a brew service: `omlx start` if ask_llm answers error 500.

## Frontier gaps

roadmap.md "Gaps with frontier models" lists the six gaps Joshua cares about beyond compute (wording, planning, conversation memory, her own thinking, learning from use, trusting what she reads). Every round: re-check that list, prefer work that shrinks one, update its line when it moves, and add any new gap found by the frontier check there too.

## Next, in order

Re-read this file, README.md and roadmap.md at the start of every round and fix anything stale in the same pass (Joshua, 2026-09-25).

2. 5.0 prep, her own head: retrain the picker on the templates plus training/feedback_to_data.py rows, score with eval/hands.py against round six. Check free memory first, never two mlx_lm.lora jobs at once.
3. Planning, the rest: recover and re-plan when a step fails, instead of stopping.
5. A second model that checks each planned write against the user's own words (the rest of the safe-reading gap).
6. Every minor: a new badge motif in tools_badge.MOTIFS (Joshua loves these), look at it at 2x before shipping.

## Restart prompt

```
/loop until version 10. ultrathink
keep close watch on usage. read docs/LOOP-HANDOFF.md first.
```
