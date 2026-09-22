# Turing loop handoff (2026-09-22, checkpoint)

The live `/loop` for this repo. Checkpoint rewrites this file every run. A new session reads it and picks up where the last one stopped.

## What the loop is
Never-ending build-out of Samantha. No finish line: each iteration compares her with frontier assistants (Claude, ChatGPT, Gemini, Siri/Apple Intelligence, Open Interpreter, Raycast AI), writes each real gap into roadmap.md "Gaps found by the loop" with where it was seen, then builds the top one: smallest honest fix, tests, checks, commit, push, delete the shipped line. Every iteration first checks every workflow run (test, release, deploy) on main and the branch and fixes any red before anything else, and splits one god file (CLAUDE.md "File size"). Every iteration also hardens her: error handling and edge cases (empty, huge, unicode, negative, malformed, missing files, offline) with a test for each. And leaves the code better: more tests for what exists, dead code removed, duplication folded, slow paths made fast. Never at the cost of a check. When the gap list runs thin, compare again. Mac-only work (training, Pixelmator, voice, GUI control, release.sh, deploy) is queued for a Mac session; a cloud session builds everything that tests on Linux.

## North star
roadmap.md "How we compete with trillion-dollar labs": local, hands on the real Mac, never confidently wrong, distill from frontier teachers, tiny and fast. Each iteration moves one. Taper (longer waits, smaller iterations) if the user says Claude usage is tight.

## Rules
Headless always: `SAMANTHA_HEADLESS=1`. Check free disk and memory before training (6GB min). One heavy job at a time. Haiku subagents one at a time, sequential not parallel. Stop at 90% usage. Root-cause fixes only, never edit tests to pass. Code review diffs before calling anything done.

## Chat + tools release pass (2026-09-22, cloud session, branch claude/full-release-chat-tools-x5i81k)
Goal: a full version you sit down and chat with, and she calls tools, without ever dying mid-conversation. Driven from a Linux container (no Mac, no MLX weights, no osascript), which is exactly what exposed these:
- Fixed: one tool failing (missing `osascript`, a hung app) crashed chat.py. `harness.Session.ask` now turns any tool exception into "I tried set_volume(30), but it did not work: osascript is not on this machine." and records the turn. `ask.local_answer` (ask.py, serve.py) does the same.
- Fixed: the answer model missing or hanging crashed chat.py. `generate` has a 180s timeout, a failure gives `MODEL_DOWN`, and `safe_turn` guards the whole answer chain in the plain chat and the TUI.
- Fixed: "hi", "how are you", "thanks", "what can you do", "list your tools" had no answer outside the web demo. `ask.small_talk`, anchored to the whole message so "hey calculate 8 + 8" still hits tools. The ability list counts `tools.TOOLS` live.
- Fixed: "roll a d20" missed the dice route (Python and JS twin, util_diff case added).
- Fixed: typed phrasings that missed. "search google for X" searched for "google for X"; "search youtube for X" / "go to youtube and search X" / "search X on amazon" now open that site's own results (`tools.site_search`); "whats"/"hows" without the apostrophe; "look up the weather in X"; "what tabs do i have open"; "open photoshop" opens Pixelmator when there's no Photoshop.
- Fixed: photo edits needed the picker model. Ten exact image routes in `tools_image.ROUTES` ("make ~/Desktop/cat.png black and white", "remove the background from X", "rotate X by 180", "resize X to 500", "convert X to jpg"...), still asking first. JS twin says those need the real Mac. actions.py 95/95, parity 95/95.
- Added: "again" / "do that again" / "one more time" repeats the last command through the harness, so a write asks again.
- Releases are automatic now: bump VERSION + stats.py + a "Release vX.Y.Z: ..." commit, merge, and .github/workflows/release.yml tags and publishes once CI passes. v1.1.0 goes out this way. Mac-only extras, whenever the user happens to be on the Mac (never asked of them): ./gate.sh --full and the landing deploy (npx wrangler deploy).

## Shipped in the build-out loop (2026-09-22)
- Chains: "open youtube and set the volume to 20", "calculate 6*7, then take a note buy milk" run every step in order with no model (`tools.chain`, JS `Samantha.chain`, demo.js). "then" always splits; a plain "and" splits only a sentence a catch-all route would swallow, and a later step only a catch-all takes is words, not a command. Each step is shown and a write still asks.

