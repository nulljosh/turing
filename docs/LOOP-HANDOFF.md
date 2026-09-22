# Turing loop handoff (2026-09-21, checkpoint)

The live `/loop` for this repo. Checkpoint rewrites this file every run. A new session reads it and picks up where the last one stopped.

## What the loop is
Samantha to a 1.0.0 release, landing page to A+. Ship features with quality gates: every feature ships with tests, eval/laws.py green, docs 100 percent, phone-size QA on the landing page, and CI green. Each cycle: take the top roadmap item or hunt a real gap (what comparable assistants do that she cannot: Siri, Apple Intelligence, Claude+ChatGPT desktop, Open Interpreter, Raycast, Ollama agents), add it to roadmap.md under "Gaps found", build the fix, test it, deploy it, delete the line when shipped. No code ships untagged. Prune roadmap, refresh landing/README/CLAUDE.md after every tag.

## Rules
Headless always: `SAMANTHA_HEADLESS=1`. Check free disk and memory before training (6GB min). One heavy job at a time. Haiku subagents one at a time, sequential not parallel. Stop at 90% usage. Root-cause fixes only, never edit tests to pass. Code review diffs before calling anything done.

## Where things stand
v0.14.0 shipped. Samantha has 73 tools: 30 photo/paint (tools_image.py, Pixelmator), 27 utilities (math/time/dice/passwords/hashes/Mac vitals), 10 chrome tabs (list/switch/close/read), MCP client (list/call other servers), memory (remember/recall/forget), read_screen (Vision OCR), eval/a11y.py (4-mode accessibility audit). Landing: draw-anything via /api/draw on Cloudflare, demo's Chrome window opens real pages (Wikipedia live, others get real tab), Chrome tab tools in the interface, skip link, scroll-in sections, full-screen demo, wordless logos (golden spiral default), new icon she designed. Knowledge 62/65. Gate: eval/laws.py (73 tools classified), eval/a11y.py (axe-core 4 modes), eval/hands.py (77/77 actions), eval/web_demo.py (0 failures), eval/web_parity.py (77/77 parity), docs 100 percent enforced. Picker bake-off: Qwen3-0.6B 683/834 unseen vs Qwen2.5 671/834, from-scratch pickers 1.8M/3.2M params hit only 248/220. Model weights gitignored (in history but untracked).

## Next, in order
1. Answer screen questions (read_screen shipped, now ask about what you see in the demo)
2. Read PDFs and documents (PDFKit extract text, ask questions about it)
3. Control the GUI with approval (click, type, tap in an app, every step asks first)
4. Voice input (she can speak, add listening via WhisperKit or similar)

Real harness for 1.0: show tool results live in chat, log every tool call, ask before writes/sends/deletes (shipment blocking in v1.0.0, not before).

## Restart prompt
```
/loop Drive Samantha (~/Documents/Code/turing) to 1.0.0 and the landing page to A+. Read docs/LOOP-HANDOFF.md and roadmap.md ("Road to 1.0.0" and "Gaps found by the loop") first. Each iteration: take the top open roadmap item, or if the gap list is thin, search the web for the biggest real gap between her and comparable assistants and add it to the roadmap with where it was seen. Build the smallest honest fix with tests, run ./gate.sh and eval/laws.py, QA the landing page on a phone size, push, wait for CI green, then delete the shipped line from the roadmap, refresh the landing page, README and CLAUDE.md, deploy, and release as you go with ./release.sh. SAMANTHA_HEADLESS=1 always, docs 100 percent, disk 6GB and memory checked before heavy jobs, one at a time, watch Claude usage. Stop at v1.0.0 and send a notification.
```
