# Samantha on a Raspberry Pi (the desk robot)

Status: planned, untested. The Pi is not here yet; nothing below has run on one.

## The idea

A small desk robot you talk to. A Pi 5 (8 GB) with a microphone and a speaker runs her on its own: no account, no cloud. She hears a sentence, picks a tool or answers from her notes, and says the result out loud.

## What should already work

- The 0.5B GGUF picker over llama.cpp is the Windows and Linux path (`install/install.sh`). A Pi runs Linux on ARM64, so the same install should apply. The prebuilt wheel index it uses is x86-first, so on a Pi `llama-cpp-python` will most likely build from source (needs `cmake` and a compiler, and takes a while).
- The 1.5B MLX picker is Mac only. On the Pi she uses the 0.5B GGUF, which is the weaker picker (see docs/PROGRESS.md), so the first goal is chat and a few safe tools, not all 135.

## What has to be built

1. Run `install/install.sh` on a real Pi 5 and write down what breaks.
2. A voice loop: speech to text (whisper.cpp small), her answer, text to speech (piper), with a push-to-talk or wake word. The Mac app already has a voice mode; this is the Linux version.
3. A safe tool list for a robot that lives on a desk: time, timers, weather, notes, reminders, math, her own FAQ. Nothing that writes files or sends mail without a spoken yes.
4. Optional later: servos for a head that turns toward the voice, and the camera for her face mode.

## First test when the Pi arrives

`./install/install.sh`, then `./samantha`, then ask "what time is it" and "what is Joshua Tree". If both work, the voice loop is next.
