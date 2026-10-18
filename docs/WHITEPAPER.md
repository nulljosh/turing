# Turing Technical Whitepaper

**v7.18.0** | October 2026

Turing builds small language models on one Mac. Its first model, Samantha, is a 0.5B chat model trained on your own writing, with a 1.5B head that picks her tools. Both are public on [Hugging Face](https://huggingface.co/trommatic/samantha-hands-1.5b-mlx). She will never out-think a frontier model. She does not try to. She runs on your Mac, costs nothing per question, keeps everything on the machine, and gets real work done with 148 exact tools. When a question is too hard for her, she borrows a bigger brain that also lives on the Mac. You can type to her or talk to her. She can see your screen, click in your apps, and research a topic with sources. She asks before anything that changes something.

## The core idea

A small model cannot hold facts without making them up. So Samantha does not try to remember. She looks things up and she uses tools. The one thing she does hold on to is what you tell her to remember: a short list of facts in a file on your Mac, which she reads back into an answer when a fact shares a real word with your question (at most three, never anywhere public).

Every request goes down the same ladder, and the first rung that holds wins:

1. **Exact routes.** "Set the volume to 30", "what's 15% of 80", "click Sign in". A recognisable command has one right answer, so no model is involved. Instant, and never wrong.
2. **Her own picker.** A 1.5B model ([on Hugging Face](https://huggingface.co/trommatic/samantha-hands-1.5b-mlx)), trained on a free Kaggle GPU to turn loose wording into a tool call. A guard refuses any pick whose argument is not in your sentence, and a pick she is unsure of asks first. On Windows and Linux the 0.5B picker stays, as a [GGUF](https://huggingface.co/trommatic/samantha-hands-gguf). A much smaller distilled copy, about 18,000 integer weights in plain C, now runs inside Joshua Tree's kernel with no float maths and no network; it abstains when unsure, and the C matches its Python reference on every checked sentence. It is tuned to the dev sets, and the sealed sets are unread, so it is called a small picker distilled from her, not her picker.
3. **Her FAQ and your notes.** Questions about the project are answered from its own docs and from your notes (the brain RAG service).
4. **The web, then her library.** Wikipedia and DuckDuckGo first. When the web has nothing or is down, her offline library: the lead of all 10,000 of Wikipedia's vital articles, plus your fieldbook of every science.
5. **Her own words.** Only now does Samantha write an answer herself, and only from passages she was handed. If they do not hold the answer, she says "My notes don't cover that."

Anything too hard goes to the biggest model on the Mac by name ("ask qwen", "ask llama", "ask claude" for the biggest): Qwen3.5-9B through oMLX, or qwen3:8b through Ollama.

## How she is trained

She starts from Qwen2.5-0.5B-Instruct, which already knows language. LoRA adds a small layer of trainable weights on top, trained with Apple's MLX on the Mac itself. No cloud GPU, no API bill.

Her material is everything: your wiki, every project README, whitepaper and roadmap, and the journal. That is 5,680 chunks, six times what she had before.

Then a teacher. Claude writes practice questions and answers from real passages of your docs. A local 9B model reads every pair and throws out answers that miss their question. Each lesson is wrapped in exactly the prompt she sees in real use. A tenth of the passages never reach training, so progress is measured on questions she has never seen. Round two taught her to decline: when her notes lack the answer, she now says so 16 times out of 16 (it was 3).

## What she can do

- **Talk.** `python3 app/chat.py --voice`. Whisper on the Mac turns speech into text, she answers, and she says it out loud. Anything new you send cuts her off, and "shh" silences her. The iPhone app has a mic button too: Apple's on-device dictation in, her reply read out loud, and a plain message if no microphone is plugged in. It passes its simulator test; it has not yet been tried on a real phone with a real mic.
- **Remembers.** The Mac app saves the chat after every answer and brings it back on launch; Cmd-N starts a new one. Her memory file is plain JSON the facts you told her; she reads the ones that fit your question back into her answers on the Mac and on the phone, and "keep my memory in iCloud" moves it into your own iCloud Drive, merged, and "keep my memory on this Mac" brings it back. A morning brief is waiting the first time you open the Mac app each day.
- **Her own typeface.** The landing page, the Mac app and the iPhone app set their words in Samantha Sans, built on Inter, an open face drawn in the spirit of SF and Helvetica, renamed for her under its open font license. Letters and figures are spaced to their own widths, and an I, an l and a 1 never look alike. `scripts/gen_font.py` builds it and checks it.
- **Logos, symbols and avatars.** "Make me a logo for a surf school" draws a bold white glyph that means the subject (a wave here, bread for a bakery, a cup for coffee) on a flat colored tile, and saves an Icon Composer bundle beside the picture. Her words pick the glyph first and her model picks the rest. "Make a symbol for" gives the glyph alone, "make a wordmark for Wavecrest, a surf school" sets the name beside it, and "make an avatar for Alex" draws a friendly face from a name, the same face every time. Never text on an icon, always a new file, always asks first.
- **3D files.** With Blender on the Mac: "what is in model.glb" counts its parts, "render scene.blend" makes a picture, "convert model.glb to obj", "make a torus at ~/Documents/ring.stl" and "make 3D text Turing at ~/Documents/logo.glb" write new files beside what you name, never over one, asking first.
- **Video and web pages.** She tells you how long a clip is, trims it ("trim a.mp4 from 0:10 to 0:25") or makes it vertical, cuts a piece out of a sound file, pulls the sound out of a video, mutes one, makes a gif from it, and "check page.html" opens a local page and says in plain words whether it is blank, dark or broken.
- **Joshua Tree.** "Joshua Tree status" reads the OS's version, open pull requests and whether its test machine is running; "boot" and "stop Joshua Tree" start and stop it headless, asking first; "what did Joshua Tree say" reads its serial log; "type ls into Joshua Tree" sends it keystrokes, asking first; "screenshot Joshua Tree" saves its screen for her eyes, and "what is Joshua Tree showing" looks in one go.
- **Shortcuts she writes.** "Make a shortcut that says good morning" shows the steps, asks first, then saves a Shortcut you add yourself in the Shortcuts app. Four simple actions only (say, notify, open a link, volume), and she never runs or schedules it.
- **On a Raspberry Pi.** She is an app on Joshua Tree, the operating system built here from nothing, running on a real Pi 4. Ask at `Samantha $` and her answer comes from your Mac over your own network. "Write hello world in C and save it as hello.c" writes the code to the Pi's SD card, and `cat JT/HELLO.C` shows it. She only saves under a name you typed.
- **See.** "Look at my screen and tell me what's wrong with this chart." A 3B vision model on the Mac looks and answers. The same model reads one frame from the Mac's own camera ("what am I holding"), deleted right after.
- **Act on screen.** "Click Sign in", "type hello", "press return". She reads the screen to find what you named, and asks before every step.
- **Research.** "Research the history of the printing press." She reads several sources and writes a short brief with a source after every sentence. A sentence she cannot back up is cut.
- **Run code.** "Stats on sales.csv", "chart sales.csv". The biggest local model writes a short Python script from your request and the file's header, and it only ever runs in a sandbox with no network, a time cap and a memory cap.
- **Know what needs you.** "What needs my attention" ranks your unread mail, today's calendar and due reminders into three lines. "Am I free Thursday afternoon" reads your calendar's open gaps. Both read only. "Good morning" is the same brief with the date on top, and the Mac app brings it to you by itself the first time it opens each morning.
- **Write and edit files.** "Draft an email about the release", "edit notes.md: make it shorter", "write a python script that prints the date to today.py". The biggest local model drafts, rewrites or writes the code; the whole change is shown as a diff and nothing lands without a yes. Only inside your home folder, never a hidden or binary file.
- **Organize.** "What are my reminders", "check off call mom", "add lunch with sam to my calendar tomorrow at noon", "what's on my calendar tomorrow", "search my notes for passport", "add eggs to my shopping note". Reading is free; completing, adding and appending ask first.
- **Run the Mac.** "Turn on dark mode", "what apps are running", "quit spotify", "is bluetooth on", "turn on do not disturb". Quitting asks first and never touches Finder or the terminal she runs in; Do Not Disturb goes through a Shortcut you make once, because macOS gives Focus no other door.
- **Code with you.** "Git status of nimble", "recent commits in cadence", "run turing's tests", "any open pull requests on sidewise", "open turing in the editor". Any repo under ~/Documents/Code by name; running tests asks first.
- **Learn from you.** Say "good", "wrong" or "wrong, I meant X" after any answer. She also notes, on your Mac only, every command no tool took and every tool that broke. All of it stays local, and it becomes training data for her next retrain.
- **Follow along.** "Do that again", "same but for nimble", "what about tomorrow", "open it". Follow-ups work for every tool from the last ten turns, and something she read can never be replayed as a command.
- **Plan.** "Find resume.docx and move it to Documents", "git status of nimble and if anything changed run its tests". She shows her plan first, checks every step, stops the moment one fails, and asks before every write. Nothing she reads along the way can change the plan.
- **Long work.** "Work on cleaning up my downloads." She plans in rounds. When a step fails she plans around it, keeps doing the parts that still can be done, and tells you at the end what she could not. Each new plan comes from your words and her own record of what ran, never from what she read. A journal of every round is kept on the Mac.
- **Asks when you point.** "Trash this file", "crop that image", "move my project folder somewhere": the sentence names the tool but not the target, so she asks which one instead of guessing.
- **Everything else.** Her Mac, pictures and painting, math and time, documents, memory across sessions, Chrome tabs, Apple Shortcuts, and MCP in both directions. The picker and chat also run on Windows and Linux through Ollama; the Mac tools stay on the Mac.

## Promises she keeps

She believes what she reads, never what it tells her to do. Text from a page, an email, a file or the screen is fenced as data before any model sees it and can never pick a tool; law 9 tries three injection attacks through every reading tool on every push. When a model proposes a write, it is checked against your own words before it can even ask you: a recipient, path or link that only came from something she read is stopped.


Rules live in docs/LAWS.md and are checked against every tool on every push. Anything that writes, sends or looks at your screen asks first. Private tools never reach a model's menu. Her hands stay in your home folder. On the 65-question knowledge check she gets 62 right and 0 confidently wrong; the rest she declines. On a sealed test of 439 sentences nobody on the project has read, her own picker lets 12 wrong picks past the guard and refuses 11 right ones; 5.0 needs under 10 and none.

## Limits, stated plainly

She cannot reason, do hard math, or write code like a frontier model. That gap is size, and it stays. On unseen questions about your own projects she answers 19 of 43 right; that is the next thing to train. Her eyes get the gist and miss details (she called the Dock a taskbar). The 9B helper takes about four minutes to load off the external drive. Voice, eyes, hands and research need the Mac; the web page is a stand-in.

---
Apache License 2.0, 2026 Joshua Trommel.
