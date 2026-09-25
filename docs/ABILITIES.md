# What she can do

Every ability, in the words you say. Anything that writes, sends or looks at your screen asks first. The landing page runs the same router in the browser, so every line here works there too, except the ones that need a real Mac (the page says so).

## Talk and listen

- **Talk.** `./.venv/bin/python chat.py --voice`: you speak, Whisper transcribes on the Mac, she answers out loud. Talk over her while she's answering and a real run of your voice on the mic cuts her off and she starts listening right away. `--wake samantha` (off unless you pass it) keeps her idle, listening in short chunks, until you say the wake word first; then she drops it and takes the rest as the command.
- **Transcribe.** "Transcribe the video ~/Desktop/clip.mp4": the words out of any video or audio file in your home folder, same Whisper pipeline.

## See

- **Look.** "Look at my screen and tell me what's wrong with this chart", "what's in ~/Desktop/cat.png": a local vision model answers. Asks first.
- **Look through the camera.** "What am I holding", "read this label", "look at this": one frame from the Mac's own camera, the same vision model, nothing saved after the answer. Asks first; a plain sentence if there is no ffmpeg or no camera.
- **Read the screen.** "Read my screen", "find Sign in on my screen": the system's own text recognition.

## Know

- **Answer.** Questions go down a ladder: exact routes, her own picker, the project FAQ and your notes, then Wikipedia and DuckDuckGo, then her offline library (the fieldbook plus ~10,000 Wikipedia leads). If nothing holds the answer she says so.
- **Research.** "Research the history of the printing press": Wikipedia, her library and your notes, then a brief with a source after every sentence. Name a page in the question ("research the docs at example.com/api") and she reads it and cites it too, or tells you plainly when it's JS-only or blocked instead of pretending it never came up. "Tell me more about X" tries the sources she already has before going back out for fresh ones. "Save that" writes it to a file.
- **Run code.** "Stats on sales.csv", "average of the price column in sales.csv", "chart sales.csv", "plot column price of sales.csv": the biggest local model writes a short Python script from your request and the file's header, and it only ever runs in a sandbox, a fresh temp folder holding a copy of that one file, no network, a time and memory cap. A chart comes back as a real PNG. Asks first.
- **Summarize.** "Summarize ~/Desktop/report.pdf", "summarize this page", "summarize my unread mail": three to five real sentences from the biggest local model.
- **Translate.** "Translate good morning to French", "how do you say thank you in Japanese", "translate the page github.com into Spanish". Offline.
- **Ask a bigger brain.** "Ask qwen why the sky is blue", "ask claude ...": the question goes to a bigger model on your Mac, never the cloud, and the answer names the model.
- **Remember.** "Remember that my dog is called Biscuit", "what do you remember about my dog", "forget Biscuit". A file only she reads.
- **Follows the conversation.** "Do that again", "again for nimble", "same but for cadence", "what about tomorrow" right after "what's on my calendar today", "open it"/"read it" right after she finds or writes a file: she rewrites the follow-up into the explicit thing you mean and routes it exactly like anything typed outright, so a write still asks first. "Undo that" is out of scope, she says so plainly. Never replays a page or note's own words as a command, only your own.
- **Learns from you.** Say "good", "thanks that's right" or "bad", "wrong", "wrong, I meant X" right after any answer and she logs it, local only, caught before it could ever be mistaken for a command. "How am I rating you" shows the count and the last five downs.
- **Answer inside Joshua Tree.** The from-scratch i386 kernel's own Chat app talks to her over `/api/chat`, an Ollama-compatible endpoint (`worker.js`); she answers from a condensed pack of the OS's own docs (`web/jt_docs.js`) before falling back to the general pipeline above.

## Do

