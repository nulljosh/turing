# Turing loop handoff (2026-09-25, 22:45)

## What the loop is

Turing builds small language models on-device. Samantha is the first (Qwen2.5-0.5B LoRA fine-tuned on Turing's own docs), with 126 tools (photo, utilities, chrome tabs, MCP client, memory, screen reading, planner). The loop trains the picker model on real user phrasings, evaluates against blind held-out test sets, ships releases as gaps close, targeting v5.0 where she picks tools entirely with her own model (no exact-match router).

One ability per minor release, a major when a whole roadmap family completes, until version 10. Each round: a frontier check first (ChatGPT, Claude, Gemini, Apple Intelligence, Operator-style agents; any real gap goes under "Gaps found by the loop" in roadmap.md with where it was seen), then the easiest, most relevant open gap, built, dogfooded for real on this Mac (the new ability plus one old one), full gate plus every file in tests/ green, docs and landing page in the same commit, push, CI checked, a line in docs/PROGRESS.md. Celebrate at 5.0.0 and 6.0.0 (4.0.0 and 100 tools are done). Every version gets a tag and a GitHub release from release.yml.

## Where things stand

Released v4.16.0: harness.py refactored to open chat loop directly and spawn read-only subagents (syntax: "spawn agents: A; B", up to three parallel, answers back in order). Tests in tests/test_harness.py SpawnTests (green). .DS_Store gitignored. AGENTS.md symlinked to CLAUDE.md.

Loop parked at 98% weekly usage (resets Saturday 22:00). Current state: 126 tools, knowledge 62/65 (zero confidently wrong), picker 395/484 on unseen. Picker trajectory: v4.15.6 tuned against two blind held-out sets (set 1: 26 wrong past guard, 19 refused; set 2: 19 wrong, 16 refused). Both sets shaped the guard rules, so an honest read of v5.0 needs a third fresh blind set.

Before v4.16.0 was v4.15.6 (round thirteen, guard only: heldout 361/26/19, heldout2 350/19/16, standard 1300/9/0; both held-out sets were used for tuning decisions, so 5.0 needs a third fresh blind set). Before that v4.15.5 (second blind held-out eval/heldout2.jsonl: 350/500, 20 wrong past guard, 16 refused; never read its rows or groups while tuning). Before that v4.15.4 (round twelve: blind-data retrain rejected as less safe, guard kept, held-out refused 24 to 19; contaminated, second fresh held-out needed before 5.0. Shell gotcha: this Mac's eval shell is zsh, so an unquoted "$t" holding "--test path" passes one argument; use ${=t}). Before that v4.15.3 (held-out check: 361/512, 29 wrong past guard, 24 refused on blind phrasings; eval/hands.py --test). Before that v4.15.2 (round eleven: guard only, 9 wrong past guard, 0 refused, 1300/1895; tuned on the test set, so not yet a held-out number). Before that v4.15.1 (round ten: guard only, 50 wrong past guard, 0 refused; the round ten retrain was less safe and is kept on disk unshipped). Before that v4.15.0 (picker round nine: 1300/1895, 83 wrong past guard, 0 refused, guard extended for five tools; badge step 8, the Pleiades). Before that v4.14.0 (every proposed write checked against your words: intent.py, law 12; picker round eight shipped, 1194/1878, guard word lists for 36 tools, 134 wrong past guard, 2 refused; badge step 7, Scutum). Before that v4.13.0 (plans: planner.py, law 11; badge step 6, a compass rose and a dotted route). Before that v4.12.0 (follows the conversation: followup.py, law 10; badge step 5, a Milky Way band). Before that v4.11.1 (tools.py split, MAX_LINES 700) and v4.11.0 (learns from you: feedback.py, ratings caught before routing; badge step 4, a ringed planet). Before that v4.10.0 (safe reading: law 9, untrusted.py fences every read result; badge step 3, a crescent moon). Before that v4.9.0 (the dev family: git status, recent commits, run a repo's tests, open PRs, open a repo in the editor; badge step 2, a shooting star), 125 tools. THE LIVE SITE DOES NOT DEPLOY ITSELF: the repo has no CLOUDFLARE_API_TOKEN secret and the deploy job goes green anyway. After every release, deploy by hand from a clean worktree of HEAD (never the working tree, it may hold a builder's half-done edits): `git worktree add --detach /tmp/turing-clean HEAD && cd /tmp/turing-clean && npx wrangler deploy`, then check stats.json on the live site says the new version, docs 100 percent, laws hold. The loop runs on Joshua's Mac. main takes direct pushes (the "2 of 2 required status checks" line on push is a notice, the push lands); the pre-push hook in .githooks runs the CI steps first, so run `git config core.hooksPath .githooks` once per clone. Rounds: the main session briefs one Sonnet subagent to build, then checks, commits, pushes and watches CI itself (Joshua's cap: 3 Haiku/Sonnet or 2 Opus at once). Pace slowly while weekly usage is in deficit. oMLX (the 9B) is a brew service: `omlx start` if ask_llm answers error 500.

## Frontier gaps

roadmap.md "Gaps with frontier models" lists the six gaps Joshua cares about beyond compute (wording, planning, conversation memory, her own thinking, learning from use, trusting what she reads). Every round: re-check that list, prefer work that shrinks one, update its line when it moves, and add any new gap found by the frontier check there too.

## Next, in order

1. Generate third fresh blind held-out test set (500 phrasings, written blind, no tuning against it yet)
2. Picker round fourteen: train and score against new set
3. Constrained decoding: previous attempt (v4.14) lost score (32 vs 934 logits, flag off), retry with deeper dive
4. Picker round fifteen: template fixes ("how many X is N Y" still writes "N Y to X"), refinement rounds
5. v5.0: ship when picker scores <10 wrong, 0 refused on blind set

Re-read this file, README.md and roadmap.md at the start of every round and fix anything stale in the same pass (Joshua, 2026-09-25).

## Restart prompt

```
/loop until version 5.0; target is fresh blind held-out set under 10 wrong past guard, 0 refused. Start with blind set generation, then picker round fourteen. Usage resets Saturday 22:00.
```
