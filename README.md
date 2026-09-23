<img src="icon.svg" width="80">

# Turing

[![version](https://img.shields.io/github/v/release/nulljosh/turing?label=version&color=blue)](https://github.com/nulljosh/turing/releases)
[![test](https://github.com/nulljosh/turing/actions/workflows/test.yml/badge.svg?branch=main)](https://github.com/nulljosh/turing/actions/workflows/test.yml)
![license](https://img.shields.io/badge/license-Apache--2.0-green) [![GitHub](https://img.shields.io/badge/GitHub-nulljosh%2Fturing-black?logo=github)](https://github.com/nulljosh/turing)

A small model, Samantha, that runs entirely on your Mac and gets real work done. 91 tools, 0.5B parameters, nothing leaves the machine.

[turing.heyitsmejosh.com](https://turing.heyitsmejosh.com)

## What she does

- **Talks.** `chat.py --voice`: you speak, Whisper transcribes, she answers out loud.
- **Transcribes video and audio.** "Transcribe the video ~/Desktop/clip.mp4" pulls the words out with the same Whisper pipeline, any file in your home folder.
- **Sees.** Look at your screen or a photo and ask about it; a local vision model answers.
- **Researches.** "Research X" reads Wikipedia, her library and your notes, writes a brief that cites every claim, and saves it if you ask.
- **Uses your apps.** "Click Sign in", "type hello", "log me into X": she reads the screen and acts, step by step, asking first.
- **Asks a bigger brain when stuck.** "Ask qwen ...", "ask claude ..." hands hard questions to another local model, never the cloud.
- **Knows things offline.** Her library holds the fieldbook plus ~10,000 Wikipedia articles; she answers only from a real page and says which one.
- **Summarizes.** "Summarize ~/Desktop/report.pdf", "summarize this page", "summarize my unread mail": three to five real sentences from the biggest local model, not a one-liner.
- **Does the rest of the Mac.** Apps, tabs, notes, reminders, calendar, unread mail, files, documents, math, time zones, dice, hashes, Shortcuts, memory across sessions.
- **Draws.** Type "draw a fox in the snow" on the landing page and she rebuilds it live from 30,000 squares.
- **Writes files.** "Draft an email about X", "write a doc about X": the local model drafts it, she saves it to your home folder, asking first.
- **Never guesses.** Every answer traces to a real source; unsupported claims are dropped, not printed.

## Run it

```bash
./.venv/bin/python chat.py                 # talk to her: answers and acts, asks before writing
./.venv/bin/python chat.py --voice          # same, but spoken
./.venv/bin/python ask.py "question"        # one-shot retrieve and answer
./gui/build.sh && open gui/build/SamanthaGUI.app   # a real Mac window instead of the terminal
python3 mcp_server.py                       # her tools over MCP
./gate.sh                                   # every check, docs coverage first
./release.sh 0.12.0 "what shipped"          # cut a release
```

## Tested

Every push runs the full suite: the router and its JavaScript twin agree word for word, the harness asks before every write, her knowledge is scored against a held-out set, and every function is documented (CI fails under 100%). `./gate.sh` runs it all locally first.

## Limits

Her own picker knows a subset of tools; the rest route through exact regex matches, not a model. Multi-step work borrows a small local model (qwen3:1.7b via Ollama). The 10 tools that read this Mac (disk, memory, Wi-Fi...) only work on a Mac; the landing page says so. She never calls another MCP server on her own, only when you name it.

<img src="progress.svg" width="460">

## More

- [`WHITEPAPER.md`](WHITEPAPER.md): architecture and voice
- [`SOUL.md`](SOUL.md): who she is and what she optimizes for
- [`SAFETY.md`](SAFETY.md): what she will and will not do, and how that is enforced
- [`roadmap.md`](roadmap.md): the honest phase-by-phase plan
- [`architecture.svg`](architecture.svg): how the pieces fit together
