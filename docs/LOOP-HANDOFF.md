# Turing loop handoff (2026-09-25, early morning)

## What the loop is

One ability per minor release, a major when a whole roadmap family completes, until version 10. Each round: a frontier check first (ChatGPT, Claude, Gemini, Apple Intelligence, Operator-style agents; any real gap goes under "Gaps found by the loop" in roadmap.md with where it was seen), then the easiest, most relevant open gap, built, dogfooded for real on this Mac (the new ability plus one old one), full gate plus every file in tests/ green, docs and landing page in the same commit, push, CI checked, a line in docs/PROGRESS.md. Celebrate at 5.0.0 and 6.0.0 (4.0.0 and 100 tools are done). Every version gets a tag and a GitHub release from release.yml.

## Where things stand

v4.15.5 cutting (second blind held-out eval/heldout2.jsonl: 350/500, 20 wrong past guard, 16 refused; never read its rows or groups while tuning). Tapering since 90 percent weekly usage on 2026-09-25 05:00: CI and red fixes only, hourly, until Saturday 22:00. Before that v4.15.4 (round twelve: blind-data retrain rejected as less safe, guard kept, held-out refused 24 to 19; contaminated, second fresh held-out needed before 5.0. Shell gotcha: this Mac's eval shell is zsh, so an unquoted "$t" holding "--test path" passes one argument; use ${=t}). Before that v4.15.3 (held-out check: 361/512, 29 wrong past guard, 24 refused on blind phrasings; eval/hands.py --test). Before that v4.15.2 (round eleven: guard only, 9 wrong past guard, 0 refused, 1300/1895; tuned on the test set, so not yet a held-out number). Before that v4.15.1 (round ten: guard only, 50 wrong past guard, 0 refused; the round ten retrain was less safe and is kept on disk unshipped). Before that v4.15.0 (picker round nine: 1300/1895, 83 wrong past guard, 0 refused, guard extended for five tools; badge step 8, the Pleiades). Before that v4.14.0 (every proposed write checked against your words: intent.py, law 12; picker round eight shipped, 1194/1878, guard word lists for 36 tools, 134 wrong past guard, 2 refused; badge step 7, Scutum). Before that v4.13.0 (plans: planner.py, law 11; badge step 6, a compass rose and a dotted route). Before that v4.12.0 (follows the conversation: followup.py, law 10; badge step 5, a Milky Way band). Before that v4.11.1 (tools.py split, MAX_LINES 700) and v4.11.0 (learns from you: feedback.py, ratings caught before routing; badge step 4, a ringed planet). Before that v4.10.0 (safe reading: law 9, untrusted.py fences every read result; badge step 3, a crescent moon). Before that v4.9.0 (the dev family: git status, recent commits, run a repo's tests, open PRs, open a repo in the editor; badge step 2, a shooting star), 125 tools. THE LIVE SITE DOES NOT DEPLOY ITSELF: the repo has no CLOUDFLARE_API_TOKEN secret and the deploy job goes green anyway. After every release, deploy by hand from a clean worktree of HEAD (never the working tree, it may hold a builder's half-done edits): `git worktree add --detach /tmp/turing-clean HEAD && cd /tmp/turing-clean && npx wrangler deploy`, then check stats.json on the live site says the new version, docs 100 percent, laws hold. The loop runs on Joshua's Mac. main takes direct pushes (the "2 of 2 required status checks" line on push is a notice, the push lands); the pre-push hook in .githooks runs the CI steps first, so run `git config core.hooksPath .githooks` once per clone. Rounds: the main session briefs one Sonnet subagent to build, then checks, commits, pushes and watches CI itself (Joshua's cap: 3 Haiku/Sonnet or 2 Opus at once). Pace slowly while weekly usage is in deficit: it was 80 percent used, reset Saturday 22:00. oMLX (the 9B) is a brew service: `omlx start` if ask_llm answers error 500.

## Frontier gaps

roadmap.md "Gaps with frontier models" lists the six gaps Joshua cares about beyond compute (wording, planning, conversation memory, her own thinking, learning from use, trusting what she reads). Every round: re-check that list, prefer work that shrinks one, update its line when it moves, and add any new gap found by the frontier check there too.

## Next, in order

Re-read this file, README.md and roadmap.md at the start of every round and fix anything stale in the same pass (Joshua, 2026-09-25).

2. 5.0, judged by eval/heldout.jsonl (4.15.3: 361/512, 29 wrong past guard, 24 refused; bar is under 10 and 0). The held-out set is the judge and stays frozen: never write guard rules or templates from its rows. Improve from tool vocabulary and new blind training phrasings (written by a subagent that never reads heldout.jsonl), then score on it. Once a round is tuned while looking at held-out groups, write a second fresh held-out before declaring 5.0. Next round: the not-a-command misfires (chit-chat firing music/open_app) and the refused groups (calculate, copy_file, rename_file, convert_image, running_apps).
3. Planning, the rest: recover and re-plan when a step fails, instead of stopping.
5. Safe reading, the rest: a stronger check for screen clicks than the keyword blocklist.
6. Every minor: a new badge motif in tools_badge.MOTIFS (Joshua loves these), look at it at 2x before shipping.

## Restart prompt

```
/loop until version 10. ultrathink
keep close watch on usage. read docs/LOOP-HANDOFF.md first.
```
