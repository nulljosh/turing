# Roadmap

Samantha is a small local model (Qwen, fine-tuned) with hands: she can open apps, browse, read your files, answer from your notes, and act on your Mac, entirely offline, no account, nothing sent out. v4.4.0 is about to cut. She has 106 tools. Her own picker (not the exact-match router) gets 958 of 1352 test phrasings right, with 61 wrong picks that slip past the safety guard. She knows 62 of 65 held-out facts with nothing confidently wrong. She runs natively on the Mac, and the picker and chat both run on Windows and Linux too. The installer is signed but not yet notarized, so a stranger's Mac still needs a manual "open anyway."

Full phase-by-phase history lives in `docs/HISTORY.md` and the picker's model comparisons in `docs/BAKEOFF.md`.

### Next few minors

- **4.5, edit the last draft.** In flight. "Make it shorter", "friendlier", "add a line about Friday" rewrites the file `write_document` just saved, shows the diff, and asks before saving.
- **4.6, edit any file, write code to disk.** Given an instruction, she edits an existing file or writes new code, always showing a diff and asking first.
- Docs in her own voice: have the local 9B redo the README intro, ABILITIES.md and WHITEPAPER.md in first person, then check facts and house rules by hand.
- Draw on the Mac, not just the page: local image generation (Flux or SD through MLX) is a 6 GB model on a 16 GB Mac, so it only runs with everything else closed.
- See better: try a 7B vision model when memory allows, and let `click_text` use her eyes for icons with no text.
- Repeating reminders: one-off timed reminders already work; "every morning" needs a Shortcuts automation she sets up herself, asking first, since Reminders only takes repeats from its own window.
- GUI control, the rest: multi-step flows ("log in to X") planned one step at a time with a yes per step, clicking icons that have no text, and a picture of where she'll click.

### Majors

- **5.0, her own head.** Every tool picked by her own model, nothing through the exact router. Check: `eval/hands.py` scores 106 of 106 tools by wording, zero right picks blocked, and fewer than ten wrong picks slip past the guard, on a matched test set.
- **6.0, everywhere.** Notarized installer for a stranger's Mac. Windows and Linux get a real browser window, not just an API. MCP works both ways: other apps can borrow her hands, and she can be handed a server to use.
- **7.0, remembers and comes to you.** A memory file she reads back into every answer. A morning brief pushed before you ask. Shortcuts automations she writes herself.
- **8.0, learns from the big ones.** Frontier models teach her: distillation raises the picker and the answers together.
- **9.0 and 10.0** get decided once 8.0 ships, based on the gaps the loop finds by then. Candidates: living inside Joshua Tree with no libc, her own voice, a phone as a thin client to your Mac.

### What needs Joshua's keyboard

- Try voice and on-screen control on the Mac: `python3 chat.py --voice` needs the microphone once, and "click ..." needs Screen Recording and Accessibility permission for the terminal.
- Get a Developer ID Application certificate so the app passes Gatekeeper for a stranger.
- Store a notarytool keychain profile once, so `./gui/package.sh` can notarize headless on its own.

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

- [ ] Painting hands (pixelmator/): paint the Last Supper at 4000 layers, polish the Mona Lisa, rebuild the bcgd logo as a text-layer spec, speed probes (group layers, fill inside make)
- [ ] Picker trick: constrained output. Tried once (round six, tool-name logits trie) and it collapsed accuracy instead of helping; worth another look feeding the prefix through the chat template's own generation-prompt path
- [ ] Picker trick: train on her mistakes. Write new templates for the kinds of wording she misses, never copy test cases into training
- [ ] Picker trick: teacher and student. Have the local 8B write varied phrasings per tool with labels, train on those alongside the templates
- [ ] Picker trick: more "not a command" and "not sure" examples so she abstains instead of guessing
- [ ] PaintBar: share its background setting with Samantha's own paint tool, add launch at login
- [ ] Two-step picking: pick a family first, then a tool inside it, so no single choice is bigger than about twelve
- [ ] System family, the rest: dark mode, bluetooth, do not disturb, brightness, running apps, quit an app
- [ ] Organizer family: list reminders, complete a reminder, add a calendar event, tomorrow's calendar, search notes, append to a note
- [ ] Browser family, the rest: download a file
- [ ] Dev family: git status, recent commits, run a repo's tests, open PRs, open a repo in the editor
- [ ] Knowledge family, the rest: define a word
- [ ] Blender family (Blender 5.2 LTS installed, headless): render a scene, make a simple 3D object, turn a logo into 3D text, convert between 3D formats, report what's in a file
- [ ] Sharp paintings: merge same-color neighbor cells so each layer buys more picture
