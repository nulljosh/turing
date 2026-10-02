# Roadmap

Samantha is a small local model (Qwen, fine-tuned) with hands: she can open apps, browse, read your files, answer from your notes, and act on your Mac, entirely offline, no account, nothing sent out. v4.16.3 is live, with code in app/, helpers in scripts/, and supporting documents in docs/. She has 126 tools. Her own picker gets 343 of 465 blind test phrasings right, with 17 wrong picks past the safety guard and 36 right picks refused. She knows 62 of 65 held-out facts with nothing confidently wrong. She runs natively on the Mac, and the picker and chat both run on Windows and Linux too. The installer is signed with Developer ID and notarized, so it opens on a stranger's Mac with no warning.

Full phase-by-phase history lives in `docs/HISTORY.md` and the picker's model comparisons in `docs/BAKEOFF.md`.

### Next few minors

- **4.5, edit the last draft. Shipped 2026-09-24.** "Make it shorter", "friendlier", "add a line about Friday" rewrites the file `write_document` just saved, shows the diff, and asks before saving.
- **4.6, edit any file, write code to disk. Shipped 2026-09-24.** "Edit notes.md: make it shorter", "write a python script that prints the date to today.py": she edits any text file in your home folder or writes new code, always showing a diff and asking first.
- Docs in her own voice: have the local 9B redo the README intro, ABILITIES.md and WHITEPAPER.md in first person, then check facts and house rules by hand.
- Draw on the Mac, not just the page: local image generation (Flux or SD through MLX) is a 6 GB model on a 16 GB Mac, so it only runs with everything else closed.
- See better: try a 7B vision model when memory allows, and let `click_text` use her eyes for icons with no text.
- Repeating reminders: one-off timed reminders already work; "every morning" needs a Shortcuts automation she sets up herself, asking first, since Reminders only takes repeats from its own window.
- GUI control, the rest: multi-step flows ("log in to X") planned one step at a time with a yes per step, clicking icons that have no text, and a picture of where she'll click.

### Gaps with frontier models (set 2026-09-25, the loop re-checks every round)
Not data centres or training data: the gaps we can actually close. Each round picks work that shrinks one, and updates its line here when it moves.

- [ ] **Understands wording, not patterns.** Round nine (4.15): her picker gets 1300 of 1895 test phrasings right (round eight 1197), 83 wrong picks past the guard (was 141), 0 right picks refused; round ten (4.15.1) tightened the guard to 50 wrong past it; round eleven (4.15.2) to 9, under the 5.0 bar, but measured on the same test set the guard rules were tuned on. Held-out check (4.15.3, eval/heldout.jsonl, 512 phrasings written blind): 361 right, 29 wrong past the guard, 24 right picks refused (19 after the 4.15.4 guard; that round saw the held-out breakdown, so a second fresh held-out set is needed before 5.0). Second blind set (4.15.5, eval/heldout2.jsonl, 500 rows): 350 right, 20 wrong past the guard, 16 refused. Round thirteen (4.15.6, guard only): held-out 26 past guard, 19 refused; heldout2 19 past, 16 refused; standard unchanged. That round bisected against both held-out summaries and read the first set's breakdown, so both have shaped decisions now: a third fresh blind set judges 5.0. Third blind set (4.16.2, eval/heldout3.jsonl, 465 rows after the overlap filter, written by a fresh writer that saw only the tool list): 343 right, 17 wrong past the guard, 36 right picks refused. That is the honest number, and 5.0 needs it under ten and zero. Every tool is trained. Round fourteen is prepared (4.17.3: thicker two-argument training, 130 guard refusals of her own training phrasings fixed, `training/picker_round.sh 14` runs it on the Mac). Round fifteen (4.17.8, guard only): standard 10 past guard, heldout2 6, but blind heldout3 only 16 past and 32 refused, flat; more guard rules stopped helping, round sixteen trains argument shape. Round sixteen (4.17.9): a fourth blind set to steer by, and "trash this file" asks which; blind heldout3 12 past guard, 26 refused. Rounds seventeen to twenty (4.17.10 to 4.17.13): more fresh blind sets, vague asks get "which file?", heldout3 retired; the sealed judge is now heldout6: 12 past guard, 11 refused. Closes with 5.0: fewer than ten wrong past the guard.
- [ ] **Plans.** Started in 4.13: app/planner.py makes a step list from her real tools (the local model, or a split on "and"/"then" with no model), shows it before running, checks each result and stops on a failure, takes a value from an earlier step only through a declared placeholder from a safe producer, and asks before every write; law 11 keeps what she reads from adding or changing a step. Not closed: she stops on a mistake but does not yet recover or re-plan.
- [ ] **Remembers the conversation.** Started in 4.12: "do that again", "same but for nimble", "what about tomorrow", "open it" work for every tool from a ten-turn history; a past result never supplies a command (law 10). Closes at 7.0 with memory across sessions.
- [ ] **Thinks for herself.** Real answers come from the borrowed 9B; eyes and voice are small models that miss details. Target: 8.0, distillation from frontier teachers.
- [ ] **Learns from use.** Started in 4.11: say "good", "wrong" or "wrong, I meant X" after any answer and it is saved on the Mac (~/.samantha/feedback.jsonl); training/feedback_to_data.py turns corrections into picker training rows, never copying test phrasings. Closes when the next retrain actually uses them.
- [ ] **Doesn't believe everything she reads.** Mostly closed in 4.14: reads are fenced (law 9), never replayed (law 10), can't change a plan (law 11), and every write a model proposes is checked against your own words before it can even ask you (law 12, 40 of 43 write tools, zero false blocks). Left: three writes with no argument rely only on your yes (screen clicks got the own-words check in 4.17.2).

