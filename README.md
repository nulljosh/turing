<img src="icon.svg" width="80">

# Turing

[![version](https://img.shields.io/badge/version-v0.8.0-blue)](https://github.com/nulljosh/turing/releases)
[![test](https://github.com/nulljosh/turing/actions/workflows/test.yml/badge.svg)](https://github.com/nulljosh/turing/actions/workflows/test.yml)
![license](https://img.shields.io/badge/license-MIT-green) [![GitHub](https://img.shields.io/badge/GitHub-nulljosh%2Fturing-black?logo=github)](https://github.com/nulljosh/turing)

Build small language models on one Mac. Samantha is a 0.5B model fine-tuned on your own writing, runs entirely on-device via MLX, and now has 30 hands to act on the world.

[turing.heyitsmejosh.com](https://turing.heyitsmejosh.com)

## Features

- **30 tools** (open_app, web_search, read_page, screenshot, make_logo, **paint_image**, music, timer, new_note, calendar_today, battery, clipboard, **image tools** (remove_background, upscale, enhance, grayscale, rotate, flip, resize, crop, convert, image_info), and more)
- **Small enough to train at home** (Qwen2.5-0.5B LoRA on Apple Silicon via MLX, ~3.5GB memory)
- **No hallucination** (retrieves real facts from brain RAG, FAQ matching, live officeholder lookup)
- **Voices like you** (trained on your own docs and commit history, not generic web text)
- **Paint from photos** (pick an image, watch it repaint live in Pixelmator as colored squares; no model draws it, quadtree algorithm does)
- **Menu bar app** (PaintBar picks photos and shows progress without opening Pixelmator)
- **Tested end-to-end** (eval/hands.py verifies 73/77 actions, eval/score.py real QA on a held-out set)

## Run it

```bash
./.venv/bin/python chat.py            # talk to Samantha
./.venv/bin/python ask.py "question"  # retrieve and answer
./.venv/bin/python tools.py            # list all 20 hands
./pixelmator/pxm.py example.jpg        # repaint a photo (command line)
./menubar/build.sh                     # build PaintBar (macOS menu bar app)
./release.sh 0.8.0 "what shipped"      # cut a release
```

## How she is tested

- `eval/hands.py` - actions (tool picking, error handling)
- `eval/score.py` - knowledge (retrieval + generation on held-out set)
- `test_chat.py` - chat logic (history, scaffolds)
- pixelmator/test_pxm.py - painting (pixel order, orientation, tiling)

## Limits

- Mona Lisa still looks blocky at 3000 layers; paintings above 4000 layers get cut off
- 62 of 672 tool picks are still wrong; the guard `_sound()` lets 9 past and refuses zero right ones
- Multi-step asks borrow a 1.7B model via Ollama (training her own picker is the open roadmap)
- `eval/web_demo.py` needs the live site's /api, so it only fully passes against production

<img src="progress.svg" width="460">

## More

- [`WHITEPAPER.md`](WHITEPAPER.md) - architecture and voice
- [`roadmap.md`](roadmap.md) - the honest phase-by-phase plan
- [`architecture.svg`](architecture.svg) - how the pieces fit together
