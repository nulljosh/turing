# Progress log

TLDR per loop round, newest first. The loop adds a line every round it ships something, then the scorecard.

- 2026-09-22: 🎉 v1.5.0: streamed replies. She stays loaded and prints words as she writes them; a warm turn is about 1s (was 2s+ reloading every turn). Output checked identical to the old path.
  `v1.5.0 · 80 tools · 126 tests · docs coverage 100% · laws all hold · biggest tools.py 820 · actions 110/110 · parity 110/110 · util_diff 195/195`
- 2026-09-22: v1.4.2: ask_claude tries oMLX's Qwen3.5-9B first (warm answer in about a second), Ollama second. Ollama's loader stalled past 5 minutes off the external drive.
  `v1.4.2 · 80 tools · 125 tests · docs coverage 100% · laws all hold · biggest tools.py 820 · actions 110/110 · parity 110/110 · util_diff 195/195`
- 2026-09-22: 🎉 v1.4.1: ask_claude runs on the Mac now. It hands hard questions to qwen3:8b through Ollama, no API key, nothing leaves the machine. Site deployed by hand.
  `v1.4.1 · 80 tools · 124 tests · docs coverage 100% · laws all hold · biggest tools.py 820 · actions 110/110 · parity 110/110 · util_diff 195/195`
- 2026-09-23: pixelmator/pxm.py split 865 -> 621 (pxm_spec.py); every example spec's AppleScript byte-identical; file-size ceiling 870 -> 825.
  `v1.4.0 · 80 tools · 125 tests · docs coverage 100% · laws all hold · biggest tools.py 820 · actions 110/110 · parity 110/110 · util_diff 195/195`
- 2026-09-22: loop strengthened: a scorecard every round (eval/scorecard.py) and law 8, a file-size ceiling that only goes down.
  `v1.4.0 · 80 tools · 125 tests · docs coverage 100% · laws all hold · biggest pixelmator/pxm.py 865 · actions 110/110 · parity 110/110 · util_diff 195/195`

- 2026-09-22 v1.4.0: ask Claude (tool 80). "ask claude ..." sends a hard question to Claude, asks first, answer marked as Claude's.
- 2026-09-22 v1.3.0: time-zone conversion (tool 79), "3pm PST in Tokyo", daylight time handled.
- 2026-09-22: ask.py split 1319 -> 388 lines (ask_faq, ask_local, ask_web); tools.py 977 -> 822 (tools_logo); tools_util.py 985 -> 644 (util_math, util_dates).
- 2026-09-22: new icon, her flower bloom, graded at 16 to 180 px, blueprint in docs/icon-blueprint.svg.
- 2026-09-22 v1.2.0: date math (tool 78). Releases publish themselves; deploy skips green until the Cloudflare secret exists.
- 2026-09-22 v1.1.0: never crashes on a broken tool, real typing, chains, search answers, photo edits by typing, 100-input edge sweep.
