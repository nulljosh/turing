# Roadmap

Anthropic spends billions of dollars and years with thousands of GPUs on foundation models. That's not this. Transformers themselves are only from 2017 (the "Attention Is All You Need" paper), the whole field is young enough that a lot of useful ground is still coverable by one person on a Mac Mini, as long as the goal is calibrated to the hardware.

### Phase 0: Pipeline proof (now, days)
LoRA fine-tune of a small open base (Qwen2.5-0.5B-Instruct) on our own Obsidian wiki + project READMEs. 588 lines of data, 200 iterations, runs in minutes on the M4. Goal: prove the loop works end to end (data → train → adapter → serve), not quality. Done, no gibberish (unlike Arthur).

### Phase 1: More data, same model (weeks 1-3)
Feed it everything: journal entries, commit messages, project READMEs/WHITEPAPERs, roadmap.md files, notes vault, even old Slack/iMessage exports if we want the voice right. Thousands of chunks instead of hundreds. Re-run LoRA. This is the single highest-leverage step, small models improve far more from 10x the data than from 10x the iterations.

### Phase 2: Evaluate like it matters (weeks 2-4, parallel with Phase 1), started
`eval/prompts.jsonl` has 28 real prompts, `eval/run_eval.py` generates against any adapter. See `eval/` for run-by-run results. A model that "trains" but never gets graded is a number going down, not progress.