- Search answers: "google how tall is everest" opens the tab and answers with its source (`tools.search_answer`, reusing ask.general_knowledge with `hands=False` so a search never re-enters the tools). A non-question ("google best pizza") only opens the tab. Demo does the same through /api/ask. Not live-tested from the cloud container (its network blocks the open web); run a real search on the Mac.

- Follow-ups: "read it", "what does that page say", "open it again" point at the page she last opened, searched or read (`Session.last_page`, `point_back`). With nothing opened they are not guessed. New exact route: "read github.com/x", "summarize https://...", "what does X say" -> read_page (JS says it needs the real Mac).

- TUI shows each tool call the moment it is found ("working: [open_app(pixelmator)]") instead of a bare "thinking..." until the end. Smoke tested in a pty.
- Cleanup: tools_image.py 458 -> 231 lines. Ten copies of open/step/export/close folded into `_pixelmator` and `_edit`. A new table test pins every tool's exact AppleScript, timeout and reply; it passes on the old and the new code alike. `.gif` dropped from the photo routes (the tools never took gifs).

- Hardening pass: a ~100-input weird sweep (empty, huge, unicode, negative, half-finished, offline, no osascript) now in `test_edges.py` and CI. Fixed what it found: empty input errored; "open"/"search for"/"remind me to"/"take a note"/"set a timer" now ask for what's missing (`tools.missing`); "is -7 prime" answered with the prime-minister FAQ entry (negatives now reach their tools); "tip on -10" and a 400-digit bill; "go to http://"; dangling "and"/"then"; full-width letters and control/bidi characters (NFKC + strip, Python and JS); "what is 1/0" says why; an unclosed FAQ.md handle.

- v1.1.0 published by the release workflow (first automatic release). Deploy workflow merged; waits on the CLOUDFLARE_API_TOKEN repo secret (the user will deploy from the Mac for now).
- date_math (tool 78): "100 days from now", "3 weeks ago", "2 months after 2026-01-31" (month-end clamp), "what day of the week was July 4 1976", "days between X and Y", years 1 to 9999. Python and JS agree word for word (util_diff 183/183). Found and fixed: strftime %Y writes year 1 as "1" on Linux and "0001" on macOS, so dates are spelled by hand.

## Where things stand
v0.14.0 shipped. Samantha has 73 tools: 30 photo/paint (tools_image.py, Pixelmator), 27 utilities (math/time/dice/passwords/hashes/Mac vitals), 10 chrome tabs (list/switch/close/read), MCP client (list/call other servers), memory (remember/recall/forget), read_screen (Vision OCR), eval/a11y.py (4-mode accessibility audit). Landing: draw-anything via /api/draw on Cloudflare, demo's Chrome window opens real pages (Wikipedia live, others get real tab), Chrome tab tools in the interface, skip link, scroll-in sections, full-screen demo, wordless logos (golden spiral default), new icon she designed. Knowledge 62/65. Gate: eval/laws.py (73 tools classified), eval/a11y.py (axe-core 4 modes), eval/hands.py (77/77 actions), eval/web_demo.py (0 failures), eval/web_parity.py (77/77 parity), docs 100 percent enforced. Picker bake-off: Qwen3-0.6B 683/834 unseen vs Qwen2.5 671/834, from-scratch pickers 1.8M/3.2M params hit only 248/220. Model weights gitignored (in history but untracked).

## Next, in order
Top of roadmap.md "Gaps found by the loop". Cloud-buildable first:
1. Streamed replies from her own model (mlx_lm stream_generate), Mac-only to test
2. Next frontier comparison pass: find three more gaps
Mac-only, queued: release 1.1.0, GUI control with approval, voice in.

## Restart prompt
```
/loop Keep building Samantha (turing). Read docs/LOOP-HANDOFF.md and roadmap.md first. Each iteration: compare her with frontier assistants (Claude, ChatGPT, Gemini, Siri, Open Interpreter), add each real gap to roadmap.md "Gaps found by the loop" with where it was seen, then build the top one that can be tested here: smallest honest fix with tests, run the CI checks (tests, eval/actions.py, eval/web_parity.py, eval/util_diff.py, eval/laws.py, stats.py --check), keep web/samantha.js in step, then one cleanup (a test for something untested, dead code out, duplication folded, a slow path made fast), commit, push, delete the shipped line, and rewrite LOOP-HANDOFF.md. Queue Mac-only work instead of faking it. Never stop on your own.
```
