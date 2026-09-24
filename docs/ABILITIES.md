# What she can do

Every ability, in the words you say. Anything that writes, sends or looks at your screen asks first. The landing page runs the same router in the browser, so every line here works there too, except the ones that need a real Mac (the page says so).

## Talk and listen

- **Talk.** `./.venv/bin/python chat.py --voice`: you speak, Whisper transcribes on the Mac, she answers out loud.
- **Transcribe.** "Transcribe the video ~/Desktop/clip.mp4": the words out of any video or audio file in your home folder, same Whisper pipeline.

## See

- **Look.** "Look at my screen and tell me what's wrong with this chart", "what's in ~/Desktop/cat.png": a local vision model answers. Asks first.
- **Look through the camera.** "What am I holding", "read this label", "look at this": one frame from the Mac's own camera, the same vision model, nothing saved after the answer. Asks first; a plain sentence if there is no ffmpeg or no camera.
- **Read the screen.** "Read my screen", "find Sign in on my screen": the system's own text recognition.

## Know

- **Answer.** Questions go down a ladder: exact routes, her own picker, the project FAQ and your notes, then Wikipedia and DuckDuckGo, then her offline library (the fieldbook plus ~10,000 Wikipedia leads). If nothing holds the answer she says so.
- **Research.** "Research the history of the printing press": Wikipedia, her library and your notes, then a brief with a source after every sentence. "Save that" writes it to a file.
- **Run code.** "Stats on sales.csv", "average of the price column in sales.csv", "chart sales.csv", "plot column price of sales.csv": the biggest local model writes a short Python script from your request and the file's header, and it only ever runs in a sandbox, a fresh temp folder holding a copy of that one file, no network, a time and memory cap. A chart comes back as a real PNG. Asks first.
- **Summarize.** "Summarize ~/Desktop/report.pdf", "summarize this page", "summarize my unread mail": three to five real sentences from the biggest local model.
- **Translate.** "Translate good morning to French", "how do you say thank you in Japanese", "translate the page github.com into Spanish". Offline.
- **Ask a bigger brain.** "Ask qwen why the sky is blue", "ask claude ...": the question goes to a bigger model on your Mac, never the cloud, and the answer names the model.
- **Remember.** "Remember that my dog is called Biscuit", "what do you remember about my dog", "forget Biscuit". A file only she reads.
- **Answer inside Joshua Tree.** The from-scratch i386 kernel's own Chat app talks to her over `/api/chat`, an Ollama-compatible endpoint (`worker.js`); she answers from a condensed pack of the OS's own docs (`web/jt_docs.js`) before falling back to the general pipeline above.

## Do

- **Apps and sites.** Open an app, go to a site, search the web or one site, read a page, list, switch, read and close Chrome tabs.
- **Her hands.** "Click Sign in", "type hello", "press return", "log me into X": she reads the screen, acts one step at a time, asks before each.
- **Files.** "Find resume.docx", "what did I just download", "how big is ~/Movies", "read the document ~/notes.pdf", "find milk in the document ~/notes.pdf", then "move", "copy", "rename", "zip", "unzip", "trash" any of them. Trash is Finder's Trash, never a hard delete.
- **Write.** "Draft an email about the release", "write a doc about the roadmap": the local model drafts it, she saves it in your home folder.
- **Mail, calendar, reminders, notes.** "Unread mail", "anything from the bank in my mail", "what's on my calendar today", "remind me tomorrow at 9am to call mom", "take a note buy milk".
- **What needs me.** "What needs my attention", "what needs me": one ranked answer built from your unread mail, today's calendar and due reminders, three short lines from the biggest local model. Says plainly when everything is clear, never invents a message or a meeting.
- **Am I free.** "Am I free Thursday afternoon", "when am I free this week": your calendar's open gaps for that day or the week, business hours, not just today's list.
- **The Mac.** Volume, battery, music, timers, the weather, the clipboard, screenshots, disk space, memory, Wi-Fi, IP, uptime, system info, sleep the screen, show a file in Finder, run any Apple Shortcut by name.
- **Pictures.** "Draw a fox in the snow" (on the landing page), "paint ~/Desktop/mona.jpg" from 30,000 squares, "make me a logo for turing" (always an icon, never text), and remove a background, upscale, enhance, grayscale, rotate, flip, resize, crop, convert.
- **Math, time, chance, text.** Calculate, convert units, tips, primes and factors, roman numerals, the time in any city, dates and days between, dice, coins, random numbers, passwords, UUIDs, SHA-256, base64, word counts, morse, tidy JSON.
- **Plug in.** She speaks MCP both ways: any assistant can use her tools, and she can call another server's tools when you name it.

## Limits, plainly

Her own picker knows 77 of 105 tools by wording; the rest route through exact matches. Multi-step work borrows a small local model (qwen3:1.7b through Ollama). She never calls another MCP server on her own. She cannot reason like a frontier model and does not try; see `roadmap.md` for what is next and `LAWS.md` for what she will never do.

Windows and Linux now run the picker and chat: `training/export_gguf.py` fuses hands-adapter into the base model and quantizes it to GGUF, `Modelfile` turns that into an Ollama model (`ollama create samantha -f Modelfile`), and `serve.py`'s Ollama-compatible `/api/chat` is reachable from there with no MLX and no Mac. `tools_agent.py`'s `pick()` uses MLX when it's importable and falls back to llama-cpp-python over that same GGUF otherwise, same prompt, same stop token, same decoding. Everything that touches the Mac itself stays Mac-only regardless of backend: AppleScript (Music, Notes, Reminders, Calendar, Mail, Finder), Pixelmator, the screen (see_screen, click, type), and the camera. A phone is its own build-out, not covered here; see `roadmap.md`.
