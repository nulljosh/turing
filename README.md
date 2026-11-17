<img src="web/logo.svg" width="96" alt="Samantha's logo: round glasses on a terracotta circle">

# Samantha

A small AI that lives on your Mac and does things for you. Free, private, asks first. Try her at [turing.jaybulb.com](https://turing.jaybulb.com).

She handles your files, mail, calendar and settings, reads your screen and clicks for you, edits code, researches with sources, and makes images, logos and videos. Anything that writes, sends or deletes asks first, and Escape stops her.

## Get it

Mac: download `SamanthaGUI.zip` from [Releases](https://github.com/nulljosh/turing/releases) and open Samantha.app.

```bash
curl -fsSL https://raw.githubusercontent.com/nulljosh/turing/main/install/install.sh | sh   # Linux
irm https://raw.githubusercontent.com/nulljosh/turing/main/install/install.ps1 | iex        # Windows
```

From source: `./.venv/bin/python app/chat.py` (add `--voice` to talk), and `./gate.sh` runs every check.

## How she works

A small model picks the tool and a router does the rest, all on your machine. Weights: [the 1.5B picker (MLX)](https://huggingface.co/trommatic/samantha-hands-1.5b-mlx) and [the GGUF for Windows and Linux](https://huggingface.co/trommatic/samantha-hands-gguf).

## Docs

- [ARCHITECTURE](docs/ARCHITECTURE.md): every file, every ability, her voice and face
- [TRAINING](docs/TRAINING.md): how she's trained and the results
- [SAFETY](docs/SAFETY.md): the laws she never breaks
- [FAQ](docs/FAQ.md), [roadmap](docs/roadmap.md), [progress](docs/PROGRESS.md)

Apache 2.0.
