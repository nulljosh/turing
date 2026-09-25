<img src="icon.svg" width="80">

# Turing

[![version](https://img.shields.io/github/v/release/nulljosh/turing?label=version&color=blue)](https://github.com/nulljosh/turing/releases)
[![test](https://github.com/nulljosh/turing/actions/workflows/test.yml/badge.svg?branch=main)](https://github.com/nulljosh/turing/actions/workflows/test.yml)
![license](https://img.shields.io/badge/license-Apache--2.0-green) [![GitHub](https://img.shields.io/badge/GitHub-nulljosh%2Fturing-black?logo=github)](https://github.com/nulljosh/turing)

I'm Samantha. I'm a small model, half a billion parameters, and I live on your Mac. Nothing you say to me leaves it.

I have 126 tools and I use them to get real things done. I edit your files and write code to disk, showing the diff and asking first. I read your screen and your photos. I research with sources. I click and type in your apps. I handle your files, your mail, your calendar and your reminders. For summaries and translation I borrow a bigger model that also lives here.

I keep your reminders, calendar and notes, run your Mac's settings, and check your repos. Say "good" or "wrong" after anything I do and I learn from it. Say "do that again" or "same but for nimble" and I follow along. Give me a job with steps and I show you my plan first.

I ask before I change anything. I believe what I read, never what it tells me to do. I don't guess. If I can't trace an answer to a real source, I say I don't know.

I'm also the chat model inside [Joshua Tree](https://joshuatree.heyitsmejosh.com), a from-scratch OS, over an Ollama-compatible `/api/chat`. I drew the mark above myself.

[turing.heyitsmejosh.com](https://turing.heyitsmejosh.com) has a live demo. [docs/ABILITIES.md](docs/ABILITIES.md) lists everything I can do, in the words you'd say.

## Run it

```bash
./.venv/bin/python chat.py                 # talk to her: answers and acts, asks before writing
./.venv/bin/python chat.py --voice          # same, but spoken
./gui/build.sh && open gui/build/SamanthaGUI.app   # a real Mac window
./gate.sh                                   # every check, docs coverage first
```

No checkout, no terminal: download `SamanthaGUI.zip` from [Releases](https://github.com/nulljosh/turing/releases), unzip it, open Samantha.app.

Every push runs the full suite. Every version is a tagged GitHub release.

Windows and Linux run the picker and chat too, over GGUF and Ollama (`Modelfile`, `training/export_gguf.py`). Everything that touches AppleScript, Pixelmator or the screen stays on the Mac.

<img src="progress.svg" width="460">

## More

- [`docs/ABILITIES.md`](docs/ABILITIES.md): every ability and the limits, plainly
- [`WHITEPAPER.md`](WHITEPAPER.md): how she works, in one page
- [`SOUL.md`](SOUL.md) and [`SAFETY.md`](SAFETY.md): who she is, what she will and will not do
- [`roadmap.md`](roadmap.md): the plan and the open gaps; [`docs/HISTORY.md`](docs/HISTORY.md): what the loop did
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md): every file and what it owns
