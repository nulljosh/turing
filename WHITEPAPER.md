# Turing Technical Whitepaper

**v0.8.0** | September 2026

Turing is a pipeline for building small language models on consumer hardware. Its first model, Samantha, is a LoRA fine-tune of a small open base, trained on this project's own notes and documentation, and now equipped with 20 hands (tools) to take real actions on the Mac: open apps, read web pages, paint images, make notes, and more.

## The core mechanic

Start from an already-trained small open model (Qwen2.5-0.5B-Instruct), which already knows grammar and reasoning. Apply LoRA (Low-Rank Adaptation), a small set of trainable weight deltas layered on top, trained on your own voice and knowledge. No relearning language, just adjusting it.

All training runs on-device via Apple's MLX framework, no cloud GPU, no API cost. A run is invoked by hand, not scheduled.

## What's working now

Samantha answers questions by retrieving real facts from `brain` RAG and generating answers from them, not from memorized weights. A regex router handles simple commands (open chrome, set volume, take screenshot) with zero model inference. Multi-step asks (poke around a website, tell me the top 3 stories) go to a 1.7B model via Ollama for tool picking.

**Painting hands:** `paint_image` repaints photos as colored squares using a quadtree algorithm (split the most-wrong region into four, repeat). No model draws the picture. The harness does the layout in Pixelmator Pro via `pxm.py`. PaintBar, a one-file SwiftUI menu bar app, picks a photo and shows live progress without opening Pixelmator.

**Picker guard:** Her own 0.5B tool picker (round three, trained on 501 examples with painting) picks the right tool 394/501 times on unseen wording. The guard `_sound()` lets 9 wrong picks past (down from 21) and refuses zero right ones.

## Limits, stated plainly

The Mona Lisa at 3000 layers still looks blocky. Paintings above 4000 layers get cut off. 62 of 672 picks are still wrong; multi-step asks borrow a 1.7B model because training her own is the next roadmap item.

---
MIT License, 2026 Joshua Trommel.
