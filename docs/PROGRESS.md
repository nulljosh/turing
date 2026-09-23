# Progress log

TLDR per loop round, newest first. The loop adds a line every round it ships something, then the scorecard.

- 2026-09-22: 🎉🎉 v3.0.0: she sees and she researches. "research the history of the printing press" reads Wikipedia, her library and your notes, and the local 9B writes a cited brief in about 40 seconds warm; uncited or unsupported sentences are cut. With eyes (v2.1.0) that is 3.0.
  `v3.0.0 · 86 tools · 169 tests · docs coverage 100% · laws all hold · biggest tools.py 753 · actions 131/131 · parity 131/131 · util_diff 195/195`
- 2026-09-22: 🎉 v2.1.0: she can see. "look at my screen and tell me...", "what's in ~/Desktop/cat.png": Qwen2.5-VL 3B on MLX looks and answers, on the Mac, asked first. Live on the real screen: right gist, some details off (called the Dock a taskbar). Half of 3.0.
  `v2.1.0 · 85 tools · 165 tests · docs coverage 100% · laws all hold · biggest tools.py 753 · actions 127/127 · parity 127/127 · util_diff 195/195`
- 2026-09-22: v2.0.1: score.py 29/29 again, and steady. A question her FAQ answers never reaches her picker or agent ("how much memory does it use" had reported the Mac's RAM). Picker and agent moved to tools_agent.py: tools.py 778 -> 751, ceiling 760.
  `v2.0.1 · 83 tools · 159 tests · docs coverage 100% · laws all hold · biggest tools.py 751 · actions 121/121 · parity 121/121 · util_diff 195/195`
- 2026-09-22: Distillation round 2 kept: 499 Sonnet-written, 9B-judged lessons. On 59 held-out questions she now declines 16/16 when her notes lack the answer (was 3/16), answers right unchanged at 19/43. score.py 28/29, the miss is a flaky route ("how much memory does it use" goes to her hands, which report the Mac's memory), not the weights. train_resilient.sh now counts reclaimable memory and unloads oMLX and Ollama models first.
- 2026-09-22: 🎉🎉 v2.0.0: talk to her and she works your screen. "click Sign in", "type hello", "press return": she reads the screen with Vision OCR to find the words, clicks with cliclick, and asks before every step. With voice in (v1.8.0) that is 2.0: speak, she listens, acts on the Mac with your yes, and answers aloud. All local.
  `v2.0.0 · 83 tools · 158 tests · docs coverage 100% · laws all hold · biggest tools.py 780 · actions 121/121 · parity 121/121 · util_diff 195/195`
- 2026-09-22: 🎉 v1.8.0: talk to her. `python3 chat.py --voice`: sox records until you stop, Whisper large-v3-turbo on MLX transcribes on the Mac, the harness answers, she says it aloud. Verified with a question rendered by `say` (heard "What is 2 plus 2?"). Half of 2.0.
  `v1.8.0 · 80 tools · 151 tests · docs coverage 100% · laws all hold · biggest tools.py 778 · actions 114/114 · parity 114/114 · util_diff 195/195`
- 2026-09-22: v1.7.1: score.py 25/29 -> 29/29. Project questions were hijacked by her hands: "what's blocked" listed a Chrome tab, others got invented or half-written tool-call answers. current_tab now needs a word for it, and the agent's answer counts only after it used a tool. tools.py 826 -> 778 (tools_agent.py), ceiling 825 -> 810.
  `v1.7.1 · 80 tools · 144 tests · docs coverage 100% · laws all hold · biggest pixelmator/test_pxm.py 806 · actions 114/114 · parity 114/114 · util_diff 195/195`
- 2026-09-22: 🎉 v1.7.0: her own library. The fieldbook plus ~10,000 Wikipedia vital-article leads offline; she answers what-is and who-was questions from the page of that name and says which. Knowledge 58/65, 0 confidently wrong (web rate-limited during the run). Retrained on everything, kept (val loss 1.98 -> 1.83). distill.py ready for the teacher.
  `v1.7.0 · 80 tools · 141 tests · docs coverage 100% · laws all hold · biggest tools.py 820 · actions 114/114 · parity 114/114 · util_diff 195/195`
- 2026-09-22: 🎉 v1.6.0: ask any LLM on this Mac by name (ask qwen, ask llama, ask gemma; claude or gpt means the biggest). A model that is not here gets the list of what is. ask_claude is now ask_llm.
  `v1.6.0 · 80 tools · 129 tests · docs coverage 100% · laws all hold · biggest tools.py 820 · actions 114/114 · parity 114/114 · util_diff 195/195`
- 2026-09-22: v1.5.1: the curses TUI streams her words too (pty smoke tested). Retrain on everything running: 5,680 chunks, was 985.
  `v1.5.1 · 80 tools · 126 tests · docs coverage 100% · laws all hold · biggest tools.py 820 · actions 110/110 · parity 110/110 · util_diff 195/195`
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
