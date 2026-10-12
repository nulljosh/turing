# Samantha on a Raspberry Pi (the desk robot)

Status: the Pi is here and runs Joshua Tree, and Samantha is an app on it (Joshua Tree 2.47.0 asks this repo's serve.py through its TLS relay). That is the 6.0 path. Everything below is the older plan for plain Linux on a Pi, optional and untested.

## The idea

A small desk robot you talk to. A Pi 5 (8 GB) with a microphone and a speaker runs her on its own: no account, no cloud. She hears a sentence, picks a tool or answers from her notes, and says the result out loud.

## What should already work

- The 0.5B GGUF picker over llama.cpp is the Windows and Linux path (`install/install.sh`). A Pi runs Linux on ARM64, so the same install should apply. The prebuilt wheel index it uses is x86-first, so on a Pi `llama-cpp-python` will most likely build from source (needs `cmake` and a compiler, and takes a while).
- The 1.5B MLX picker is Mac only. On the Pi she uses the 0.5B GGUF, which is the weaker picker (see docs/PROGRESS.md), so the first goal is chat and a few safe tools, not all 135.

## What is built (untested on a Pi)

`app/robot.py` is the voice loop for Linux: sox records, whisper.cpp (or faster-whisper) hears, piper (or espeak-ng) speaks, and anything that writes is confirmed out loud. `python3 app/robot.py --text` types instead of listens, so everything but the hardware can be tried anywhere, and it runs on the Mac today. The models it expects: `~/models/ggml-base.en.bin` (whisper.cpp) and `~/models/en_US-lessac-medium.onnx` (piper), or the `SAMANTHA_WHISPER_MODEL` and `SAMANTHA_PIPER_MODEL` paths.

## What has to be built

1. Run `install/install.sh` on a real Pi 5 and write down what breaks.
2. Try the voice loop on the real mic and speaker (`app/robot.py`, written, never run on a Pi), then add a wake word.
3. A safe tool list for a robot that lives on a desk: time, timers, weather, notes, reminders, math, her own FAQ. Nothing that writes files or sends mail without a spoken yes.
4. Optional later: servos for a head that turns toward the voice, and the camera for her face mode.

## First test when the Pi arrives

`./install/install.sh`, then `./samantha`, then ask "what time is it" and "what is Joshua Tree". If both work, the voice loop is next.

## Next: the shell is a shell, she is a command

Joshua's call (2026-10-11, after trying her at the Pi's terminal): the console should boot to a real shell, zsh or bash, not to Samantha. Samantha becomes a command you run from that shell (a CLI, `samantha "what is ten plus ten"` or an interactive `samantha`), and she is also an app with her own window. Today the `Samantha $` prompt is the default console on Joshua Tree; this flips it. Lives in the Joshua Tree repo (arch/arm64 console and shell), on a branch with a PR.
