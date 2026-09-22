# Architecture

Turing teaches a small AI model to write and answer the way you do. It reads everything you have written, your notes and your project docs, and trains the model on that until it picks up your voice and knows your work. The result is called Samantha, and you talk to her from the terminal.

The whole thing runs on this Mac. Nothing is uploaded, no rented graphics cards, no bill. It is a small enough model to train at home, nudged toward your writing rather than rebuilt from scratch, which is why it fits.

## How it runs

First `prep_data.py` gathers your wiki and project documentation and cuts it into training examples, holding some back to check the results against. Then the training step runs on the Mac's own chip. It does not make a new copy of the model; it saves only the adjustments, a few megabytes rather than gigabytes. `parse_log.py` turns the training log into `web/status.json` so you can watch it improve.

Once she is trained, `ask.py` and `chat.py` handle questions. Before answering, they look up the relevant passages from your notes through the brain project, so answers come from what you actually wrote instead of being made up. Common questions are matched even when worded differently, and anything that changes with time, like who currently holds an office, is looked up live rather than remembered. `serve.py` runs the prompt you type into.

| File | What it owns |
|---|---|
| `prep_data.py` | Data pipeline. Walks Obsidian wiki + Code directory, chunks markdown into train/valid JSONL. Skips non-documentation. |
| `train.py` (via `mlx_lm lora`) | Training orchestration. Launches LoRA fine-tune on the frozen base model (Qwen2.5-0.5B). Stores weights in `ada-1-adapter/`. |
| `parse_log.py` | Post-training: parses loss history from `train.log`, writes `web/status.json` for the landing page. |
| `ask.py` + `chat.py` | Inference. Loads the trained adapter, retrieves facts from brain RAG, generates answers. `chat.py` wraps it in an interactive loop, and hands every command ("set the volume to 30", "take a note buy milk") to `harness.py` first, which shows the tool call and asks before anything that writes. |
| `serve.py` | CLI server. Local REPL for chat sessions. |
| `gate.sh` | Validation suite. Runs fast checks (chat, actions, parity, pixelmator, tools) against eval baselines. `release.sh` runs the full gate. |
| `stats.py` | Generates documentation coverage metrics (docstring + file citation percentages) into web/stats.json. |
| `worker.js` | Cloudflare Worker for the /api endpoints. Deploys the landing page assets via `wrangler deploy`. |
| `tools.py` | The small fixed set of things Samantha can actually do on this Mac. Simple commands are matched by pattern and run straight away, with no model involved. Multi-step asks go to Ollama. Includes `paint_image` for the painting hands. |
| `tools_image.py` | Image processing tools that drive Pixelmator Pro. Ten tools: remove_background, upscale_image, enhance_image, grayscale_image, rotate_image, flip_image, resize_image, crop_square, convert_image, image_info. All validate paths with `_inside_home()`, export to ~/Desktop, never modify originals. `ROUTES` makes each one an exact command ("make ~/Desktop/cat.png black and white"), no model needed, ported to `web/samantha.js`. |
| `tools_util.py` | Forty-seven utility tools that need no app: calculate, convert_units, time_in, current_date, days_until, flip_coin, roll_dice, random_number, make_password, make_uuid, hash_text, base64_encode, base64_decode, word_count, reverse_text, shout, morse_code, json_pretty, is_prime, roman_numeral, tip, plus the Mac readers disk_space, uptime, memory_usage, cpu_load, ip_address, wifi_name, system_info and the three that act, copy_to_clipboard, sleep_display, reveal_in_finder, list_shortcuts, run_shortcut the MCP client pair list_mcp_tools and call_mcp_tool, the Chrome tab tools list_tabs, switch_tab, close_tab and read_tab, memory across sessions with remember, recall and forget (a JSON file in ~/.samantha, private: hidden from models and MCP, remember and forget ask first), read_document, find_in_document and ask_document (a grounded answer from a local reader model, every number and name checked against the text), ask_screen (the same over the screen's OCR text, private and ask-first), and read_document/find_in_document (PDF through pdf.swift and PDFKit, Word, RTF and HTML through textutil, plain text, home folder only), read_screen (macOS Vision OCR through ocr.swift on a fresh screenshot, private and ask-first), and close_tab asks first and is never a model's choice (run_shortcut and call_mcp_tool only when named, never chosen by a model; call_mcp_tool asks first). Fixed argv only, silent under SAMANTHA_HEADLESS. Its ROUTES table is appended to the router in tools.py. |
| `mcp_server.py` | Her tools over MCP, so other assistants can use her hands. A stdio JSON-RPC server, standard library only: initialize, tools/list, tools/call. It leaves out the tools that fire a side effect (run_shortcut, copy_to_clipboard, sleep_display) until the harness can ask first. |
| `ocr.swift` | Reads the text in an image with macOS Vision, one line per recognized line. tools_util.read_screen runs it on a fresh screenshot. |
| `pdf.swift` | Prints the text of a PDF with macOS PDFKit. tools_util.read_document runs it for .pdf files. |
| `scratch-picker/train.py` and `scratch-picker/eval.py` | The from-scratch picker experiment: a character transformer with tool, argument-mode and span heads, and the scorer that reports the same numbers as eval/hands.py. Results and why it does not generalize are in docs/BAKEOFF.md. |
| `harness.py` | The conversation around her hands. It remembers every turn's command, tool calls and result, prints each tool call before it runs, and asks before anything in tools.WRITES (a note, a reminder, a file on the Desktop, a Shortcut, the clipboard). tools.plan() finds the calls without running them. |
| `pixelmator/pxm.py` | Painter logic. Repaints a photo using quadtree algorithm (split most-wrong region into four cells). Drives Pixelmator Pro via AppleScript. Handles layer creation, coloring, and bounds checking. |
| `pixelmator/arc_text.py` | Text-along-arc rendering for logo design (used by `make_logo` tool). |
| `menubar/PaintBar.swift` | SwiftUI menu bar app. Lets you pick a photo, shows live painting progress, has a background switch to hide Pixelmator. Supports `--paint <image>` for headless QA. |
| `menubar/build.sh` | Build script for PaintBar. Creates the macOS app bundle. |
| `gen_hands_data.py` | Generates training data for the hands (tool picker). Harvests labeled examples for action classification. |
| `harvest_voice.py` | Voice data harvester. Collects training examples from git commits (183 pairs extracted from fleet repos), used for style transfer beyond documentation alone. |
| `run_lora_capped.py` | Utility to run LoRA training with memory caps, protecting against OOM crashes on the 16GB machine. |
| `train_resilient.sh` | Wrapper script for resilient training runs (retries on crash, memory limits). |
| `release.sh` | Cut a release: run checks, bump VERSION, tag, push, publish GitHub release, deploy site. |
| `test_nimble.py` | Integration tests for Nimble service integration (via serve.py REPL). |
| `eval/hands.py` | Automated QA for tool picking and action execution. Measures precision of wrong picks and false refusals. |
| `eval/score.py` + `test_chat.py` | Automated QA over a held-out test set. No eyeballed results, CI validates every run. |
| `test_tools_image.py` | Unit tests for image tools. Mocks Pixelmator's pxm module so tests run on Linux CI without the app. Tests path validation, argument parsing, AppleScript generation, and output file handling. |
| `test_mcp.py` | A real client conversation against mcp_server.py: initialize, list, call, an unknown tool, an unknown method, and garbage input. |
| `test_tabs.py` | The Chrome tab tools against a made-up tab list: numbering, finding a tab by number or word, headless never touching Chrome, closing built only from parsed tab numbers, and the JavaScript-setting hint. |
| `test_memory.py` | Her memory across sessions against a temporary file: it survives a new session, repeats and blanks, ranked recall, careful forgetting, the 500 fact cap, a broken file, the harness asking first, and privacy from models and MCP. |
| `test_screen.py` | read_screen against a made-up OCR result: headless never captures, all lines or only matching ones, the Screen Recording hint, the temporary screenshot always removed, and privacy from models and MCP. |
| `test_documents.py` | Reading documents in a made-up folder under home: text, RTF through textutil, PDF through PDFKit, finding passages, and refusing hidden files, paths outside home, missing files, unknown types and empty files in words. |
| `test_reader.py` | Questions about documents and the screen with the reader model faked: a grounded answer comes back, an invented number or name is declined, UNKNOWN is declined, no Ollama falls back to passages, long text is narrowed to relevant passages, and the screen path stays private. |
| `test_harness.py` | The harness keeps its promises: a no stops the write, a yes runs it once, reads never ask, the record is kept, and plan() runs nothing. |
| `eval/util_diff.py` | Runs about a hundred phrasings through tools_util.py and through its JavaScript twin in web/samantha.js under node, and fails on any difference in the words that come back. Also checks that near-miss sentences ("hash browns are good") are not stolen. |
| `eval/laws.py` | Checks the rules in LAWS.md against every tool, not a sample: side-effect tools are classified, hidden tools never reach a model or MCP, a no from the harness stops a write, her hands stay in the home folder, docs stay at 100 percent, Python and JavaScript agree, no em dashes. Borrowed from the idea of Bend's LAWS.bend. |
| `eval/a11y.py` | Audits the live landing page with axe-core (fetched at run time) in four modes, desktop and phone, light and dark, and fails on any WCAG 2 A or AA violation or best-practice issue. |
| `eval/smoke_images.py` | Runs all ten image tools for real through a hidden Pixelmator Pro on a sample photo and measures each output (size, rotation, saturation, transparency, difference from the original). Mac only, not in CI, run by the full gate. It caught grayscale and enhance sending AppleScript Pixelmator rejects. |
| `web/paint.js` | Landing page painting demo. Shows live quadtree painting in the browser (three clickable paintings). |
| `scratch/` | Experimental from-scratch transformer (character-level, no pre-trained weights). Deliberately tiny, proves we can build one without repeating the Arthur gibberish failure. Not intended to be fluent. |
| `tui/` | Terminal UI. SwiftPM + SwiftTUI wrapper around the Python CLI. |
| `web/status.json` | Training progress (loss chart, phase tracker). Generated by `parse_log.py`, read by the landing page. |
| `web/index.html` | Landing page. Loss chart, training status, painter demo, project roadmap. |
| `wrangler.toml` | Cloudflare Worker deployment (landing page assets only). |