### Phase 3: Bigger base, same recipe (month 2)
Once the pipeline is boring and repeatable, try a bigger base. Candidates as of Sept 2026: `Qwen3.5-0.8B` (direct successor to what we're using now), `SmolLM2-1.7B` (fully open training recipe, worth it if transparency matters to us), `Llama-3.2-1B-Instruct` (solid middle ground, ~1GB at Q4). Bigger model = slower training, more memory, better baseline fluency. Compare quality per minute of training against the 0.5B, there's a real chance the 0.5B fine-tuned on great data beats a bigger base fine-tuned on so-so data.

### Phase 4: Retrieval instead of memorization (month 2-3)
Don't try to cram every project fact into model weights, that's what causes hallucination and stale knowledge. Wire it to `brain` (the existing RAG-over-notes setup) so the model reasons over live retrieved context instead of "remembering" it. Small fine-tuned model + good retrieval beats a bigger model with neither. This is the actual production architecture, not a toy.

### Phase 5: Give it a job (month 3+), started
Once retrieval works, point it at concrete, boring, checkable tasks:
- **In-voice drafting**, journal entries, commit messages, README sections in house style (no em dash, no AI voice, sans-serif brain already enforced elsewhere, teach the model the same rules)
- **Project Q&A**, "what's the status of Epiphany", answered from the wiki instead of us re-reading MEMORY.md
- **Local autocomplete**, a tiny always-available model that doesn't hit the network, for quick text expansion
- **A judge/filter model**, small models are cheap enough to run on every commit or PR as a first-pass linter before anything hits a bigger model

### Phase 9: Hands (started 2026-09-20)

Samantha could answer. She could not do anything. "Open chrome and go to hacker news" got "that's outside what I know about this project." Now it opens Hacker News.

- **`tools.py`, six tools: `open_app`, `open_url`, `web_search`, `current_tab`, `read_page`, `screenshot`.** No shell tool, on purpose. Every tool is a fixed argv. A string a model wrote never reaches `sh`.
- **Two layers.** `act()` is a regex router, instant and exact, same category as arithmetic and the clock: a recognisable command has one right action, so no model is involved. `agent()` handles multi-step asks ("poke around hacker news and tell me the top stories") by letting `qwen3:8b` drive the same tools through Ollama's native tool calling. The 0.5B cannot pick tools reliably. She borrows a bigger head for her hands.
- **Wired in at `local_answer()`**, the one place `ask.py`, `chat.py`, the TUI and `serve.py` all route through.
- One real bug caught before commit: the action detector matched "summarize", which hijacked the eval prompt "Summarize what Turing is in one sentence" into the agent. Narrowed the verb list, added it to `tools.py`'s self-check.
- Not yet done: `read_page` is a tag-strip over a plain fetch, so JS-rendered pages come back empty. Clicking and typing in Chrome needs a real bridge. And the goal that matters: a small model that calls these tools itself, so the borrowed 8B head can go.

### Majors, each one a leap with one check (set 2026-09-23)
A major ships when a whole family is done and one check proves it. In order:

- **5.0, her own head.** Every tool picked by her own 0.5B, none through the exact router: two-step picking (family, then tool, so no choice is bigger than twelve), constrained decoding (she can only emit a real tool name and words copied from the sentence), and abstaining instead of guessing. Check: `eval/hands.py` at 105 of 105 tools by wording, zero right picks blocked, wrong picks past the guard under ten, on a matched test set.
- **6.0, everywhere.** A stranger installs her: the signed, notarized app that fetches its models on first run; Windows and Linux get a browser window from `serve.py` on the llama.cpp backend, so no second GUI; MCP both ways, so Claude, Cursor and Shortcuts can borrow her hands and she can be handed a server, asked first. Check: a fresh Mac user account and a Linux container each go from download to a first answered command with no terminal.
- **7.0, she remembers and she comes to you.** "Remember I take the 8:10 bus" lands in a plain file she reads back into every answer; a morning brief (what needs me, am I free, weather, the one thing due) she pushes as a notification before you ask; Shortcuts automations she writes herself for the repeats Reminders will not take. Check: a week of briefs with no wrong fact, memory recalled in `eval/basic_questions.py`.
- **8.0, she learns from the big ones.** Phase 6 distillation: frontier models as teachers write varied phrasings and hard cases, she trains on them, the picker and the answer chain both rise. Check: the same hands and knowledge evals, both up, nothing confidently wrong.
- **9.0 and 10.0** are decided when 8.0 ships, from the gaps the loop finds then. Candidates: inside Joshua Tree with no libc (joshuatree issue #156), her own voice model, a phone as a thin client to your Mac.

### Biggest gaps vs the market (set 2026-09-23)
Measured against Siri and Apple Intelligence, and the ChatGPT and Claude desktop apps. Ranked; the loop works top down.

1. **Picker coverage.** Her own picker knows 77 of 105 tools by wording (round six, docs/BAKEOFF.md); the rest need exact phrasing. Close the remaining 28 with training templates for the tools that still have none, then two-step picking (family, then tool) and constrained output if aggregate accuracy still lags, scored by `eval/hands.py`, with no regression on the 77.
2. **Cross-source answers, SHIPPED 2026-09-23.** "What needs my attention" (unread mail, today's calendar and due reminders, ranked, the 9B writing three lines) and "am I free Thursday afternoon" / "when am I free this week" (the calendar's open gaps for a day or the week, not just today's list). Both exact-router tools in `tools_apps.py` (`needs_attention`, `free_when`).
3. **Voice, SHIPPED 2026-09-23.** Barge-in (a real run of loud mic energy while she's speaking kills `say` and drops straight back into listening, `should_barge_in` in `voice.py`, no new model) and a wake word (`--wake samantha`, off by default: idles in short chunks until a transcript starts with the word, `wake_match`).
4. **Eyes and hands, camera half SHIPPED 2026-09-23.** GUI control is one step at a time. The camera half: `see_camera` ("what am I holding", "read this label", "look at this"), one frame via ffmpeg avfoundation, the same vision model see_image uses. Asks first, `tools_see.py`.
5. **Research and code, code half SHIPPED 2026-09-23.** Pages beyond Wikipedia still open. The code half: `run_code` ("stats on sales.csv", "average of the price column in sales.csv", "chart sales.csv", "plot column price of sales.csv"). The biggest local model writes a short script from the request and the CSV's own header, and it only runs in a fresh temp folder holding a copy of that one file, no network, a 20 second timeout, a memory cap, output capped at 2000 characters. Asks first, `tools_code.py`.
6. **Install, mostly SHIPPED 2026-09-23.** `gui/package.sh` builds a self-contained SamanthaGUI.app: `gui/launcher.sh` creates her own Python env in Application Support and installs `requirements.txt` on first open, showing a plain "setting up, about two minutes" state instead of crashing (its shell logic is unit tested with a mocked HOME, `tests/test_launcher.py`, no Xcode needed); the base model and Whisper still fetch lazily through mlx-lm/mlx-whisper on first use, exactly the way chat.py already gets them, nothing extra to pull. Not fully shipped: this Mac has no Developer ID Application certificate, so the built zip is signed with Apple Development only, and no notarytool keychain profile exists to notarize headless. See Joshua's Mac to-do.

### Road to 1.0.0 (set 2026-09-20)

1.0.0 means you can sit down, talk to her, and she answers and acts without a rewrite. Each box ships as its own tagged release. No box gets ticked without a check that fails when it breaks.

Shipped and off the list: a 1.7B head that answers in 5 seconds; music and personal tools; know things (62/65, 0 confidently wrong, `eval/basic_questions.py`); browser tabs (list, switch, close, read the rendered page); a real harness (`harness.py`, wired into `chat.py`, asks before writes); her own head for 77 of 103 tools (`hands-adapter`, `eval/hands.py`); the ten image tools smoke tested for real (`eval/smoke_images.py`).

Gaps, in order:

- [ ] **Her own head, the rest.** Shipped 2026-09-23 (docs/BAKEOFF.md "round six"): the round-five regression was a training/guard mismatch on `ask_document`, not the guard being too strict; fixing it and retraining raised the shipped picker to 77 of 103 tools with no regression on the tools round four already handled. 26 tools still have no training templates and route through the exact router only. Not blocking 1.0.0.

### Joshua's Mac to-do (only these need the keyboard)
The loop runs in the cloud and cannot reach Cloudflare or this Mac. Tick a box when done, the loop picks it up.

- [ ] Try voice and on-screen control on the Mac: `python3 chat.py --voice` needs the microphone once, "click ..." needs cliclick (installed) plus Screen Recording and Accessibility for the terminal (macOS asks)
- [ ] Get a Developer ID Application certificate (this Mac only has Apple Development, 3rd Party Mac Developer Application and iPhone Distribution; none of those pass Gatekeeper for a stranger). Apple Developer site, Certificates, new Developer ID Application cert.
- [ ] Store a notarytool keychain profile once: `xcrun notarytool store-credentials samantha-notary --apple-id <your Apple ID email> --team-id <your Team ID> --password <an app-specific password from appleid.apple.com>`. After both, `./gui/package.sh` signs with the real identity and notarizes headless on its own.

### How we compete with trillion-dollar labs (set 2026-09-22)
We will not out-think Claude or GPT: that is data centres and years. We win where they structurally can't follow:
1. **It's yours and it's local.** Runs on your Mac, no account, no per-query cost, nothing leaves the machine. They can't ship that without giving away the model.
2. **Hands on your real computer.** Exact, instant tools (86 and counting) that open, edit, search, remember, and ask before writing. Frontier chat apps still mostly live in a browser tab.
3. **Never confidently wrong.** Grounded answers with sources, declines instead of guessing. A small model that says "I don't know" beats a big one that invents.
4. **Borrow their brains, legally.** Use frontier models as teachers (Phase 6 distillation) and as tools she can call when asked, so her floor rises with theirs.
5. **Tiny and fast.** 0.5B picks tools in milliseconds on a Mac Mini. Speed and reliability are the product.
Every loop iteration should move one of these five.

### Compatibility, honestly scoped (set 2026-09-23)
Samantha's whole design is Mac plus MLX (Apple Silicon), and that is not a detail to port around, it is the reason she is free, fast and private. Each step below changes what runs where, in real, increasing order of cost:
1. **Native macOS GUI, SHIPPED.** `gui/SamanthaGUI.swift`, same shape as `menubar/PaintBar.swift`: a real chat window driving `chat_pipe.py` (the exact answer chain, kept warm the whole session), a native confirm bar before any write. No backend change, MLX stays exactly as is.
2. **Windows and Linux, SHIPPED.** MLX is Apple Silicon only, full stop, so this is a second inference backend: `training/export_gguf.py` fuses hands-adapter and quantizes to GGUF (Q8_0), `Modelfile` makes it an Ollama model with the same system prompt and stop token as the MLX picker, and `tools_agent.py`'s `pick()` uses MLX when it's importable and falls back to llama-cpp-python over that GGUF otherwise. `serve.py`'s Ollama-compatible `/api/chat` was already reachable from any OS; now the picker and chat both are too. What stays Mac-only regardless of backend: every tool that touches AppleScript (Music, Notes, Reminders, Calendar, Mail, Finder), Pixelmator, or the screen and camera.
3. **iPhone and Android.** A phone cannot run a model her size at a useful speed today. Two honest shapes, not a port: a genuinely small on-device model built for a phone, or the phone as a thin client talking to your own Mac as a server over your network. Either way it is closer to a new product than a build-out of this one.
4. **Inside Joshua Tree (his own OS, i386, no libc).** The 0.5B picker cannot fit 32-bit memory, so this is a llama2.c-style engine in plain C on the kernel side (joshuatree issue #156) plus a distilled 15 to 40M model trained here (Phase 6). Chat already reaches her over /api/chat today.
Ship in that order. Skipping straight to phone apps without 1 and 2 first would mean nothing shared with this codebase at all.

### Gaps found by the loop
The loop compares her with other assistants (Siri and Shortcuts, Apple Intelligence, Claude and ChatGPT desktop with MCP, Open Interpreter, Raycast AI, local Ollama agents), adds each real gap here with where it was seen, builds it, then deletes the line once it ships (history lives in git). Newest and biggest first.

- [ ] Docs in her voice: the README intro is hand-written to SOUL.md; have the 9B (warm, briefed with SOUL.md) redo the intro, ABILITIES.md and WHITEPAPER.md in first person, then check facts and house rules by hand. Direct request, 2026-09-23
- [ ] Edit the last draft: "make it shorter", "friendlier", "add a line about Friday" rewrites the file write_document just saved, showing the diff and asking first. Seen in ChatGPT canvas, Claude artifacts
- [ ] Draw on the Mac, not just the page: local image generation (Flux or SD through MLX) is a 6 GB model on a 16 GB Mac, so it only runs with everything else closed; a real ability, honestly scoped. Seen in ChatGPT images, Gemini
- [ ] See better: the 3B vision model gets the gist but misnames details (called the Dock a taskbar); try a 7B when memory allows, and let click_text use her eyes for icons with no text. Seeing shipped v2.1.0 (see_screen, see_image)
- [ ] Research, the rest: pages beyond Wikipedia (news, docs), follow-up questions on a brief, and saving a brief to a file. Research shipped v3.0.0
- [ ] Repeating reminders: one-off timed ones shipped ("remind me tomorrow at 9am", "in 20 minutes", "on friday at 5pm" set a real due date); "every morning" is declined because Reminders takes repeats only from its own window, so the honest path is a Shortcuts automation she sets up, asking first. Seen in ChatGPT tasks, Gemini scheduled actions
- [ ] GUI control, the rest: multi-step flows ("log in to X") planned by the agent with a yes per step, clicking icons that have no text, and a picture of where she will click. Click, type and press shipped in v2.0.0. Seen in Claude computer use, Open Interpreter

### Phase 6: Distillation, not scale (month 4+, optional/ambitious)
Instead of chasing bigger bases, use a frontier model (Claude) to generate high-quality synthetic training examples in our exact style, then distill that into Samantha. This is literally how most useful small models are built today, nobody pretrains from raw internet text anymore if they can help it.

### What we will never do on this budget
Pretrain a foundation model from raw text at frontier scale. That needs a data-center, a research team, and normally $10M+ in compute even for a "small" frontier-adjacent model. Not the plan, the plan is a small model that's genuinely ours and genuinely useful, which is a completely different (and completely reachable) goal.

### Win condition
Not "beat GPT." Win condition is: ask it to draft something in our voice, or answer a question about one of our own projects, and the answer is actually good enough to use without rewriting it.

### Open backlog

- [ ] Painting hands (pixelmator/): paint the Last Supper at 4000 layers, polish the Mona Lisa, rebuild the bcgd logo as a text-layer spec, speed probes (group layers, fill inside make)
- [ ] Picker trick: constrained output. Let her only emit a real tool name and an argument copied from the sentence (mlx_lm logits processor), so a wrong-shaped pick is impossible instead of caught after
- [ ] Picker trick: train on her mistakes. Write NEW templates for the kinds of wording she misses. Never copy items from hands-data/test.jsonl into training, that would fake the score
- [ ] Picker trick: teacher and student. Have the local 8B write a few hundred varied phrasings per tool with labels, train on those alongside the templates
- [ ] Picker trick: more "not a command" and "not sure" examples so she abstains instead of guessing
- [ ] PaintBar: share its background setting with Samantha's own paint tool, add launch at login

### 100 tools (set 2026-09-21)

The model picks, the code does. More menu is more power. Rules: every tool ships with cases in `eval/actions.py` and phrasings in `gen_hands_data.py`, the gate baseline only moves up, anything that writes, sends or deletes asks first through the harness, stdlib and built-in macOS commands only.

- [ ] Two-step picking: she picks a family first, then a tool inside it, so no single choice is bigger than about twelve. Retrain the picker for it and score it before adding tools in bulk
- [ ] System family, the rest: dark mode, bluetooth, do not disturb, brightness, running apps, quit an app (wifi, lock, sleep, uptime and ip address shipped)
- [ ] Organizer family: list reminders, complete a reminder, add a calendar event, tomorrow's calendar, search notes, append to a note
- [ ] Browser family, the rest: download a file (tabs, switching, closing and reading the rendered page shipped)
- [ ] Dev family: git status, recent commits, run a repo's tests, open PRs, open a repo in the editor
- [ ] Knowledge family, the rest: define a word (translate, units, time in a city and calculate shipped)
- [ ] Blender family (Blender 5.2 LTS is installed, runs with no window: `blender -b -P script.py`): render a scene to an image, make a simple 3D object from a fixed menu, turn a logo into 3D text, convert between 3D formats, report what is in a file. Same rules as every family: new file, mocked unit tests that pass on Linux, one live smoke run each
- [ ] Sharp paintings: 20,000 layers removes the blocky look and 60,000 looks photographic (simulated offline). Grouping layers was measured SLOWER (460 s against 336 s flat for 2000 layers) and reverted. Hiding the app is the one proven speed-up. Next idea to measure: merge same-color neighbor cells so each layer buys more picture
