---
license: apache-2.0
base_model: Qwen/Qwen2.5-0.5B-Instruct
tags: [gguf, tool-calling, llama.cpp, on-device]
---

# Samantha hands (GGUF)

Samantha's tool picker from [Turing](https://github.com/nulljosh/turing) v__VERSION__: a LoRA on Qwen2.5-0.5B-Instruct, fused and quantized to Q8_0 GGUF. Given a request in plain words, she picks which of her tools to run and with what arguments. Built and trained on one Mac Mini. Live demo: [turing.heyitsmejosh.com](https://turing.heyitsmejosh.com).

## Run it

One line on Linux: `curl -fsSL https://raw.githubusercontent.com/nulljosh/turing/main/install/install.sh | sh`
Windows (PowerShell): `irm https://raw.githubusercontent.com/nulljosh/turing/main/install/install.ps1 | iex`
Both install llama-cpp-python, download this file, and start her chat. The Windows installer runs on a real Windows machine in CI on every push.

## Measured

- 395 of 484 unseen test phrasings picked right.
- On the sealed test set, 12 wrong picks still get past her guard and 11 right ones are refused. Her 5.0 goal is under 10 and none.
- This GGUF agrees with the original MLX picker on 16 of 20 fixture prompts; the misses are ambiguous wordings.

## What she does (v__VERSION__)

134 tools on your own computer: files, apps, calendar, reminders, mail, music, screen, explain a codebase, teach a topic, email a contact by name (asks first). Anything that writes, sends or clicks asks first. The tools that drive a Mac's screen and apps stay on the Mac.

## Limits

She picks tools; she does not reason, do hard math or write code like a big model. A direct Q8 conversion produced gibberish, so this file goes through f16 first, then quantizes. Trained on template phrasings and teacher-written commands, not yet on real user ratings. A bigger 1.5B picker is built and scores higher on accuracy but is not yet as safe on messy phrasings, so it is not the default.