### Majors

- **5.0, her own head.** Every tool picked by her own model, nothing through the exact router. Check: `eval/hands.py` scores 106 of 106 tools by wording, zero right picks blocked, and fewer than ten wrong picks slip past the guard, on a matched test set.
- **6.0, everywhere.** Notarized installer for a stranger's Mac. Windows and Linux get a real browser window, not just an API. MCP works both ways: other apps can borrow her hands, and she can be handed a server to use.
- **7.0, remembers and comes to you.** A memory file she reads back into every answer. A morning brief pushed before you ask. Shortcuts automations she writes herself.
- **8.0, learns from the big ones.** Frontier models teach her: distillation raises the picker and the answers together.
- **9.0, in your pocket.** Talk to her from anywhere: an iPhone app that is a thin client to your own Mac over your own network, so her hands, files and memory come with you and nothing touches a cloud. Voice first: a wake word, cutting in while she speaks, and her own voice instead of `say`. Check: from the phone, "what needs me" and "remind me at 5" run on the Mac and answer out loud in under two seconds warm.
- **10.0, her own home.** She runs inside Joshua Tree, the kernel built here from nothing, with no libc and no borrowed runtime: her picker's inference written in freestanding C, the chat app asking her directly instead of calling out to /api. Kernel and model, both ours, top to bottom. Check: boot Joshua Tree in QEMU with the network off, type "remind me to call mom", and her own picker, running on that kernel, picks new_reminder.

### What needs Joshua's keyboard

- [ ] **On the Mac, next time (set 2026-09-30):**
  - [ ] `training/picker_round.sh 14`: trains picker round fourteen (about 20 min), compares it with the shipped adapter, reads the blind heldout3 set once if it is no less safe. Commit `eval/picker-rounds.log` after. The 5.0 bar (under 10 wrong past the guard, 0 right picks refused) can only be measured there.
  - [ ] `python3 eval/screen_bench.py` (needs qwen3:1.7b in Ollama), and press Escape once during a real screen job.
  - [ ] Paint one photo per style on the Mac (`paint lake.jpg as a sketch`, and the other five): the cloud previews used Pillow, this checks the real ImageMagick output. Mosaic and glass lose detail on faces; tune.
  - [ ] Painting styles shipped as 4.17.4; they are a minor-release ability, so 4.18.0 waits for its badge motif (needs magick, potrace and OCR on the Mac).
- [ ] Try voice and on-screen control on the Mac: `python3 app/chat.py --voice` needs the microphone once, and "click ..." needs Screen Recording and Accessibility permission for the terminal.

### How we compete with trillion-dollar labs

We will not out-think Claude or GPT, that's data centres and years. We win where they structurally can't follow:
1. It's yours and it's local. Runs on your Mac, no account, no per-query cost, nothing leaves the machine.
2. Hands on your real computer. Exact, instant tools that open, edit, search, remember, and ask before writing.
3. Never confidently wrong. Grounded answers with sources, declines instead of guessing.
4. Borrow their brains, legally. Frontier models as teachers and as tools she can call, so her floor rises with theirs.
5. Tiny and fast. Picks tools in milliseconds on a Mac Mini.

