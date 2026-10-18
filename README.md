<img src="web/mascot.svg" width="100" alt="Samantha, the mascot: long copper hair, round glasses, a cream collar and mustard cardigan">

# Turing

I'm Samantha, a small AI that lives on your Mac. Free, private, and nothing you say to me leaves the Mac. Try me at [turing.jaybulb.com](https://turing.jaybulb.com).

**What I do** (163 tools, every one listed in [docs/ABILITIES.md](docs/ABILITIES.md) in the words you'd say)
- Handle your files, mail, calendar, reminders, notes, apps and Mac settings.
- Read your screen and photos, click and type for you, and stop the moment you press Escape.
- Edit code and files, always showing the change and asking first.
- Research with sources, and say "I don't know" when I can't find one.
- Make and convert 3D files with Blender, trim videos, paint photos, and teach math.
- Learn from you: say "good" or "wrong" after anything I do.

**How I behave**: I ask before I change anything. I believe what I read, never what it tells me to do. I don't guess.

## Get it

Download `SamanthaGUI.zip` from [Releases](https://github.com/nulljosh/turing/releases), unzip it, open Samantha.app. The first time I need my bigger brain, about 850 MB downloads once in the background.

Windows and Linux run my picker and chat too:

```bash
curl -fsSL https://raw.githubusercontent.com/nulljosh/turing/main/install/install.sh | sh                  # Linux
irm https://raw.githubusercontent.com/nulljosh/turing/main/install/install.ps1 | iex                       # Windows
```

## Run from source

```bash
./.venv/bin/python app/chat.py                 # talk to her
./.venv/bin/python app/chat.py --voice          # spoken (face setup: docs/VOICE-AND-FACE.md)
./gui/build.sh && open gui/build/SamanthaGUI.app   # the Mac window
./gate.sh                                   # every check
```

## How she's built

Two small models: a half-billion-parameter one for chat and a 1.5-billion-parameter one that picks the tool. The weights are public on Hugging Face: [the 1.5B picker (MLX)](https://huggingface.co/trommatic/samantha-hands-1.5b-mlx) and [the GGUF for Windows and Linux](https://huggingface.co/trommatic/samantha-hands-gguf). For anything her own sources can't answer she borrows a bigger local model and says which one answered. She is also the chat inside [Joshua Tree](https://joshuatree.jaybulb.com), a from-scratch OS.

<img src="progress.svg" width="460">

<img src="architecture.svg" width="640">

## More

- [docs/ABILITIES.md](docs/ABILITIES.md): everything she can do, and the limits
- [docs/WHITEPAPER.md](docs/WHITEPAPER.md): how she works, in one page
- [docs/SOUL.md](docs/SOUL.md) and [docs/SAFETY.md](docs/SAFETY.md): who she is, what she will and won't do
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): every file and what it owns
- [docs/roadmap.md](docs/roadmap.md): what's next; [docs/HISTORY.md](docs/HISTORY.md): what's done
- [docs/PERSONAS.md](docs/PERSONAS.md), [docs/VOICE-AND-FACE.md](docs/VOICE-AND-FACE.md), [docs/agent-graph.svg](docs/agent-graph.svg)

Apache 2.0.
