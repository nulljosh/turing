---
license: apache-2.0
base_model: Qwen/Qwen2.5-0.5B-Instruct
tags: [gguf, tool-calling, llama.cpp, on-device]
---

# Samantha hands (GGUF)

This is the portable 0.5B picker for Windows and Linux. The 1.5B picker that Mac users get in Turing 5.0 is at [trommatic/samantha-hands-1.5b-mlx](https://huggingface.co/trommatic/samantha-hands-1.5b-mlx).

Samantha's tool picker from [Turing](https://github.com/nulljosh/turing) v__VERSION__: a LoRA on Qwen2.5-0.5B-Instruct, fused and quantized to Q8_0 GGUF. Given a request in plain words, she picks which of her tools to run and with what arguments. Built and trained on one Mac Mini. Live demo: [turing.heyitsmejosh.com](https://turing.heyitsmejosh.com).

## Run it

One line on Linux: `curl -fsSL https://raw.githubusercontent.com/nulljosh/turing/main/install/install.sh | sh`
Windows (PowerShell): `irm https://raw.githubusercontent.com/nulljosh/turing/main/install/install.ps1 | iex`
Both install llama-cpp-python, download this file, and start her chat. The Windows installer runs on a real Windows machine in CI on every push.

## Measured

- 395 of 484 unseen test phrasings picked right.
- On 869 sealed sentences she never trained on (two sets nobody tuned to), version 5.11 picks the right tool for 802 (5.6: 801, 5.1: 788) and the wrong tool for 45 (39, 53); 20 wrong picks get past her guard (19, 19) and 39 right picks are refused (40, 45). On 360 fresh messy phrasings, 325 right (5.6: 323). She now knows the Joshua Tree family by wording (86 of 93 test phrasings). About 5 percent of right commands are still left undone against a goal of under 2. (Training run 20; 5.6 was run 19, 5.1 run 13.) Older line kept for the record: 619 sealed sentences, 5.1 picked 351 right and 79 wrong, 5.0 317 and 126; 27 past the guard, and 11 of 273 right commands (4.0 percent) are left undone. On messier test sentences (typos, voice dictation) about 8 percent are left undone. The goal is under 2 percent, and that is the next work.
- This GGUF agrees with the original MLX picker on 16 of 20 fixture prompts; the misses are ambiguous wordings.

## What she does (v__VERSION__)

She also runs as an app on Joshua Tree on a Raspberry Pi, and can write code to its card. She remembers what you tell her, can keep it in your own iCloud Drive, and writes Shortcuts you add yourself.

159 tools on your own computer: files, apps, calendar, reminders, mail, music, screen, explain a codebase, teach a topic, email a contact by name (asks first). Anything that writes, sends or clicks asks first. The tools that drive a Mac's screen and apps stay on the Mac.

## Limits

She picks tools; she does not reason, do hard math or write code like a big model. A direct Q8 conversion produced gibberish, so this file goes through f16 first, then quantizes. Trained on template phrasings and teacher-written commands, not yet on real user ratings. A bigger 1.5B picker is built and scores higher on accuracy but is not yet as safe on messy phrasings, so it is not the default.