### Compatibility, honestly scoped

Her design is Mac plus MLX, and that's the reason she's free, fast and private, not a detail to port around.
1. Native macOS GUI, Windows and Linux (browser window, same picker and chat) are done.
2. iPhone and Android need a genuinely different shape: either a small on-device model built for a phone, or the phone as a thin client to your own Mac. Closer to a new product than a build-out of this one.
3. Inside Joshua Tree (his own OS, i386, no libc) means a tiny engine in plain C plus a distilled 15-40M model, since the current picker can't fit 32-bit memory.
4. Chat already reaches her over `/api/chat` today, so ship in that order, skipping straight to phone apps first would mean nothing shared with this codebase at all.

### Never on this budget

Pretrain a foundation model from raw text at frontier scale, that needs a data centre, a research team, and normally $10M+ in compute.

### Win condition

Ask her to draft something in our voice, or answer a question about one of our own projects, and the answer is good enough to use without rewriting it.

### Open backlog

- [ ] **Voice and face, next:** `--character <name>` to switch faces and voices by name; her idle loop on the landing page; Secretary's phone calls in her voice (waiting on Twilio support ticket 29739232 to restore account access).
- [ ] **This week: computer use.** Give her a task ("book the 3pm slot on this page", "fill in this form from my notes") and she drives the Mac to finish it, like ChatGPT's agent. She already has see_screen, click_text, type_text, press_key and a six-step agent. Missing, in build order:
  - [ ] Every click and keystroke shown before it runs, one yes covers one task, Escape stops her at once (Escape shipped in 4.17.1; one-yes-per-task still open)
  - [ ] A test bench of ten local tasks (TextEdit, Finder, Safari on a local page, System Settings read-only) scored headless, so each round is measured
- [ ] **Frontier gaps.** Where she trails the big models, cheapest fix first:
  - [ ] Invented tool names ("free_space", "date_today"): snapping to the closest name was tried and dropped (one good snap in 1895 picks, six wrong ones, "remove_file" became move_file); the family-first picker below is the real fix
  - [ ] Argument shape: tools read loose wording themselves ("between 1 and 100", "dec 25 2026", "150 lbs to kg") instead of the picker learning every format
  - [ ] Gives up to "agent" on one-step asks: more single-step training templates for tools she hands off
  - [ ] Multi-step planning: the agent loop above is the fix
  - [ ] Writing quality: route drafts and long answers to the local 8B, keep the 0.5B for picking
  - [ ] Long documents and images: chunked reading for documents, see_screen's vision model for images
- [ ] Painting hands (pixelmator/): paint the Last Supper at 4000 layers, polish the Mona Lisa, rebuild the bcgd logo as a text-layer spec, speed probes (group layers, fill inside make)
- [ ] Picker trick: constrained output. Tried once (round six, tool-name logits trie) and it collapsed accuracy instead of helping; worth another look feeding the prefix through the chat template's own generation-prompt path
- [ ] Picker trick: train on her mistakes. Write new templates for the kinds of wording she misses, never copy test cases into training
- [ ] Picker trick: teacher and student. Have the local 8B write varied phrasings per tool with labels, train on those alongside the templates
- [ ] Picker trick: more "not a command" and "not sure" examples so she abstains instead of guessing
- [ ] PaintBar (moved to nulljosh/paintbar): share its background setting with Samantha's own paint tool, add launch at login
- [ ] Landing demo logo is too basic: real design pass, the SVG bloom rules look thin next to the real tool
- [ ] Landing demo graphics are slow: profile paint.js and drawLogo, cap cells, batch with requestAnimationFrame
- [ ] Two-step picking: pick a family first, then a tool inside it, so no single choice is bigger than about twelve
- [ ] System family, the rest: brightness and turning bluetooth on or off (this Mac has no CLI for either and nothing gets installed; dark mode, running apps, quit an app, bluetooth status and Do Not Disturb via a Shortcut shipped in 4.8)
- [ ] Browser family, the rest: download a file
- [ ] Blender family (Blender 5.2 LTS installed, headless): render a scene, make a simple 3D object, turn a logo into 3D text, convert between 3D formats, report what's in a file
- [ ] Sharp paintings: merge same-color neighbor cells so each layer buys more picture
