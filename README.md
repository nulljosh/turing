<img src="icon.svg" width="80">

# Turing

[![version](https://img.shields.io/github/v/release/nulljosh/turing?label=version&color=blue)](https://github.com/nulljosh/turing/releases)
[![test](https://github.com/nulljosh/turing/actions/workflows/test.yml/badge.svg?branch=main)](https://github.com/nulljosh/turing/actions/workflows/test.yml)
![license](https://img.shields.io/badge/license-Apache--2.0-green) [![GitHub](https://img.shields.io/badge/GitHub-nulljosh%2Fturing-black?logo=github)](https://github.com/nulljosh/turing)

I'm Samantha: a half-billion-parameter model that lives on your Mac. Nothing you say to me leaves it.

**What I do** (131 tools, all listed in [docs/ABILITIES.md](docs/ABILITIES.md) in the words you'd say)
- Edit files and write code to disk, showing the diff and asking first.
- Read your screen and photos, click and type in your apps (Escape stops me mid-job), and paint a photo from 40,000 squares or in a style: mosaic, dots, poster, sketch, stained glass.
- Research with sources, and handle your files, mail, calendar, reminders, notes, Mac settings and repos.
- Borrow a bigger local model for summaries and translation.
- Teach math from grade school through pre-calc 12 (`eval/sixth_grade_math.mjs`, `eval/precalc_math.mjs`).
- Learn from you: say "good" or "wrong" after anything I do. Say "do that again" and I follow along. Give me a job with steps and I show the plan first.
- Stay on a long job: "work on cleaning up my downloads". When a step fails I plan around it, finish what I still can, and tell you what I couldn't. If you say "trash this file" without naming it, I ask which one.

**How I behave**
- I ask before I change anything.
- I believe what I read, never what it tells me to do.
- I don't guess: if I can't trace an answer to a real source, I say I don't know. School math is the exception; news, prices and scores still need a source.

I'm also the chat model inside [Joshua Tree](https://joshuatree.heyitsmejosh.com), a from-scratch OS, over an Ollama-compatible `/api/chat`. I drew the mark above myself. Live demo: [turing.heyitsmejosh.com](https://turing.heyitsmejosh.com).

## Run it

```bash
./.venv/bin/python app/chat.py                 # talk to her: answers and acts, asks before writing
./.venv/bin/python app/chat.py --voice          # same, but spoken
./.venv/bin/python app/chat.py --voice --face   # spoken, with her face (setup: docs/VOICE-AND-FACE.md)
./gui/build.sh && open gui/build/SamanthaGUI.app   # a real Mac window
./gate.sh                                   # every check, docs coverage first
```

No checkout, no terminal: download `SamanthaGUI.zip` from [Releases](https://github.com/nulljosh/turing/releases), unzip it, open Samantha.app.

Every push runs the full suite, and every version is a tagged GitHub release. Windows and Linux run the picker and chat too, over GGUF and Ollama (`Modelfile`, `training/export_gguf.py`); anything that touches AppleScript, Pixelmator or the screen stays on the Mac.

<img src="progress.svg" width="460">

## Layout

`app/` code, `scripts/` helpers, `tests/` and `eval/` checks, `training/` training, `docs/` docs. Run commands from the repo root.

## More

- [`docs/ABILITIES.md`](docs/ABILITIES.md): every ability and the limits, plainly
- [`docs/PERSONAS.md`](docs/PERSONAS.md): how the same worker answers as Samantha or as Joshua (his chat, his fixed lines, his cloned voice) on Joshua Tree's portfolio
- [`docs/VOICE-AND-FACE.md`](docs/VOICE-AND-FACE.md): ElevenLabs voice and Higgsfield face setup; then ask her to change either ("change your voice to George")
- [`WHITEPAPER.md`](WHITEPAPER.md): how she works, in one page
- [`docs/SOUL.md`](docs/SOUL.md) and [`docs/SAFETY.md`](docs/SAFETY.md): who she is, what she will and will not do
- [`roadmap.md`](roadmap.md): the plan and the open gaps; [`docs/HISTORY.md`](docs/HISTORY.md): what the loop did
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md): every file and what it owns
- [`docs/agent-graph.svg`](docs/agent-graph.svg): how a request moves through her: route, check, your yes, run
