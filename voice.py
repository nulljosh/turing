"""Voice in: talk to her, she listens, answers, and says it aloud. Whisper (large-v3-turbo on MLX) turns speech into
text on this Mac, sox records until you stop talking, and every turn goes through the same harness as typing, so
anything that writes still asks first (answer y or n out loud or on the keyboard). Nothing leaves the Mac.

    python3 chat.py --voice       # talk; say "goodbye" or press Ctrl+C to stop
    python3 voice.py file.wav     # transcribe one recording

The first run downloads the Whisper weights (about 1.6GB) and macOS asks once for microphone access.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

MODEL = os.environ.get("SAMANTHA_WHISPER", "mlx-community/whisper-large-v3-turbo")
MAX_SECONDS = 30  # one turn never records longer than this
STOP = re.compile(r"^(?:goodbye|good bye|bye|stop listening|that's all|exit|quit)\W*$", re.I)
# what Whisper writes when it hears silence or breath: a turn made only of these heard nothing
PHANTOMS = re.compile(r"^(?:thank you\W*|thanks for watching\W*|you\W*|\W*|\[[^\]]*\]|\([^)]*\)|\.+)$", re.I)


def record(path, seconds=MAX_SECONDS):
    """Record from the default microphone into path until 1.5 seconds of quiet, at most `seconds`. False without sox."""
    rec = shutil.which("rec")
    if not rec:
        return False
    # start on the first sound above 1%, stop after 1.5s below it
    subprocess.run([rec, "-q", "-c", "1", "-r", "16000", path, "silence", "1", "0.1", "1%", "1", "1.5", "1%",
                    "trim", "0", str(seconds)], timeout=seconds + 15, check=False)
    return os.path.exists(path) and os.path.getsize(path) > 1000


def transcribe(path):
    """What was said in a recording, as text; "" when it was silence or Whisper only heard its usual phantoms."""
    import mlx_whisper
    got = mlx_whisper.transcribe(path, path_or_hf_repo=MODEL, language="en", condition_on_previous_text=False)
    text = " ".join(s["text"].strip() for s in got.get("segments", []) if s.get("no_speech_prob", 0) < 0.6).strip()
    return "" if PHANTOMS.match(text) else text


def heard(text):
    """What to do with a transcript: ("stop", None), ("nothing", None) or ("ask", the question)."""
    text = text.strip()
    if not text or PHANTOMS.match(text):
        return "nothing", None
    if STOP.match(text):
        return "stop", None
    return "ask", text


def converse(listen=None, say=None, show=print, turns=None):
    """The voice loop: listen, show what was heard, answer through the harness and the answer chain, say it aloud.
    listen() returns one transcript; say(text) speaks; turns caps the loop (tests). Returns how many questions it answered."""
    import chat
    import harness
    import tools

    def mic():
        """One turn from the microphone."""
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "turn.wav")
            if not record(path):
                return None
            return transcribe(path)

    listen = listen or mic
    say = say or tools.say
    session = harness.Session(confirm=harness._ask_yes, log=show)
    history, topic, subject, answered = [], False, None, 0
    show("Listening. Say \"goodbye\" to stop.")
    while turns is None or turns > 0:
        if turns is not None:
            turns -= 1
        text = listen()
        if text is None:
            show("I can't hear the microphone: install sox (brew install sox) and allow microphone access for this terminal.")
            return answered
        what, question = heard(text)
        if what == "stop":
            say("Bye.")
            return answered
        if what == "nothing":
            continue
        show(f"You: {question}")
        reply = session.ask(question, or_none=True)
        if reply is None:
            reply, topic, subject = chat.safe_turn(question, history, topic, subject)
        history.append((question, reply))
        show(f"Samantha: {reply}")
        say(reply)
        answered += 1
    return answered


if __name__ == "__main__":
    if len(sys.argv) > 1:
        print(transcribe(sys.argv[1]) or "(heard nothing)")
    else:
        converse()