- **Apps and sites.** Open an app, go to a site, search the web or one site, read a page, list, switch, read and close Chrome tabs.
- **Her hands.** "Click Sign in", "type hello", "press return", "log me into X": she reads the screen, acts one step at a time, asks before each.
- **Files.** "Find resume.docx", "what did I just download", "how big is ~/Movies", "read the document ~/notes.pdf", "find milk in the document ~/notes.pdf", then "move", "copy", "rename", "zip", "unzip", "trash" any of them. Trash is Finder's Trash, never a hard delete.
- **Write.** "Draft an email about the release", "write a doc about the roadmap": the local model drafts it, she saves it in your home folder.
- **Edit the last draft.** "Make it shorter", "make it friendlier", "add a line about Friday": rewrites the file write_document just saved, shows a diff of the change, and asks before writing it. Says plainly when there is no draft yet.
- **Edit any file, write code.** "Edit notes.md: make it shorter", "in ~/Desktop/plan.md, fix the typo", "write a python script that prints the date to today.py": any text file inside your home folder, or new code from the biggest local model, the whole change shown as a diff, written only on a yes.
- **Mail, calendar, reminders, notes.** "Unread mail", "anything from the bank in my mail", "what's on my calendar today", "remind me tomorrow at 9am to call mom", "take a note buy milk".
- **Organizer.** "What are my reminders", "complete the reminder to buy milk", "add lunch with sam to my calendar tomorrow at noon", "what's on my calendar tomorrow", "search notes for eggs", "add eggs to my shopping note". Reads are read only; the writes ask first, and a reminder or note that does not match changes nothing.
- **What needs me.** "What needs my attention", "what needs me": one ranked answer built from your unread mail, today's calendar and due reminders, three short lines from the biggest local model. Says plainly when everything is clear, never invents a message or a meeting.
- **Am I free.** "Am I free Thursday afternoon", "when am I free this week": your calendar's open gaps for that day or the week, business hours, not just today's list.
- **The Mac.** Volume, battery, music, timers, the weather, the clipboard, screenshots, disk space, memory, Wi-Fi, IP, uptime, system info, sleep the screen, show a file in Finder, run any Apple Shortcut by name.
- **System.** "Turn on dark mode", "what apps are running", "quit spotify", "turn on do not disturb", "bluetooth status". Dark mode and running apps are read plainly; quit refuses Finder, her own terminal and anything not actually running; Do Not Disturb runs a named Shortcut if it exists, or says plainly how to make one; Bluetooth is read only, this Mac has no blueutil or brightness CLI to drive them.
- **Dev.** "Git status", "recent commits in cadence", "run turing's tests", "open prs", "open the nimble repo in vs code". Any repo found by folder name under ~/Documents/Code, turing itself when none is named. Git status and commits are read plainly; running tests picks the repo's own command (npm, pytest, python3 or swift) and asks first; open PRs is read only, honest when gh is missing or not logged in; opening the editor prefers `code`, then VS Code, then Finder.
- **Pictures.** "Draw a fox in the snow" (on the landing page), "paint ~/Desktop/mona.jpg" from 30,000 squares, "make me a logo for turing" (always an icon, never text), and remove a background, upscale, enhance, grayscale, rotate, flip, resize, crop, convert. All of it runs through ImageMagick, no Pixelmator.
- **Math, time, chance, text.** Calculate, convert units, tips, primes and factors, roman numerals, the time in any city, dates and days between, dice, coins, random numbers, passwords, UUIDs, SHA-256, base64, word counts, morse, tidy JSON.
- **Plug in.** She speaks MCP both ways: any assistant can use her tools, and she can call another server's tools when you name it.
- **Safe with what she reads.** A page, an email, a document, a note, the screen, another server's tool: none of it can pick or trigger a tool on its own. Only your own words do that, law 9.

## Limits, plainly

Her own picker knows 77 of 106 tools by wording; the rest route through exact matches. Multi-step work borrows a small local model (qwen3:1.7b through Ollama). She never calls another MCP server on her own. She cannot reason like a frontier model and does not try; see `roadmap.md` for what is next and `LAWS.md` for what she will never do.

Windows and Linux now run the picker and chat: `training/export_gguf.py` fuses hands-adapter into the base model and quantizes it to GGUF, `Modelfile` turns that into an Ollama model (`ollama create samantha -f Modelfile`), and `serve.py`'s Ollama-compatible `/api/chat` is reachable from there with no MLX and no Mac. `tools_agent.py`'s `pick()` uses MLX when it's importable and falls back to llama-cpp-python over that same GGUF otherwise, same prompt, same stop token, same decoding. Everything that touches the Mac itself stays Mac-only regardless of backend: AppleScript (Music, Notes, Reminders, Calendar, Mail, Finder), the screen (see_screen, click, type), and the camera. Image tools run on ImageMagick, so they are not on that list. A phone is its own build-out, not covered here; see `roadmap.md`.
