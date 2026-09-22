# Progress log

TLDR per loop round, newest first. The loop adds a line every round it ships something, then the scorecard.

- 2026-09-22: loop strengthened: a scorecard every round (eval/scorecard.py) and law 8, a file-size ceiling that only goes down.
  `v1.4.0 · 80 tools · 125 tests · docs coverage 100% · laws all hold · biggest pixelmator/pxm.py 865 · actions 110/110 · parity 110/110 · util_diff 195/195`

- 2026-09-22 v1.4.0: ask Claude (tool 80). "ask claude ..." sends a hard question to Claude, asks first, answer marked as Claude's.
- 2026-09-22 v1.3.0: time-zone conversion (tool 79), "3pm PST in Tokyo", daylight time handled.
- 2026-09-22: ask.py split 1319 -> 388 lines (ask_faq, ask_local, ask_web); tools.py 977 -> 822 (tools_logo); tools_util.py 985 -> 644 (util_math, util_dates).
- 2026-09-22: new icon, her flower bloom, graded at 16 to 180 px, blueprint in docs/icon-blueprint.svg.
- 2026-09-22 v1.2.0: date math (tool 78). Releases publish themselves; deploy skips green until the Cloudflare secret exists.
- 2026-09-22 v1.1.0: never crashes on a broken tool, real typing, chains, search answers, photo edits by typing, 100-input edge sweep.
