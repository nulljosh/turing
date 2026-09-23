# Turing loop handoff (2026-09-23, cloud loop wrapped up, Mac picks it up)

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

- God-file splits: tools_util.py 985 -> 644 (util_math.py, util_dates.py); ask.py 1319 -> 717 (ask_faq.py, ask_local.py) -> 388 (ask_web.py; two test_chat outage tests now stub ask_web.http_json, where the code moved). Old modules re-export every moved name; behavior checked unchanged (FAQ paraphrase 5/16 with 0 wrong, prompts 26/29, all tests and evals). tools.py 977 -> 816 (tools_logo.py). Next targets: tools.py 822, web/demo.js, web/samantha.js, tools_util.py 644 (web lookups), web/demo.js 710, web/samantha.js ~720, tools_util.py 644.
- CI: deploy skips green without the Cloudflare secret. Every workflow run on main is green.

- New icon, made with her designer: tools_logo gained style "flower" (89 ember petals, dark ring, one lit core) and layers_to_svg (her designs without Pixelmator). Graded on contact sheets at 180/64/32/16 px on white and black against the old 144-dot spiral (a grey blob at 16 px) and her simple motifs (generic); inspired by what frontier LLM marks share (one bold radial silhouette, flat, one accent) without copying any. web/icon.svg, icon.svg (README) and web/samantha-logo.png (og:image) all rebuilt; test_edges pins them to tools_logo.icon_svg(). Demo's drawBloom ported (spiral size scaling, flower style). On the Mac her 1.7B can pick style flower too. Pro review graded it A- (mark 85% of tile, 36-unit ring vanishing at 16 px, core only 1.31:1 on petals), so the flower was re-proportioned: mark 78%, ring 63 units (a full pixel at 16 px), core Ø160; docs/icon-blueprint.svg measures it and a test enforces it.

- convert_time (tool 79): "what time is 3pm PST in Tokyo", "15:30 London to New York", "9am in Sydney" (from here). Cities, PST/EST/GMT/JST..., IANA names, daylight time followed; JS twin does the zone math with Intl alone and agrees word for word (util_diff 195/195). Route needs am/pm, a colon, noon or midnight so "convert 5 km to miles" stays a unit. Released as v1.3.0.

- ask_claude (tool 80, north star 4, "borrow their brains"): "ask claude ...", "claude, ...", "have claude ..." sends a hard question to claude-opus-5 through the official anthropic SDK (medium effort, server-side refusal fallbacks) and marks the answer as Claude's. Only by name; WRITES (asks first) and NOT_FOR_MODELS (no model menu, no MCP); every failure is a plain reply. test_claude.py runs a fake SDK; checked against the real SDK 1.8.0 here, which found that a missing key raises TypeError (now read by message). The never-crash sweep blocks the SDK so tests can never make a billed call. User setup on the Mac: .venv/bin/pip install anthropic, and ANTHROPIC_API_KEY or ant auth login. Released as v1.4.0.

- pixelmator/pxm.py 865 -> 621: the spec trust boundary (exit codes, shape tables, PxmError, validate_spec) moved to pxm_spec.py. Every example spec's AppleScript is byte-identical before and after; law 8 ceiling 870 -> 825.

## Where things stand
The cloud loop stopped on 2026-09-23 so the loop can move to the Mac. Everything is on main (1b324ce and earlier), nothing is left on a side branch.
v1.4.0, 80 tools, all workflow runs green. Scorecard: `v1.4.0 · 80 tools · 125 tests · docs coverage 100% · laws all hold · biggest tools.py 820 · actions 110/110 · parity 110/110 · util_diff 195/195`.
The live site has not been deployed from the cloud (no Cloudflare access), so it likely shows an older version. roadmap.md "Joshua's Mac to-do" lists what needs the keyboard.

## Next, in order
1. On the Mac: site deployed by hand 2026-09-22; run `./gate.sh --full` to check her real model, Pixelmator and the live page against v1.4.0.
2. Split tools.py (822, the biggest; tests patch tools._run, _app, installed_apps, pick, read_page, grayscale_image, and plan() swaps tools-module globals, so re-export and patch where the names live), then lower MAX_LINES in eval/laws.py. Then pixelmator/test_pxm.py 806, tools_util.py 651, web/demo.js, web/samantha.js.
3. Top of roadmap.md "Gaps found by the loop", Mac-first now: streamed replies SHIPPED v1.5.0 in the plain chat (model loaded once, a warm turn is about 1s, was 2s+ reloading per turn; the TUI streams too since v1.5.1), then voice in (Whisper on MLX), GUI control with approval. 2.0.0 = GUI control + voice in.
4. ask_claude now asks the biggest local model instead of Claude: oMLX Qwen3.5-9B first (warm answers in about a second), Ollama qwen3:8b as fallback. Ollama loads from the external LaCie drive and its loader stalled past 5 minutes on 2026-09-22, which is why oMLX goes first: the user will not hand out API keys. No anthropic SDK, nothing leaves the Mac.

## Restart prompt
```
/loop Keep building Samantha (turing). Read docs/LOOP-HANDOFF.md and roadmap.md first. Each iteration: compare her with frontier assistants (Claude, ChatGPT, Gemini, Siri, Open Interpreter), add each real gap to roadmap.md "Gaps found by the loop" with where it was seen, then build the top one that can be tested here: smallest honest fix with tests, run the CI checks (tests, eval/actions.py, eval/web_parity.py, eval/util_diff.py, eval/laws.py, stats.py --check), keep web/samantha.js in step, then one cleanup (a test for something untested, dead code out, duplication folded, a slow path made fast), commit, push, delete the shipped line, and rewrite LOOP-HANDOFF.md. Queue Mac-only work instead of faking it. Never stop on your own.
```
