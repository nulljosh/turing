"""Samantha as a desk robot on a Raspberry Pi (or any Linux box): the voice loop with Linux ears and mouth.

    python3 app/robot.py              # talk to her; say "goodbye" to stop
    python3 app/robot.py --text       # no microphone: type, and she answers aloud (to test without the hardware)

voice.converse already runs the loop (listen, harness, answer chain, say). This file only supplies what the Mac gives it for free:
ears = sox's `rec` (voice.record) then whisper.cpp's `whisper-cli` or the faster-whisper package; mouth = piper, else espeak-ng,
else the terminal. A write or a send is confirmed out loud ("Should I trash x? Say yes or no"), since a robot has no keyboard.
Status: written on a Mac, untested on a Pi. docs/PI.md lists what to check first."""
import os
import shutil
import subprocess
import sys
import tempfile

import voice

WHISPER_CLI = os.environ.get("SAMANTHA_WHISPER_CLI", "whisper-cli")  # whisper.cpp
WHISPER_MODEL = os.environ.get("SAMANTHA_WHISPER_MODEL", os.path.expanduser("~/models/ggml-base.en.bin"))
PIPER_MODEL = os.environ.get("SAMANTHA_PIPER_MODEL", os.path.expanduser("~/models/en_US-lessac-medium.onnx"))


def transcribe(path):
    """The words in a wav file: whisper.cpp when its binary and model are there, faster-whisper when installed, else None."""
    if shutil.which(WHISPER_CLI) and os.path.exists(WHISPER_MODEL):
        out = subprocess.run([WHISPER_CLI, "-m", WHISPER_MODEL, "-f", path, "-nt", "-np"], capture_output=True, text=True)
        return out.stdout.strip()
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return None
    segments, _ = WhisperModel("base.en", compute_type="int8").transcribe(path, language="en")
    return " ".join(s.text.strip() for s in segments).strip()


def mic():
    """One turn from the microphone, or None when the mic or a transcriber is missing (converse then says so)."""
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "turn.wav")
        return transcribe(path) if voice.record(path) else None


def speak(text):
    """Say text aloud with piper (then aplay), else espeak-ng; with neither she only prints, so the loop never crashes."""
    if shutil.which("piper") and os.path.exists(PIPER_MODEL) and shutil.which("aplay"):
        with tempfile.TemporaryDirectory() as d:
            wav = os.path.join(d, "say.wav")
            subprocess.run(["piper", "--model", PIPER_MODEL, "--output_file", wav], input=text, text=True, capture_output=True)
            subprocess.run(["aplay", "-q", wav])
    elif shutil.which("espeak-ng"):
        subprocess.run(["espeak-ng", text])


def spoken_yes(listen, say):
    """A confirm for a robot: ask out loud, take one spoken answer, only a plain yes counts."""
    def confirm(name, args):
        """Ask whether to run the tool, and return True only on a yes."""
        say(f"Should I {name.replace('_', ' ')} {' '.join(str(a) for a in args)}? Say yes or no.")
        heard = (listen() or "").lower()
        return heard.strip(" .!").split(" ")[0] in ("yes", "yeah", "yep", "sure", "ok", "okay")
    return confirm


def main():
    """Run the loop: --text types instead of listens, so everything but the hardware can be tried anywhere."""
    if "--text" in sys.argv:
        listen = lambda: input("You: ")  # noqa: E731
    else:
        listen = mic
    voice.converse(listen=listen, say=speak, confirm=spoken_yes(listen, speak))


if __name__ == "__main__":
    main()
