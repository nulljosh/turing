"""Voice in: talk to her, she listens, answers, and says it aloud. Whisper (large-v3-turbo on MLX) turns speech into
text on this Mac, sox records until you stop talking, and every turn goes through the same harness as typing, so
anything that writes still asks first (answer y or n out loud or on the keyboard). Nothing leaves the Mac.

    python3 chat.py --voice                  # talk; say "goodbye" or press Ctrl+C to stop
    python3 chat.py --voice --wake samantha  # idle until you say the wake word, then listen (off unless passed)
    python3 voice.py file.wav                # transcribe one recording

While she's speaking, a real run of loud sound on the mic (not one click) kills `say` and drops straight back
into listening, same as talking over a person. No new model, just an energy check on the raw mic stream.

The first run downloads the Whisper weights (about 1.6GB) and macOS asks once for microphone access.
"""
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile

MODEL = os.environ.get("SAMANTHA_WHISPER", "mlx-community/whisper-large-v3-turbo")
MAX_SECONDS = 30  # one turn never records longer than this
WAKE_SECONDS = 8  # idle chunks while waiting for a wake word are short: it's just a name plus one command
WAKE_WORD = "samantha"  # --wake with no word after it means this one
STOP = re.compile(r"^(?:goodbye|good bye|bye|stop listening|that's all|exit|quit)\W*$", re.I)
# what Whisper writes when it hears silence or breath: a turn made only of these heard nothing
PHANTOMS = re.compile(r"^(?:thank you\W*|thanks for watching\W*|you\W*|\W*|\[[^\]]*\]|\([^)]*\)|\.+)$", re.I)

BARGE_THRESHOLD = 1500  # RMS of a 16-bit PCM chunk; normal room noise sits well under this, real speech clears it
BARGE_RUN = 2  # consecutive loud chunks needed to count as someone talking, not one click or a door
BARGE_CHUNK_SECONDS = 0.25


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


def wake_match(text, word=WAKE_WORD):
    """(True, the rest) when a transcript starts with the wake word (any case, an optional comma after it,
    "sam" or any other prefix never matches, the word must stand whole); (False, None) otherwise."""
    m = re.match(rf"^{re.escape(word)}\b[,]?\s*", text.strip(), re.I)
    return (True, text.strip()[m.end():].strip()) if m else (False, None)


def _chunk_energy(chunk):
    """RMS of a chunk of raw 16-bit little-endian PCM bytes, as a plain int; 0 for empty or silent input."""
    n = len(chunk) // 2
    if n == 0:
        return 0
    samples = struct.unpack(f"<{n}h", chunk[:n * 2])
    return int((sum(s * s for s in samples) / n) ** 0.5)


def should_barge_in(levels, threshold=BARGE_THRESHOLD, run=BARGE_RUN):
    """True once `levels` (energy per mic chunk, oldest first) holds a real run of `run` consecutive chunks
    over `threshold`: someone talking, not one loud click or a single spike in the room noise."""
    streak = 0
    for level in levels:
        streak = streak + 1 if level > threshold else 0
        if streak >= run:
            return True
    return False


def speak(text):
    """Speak text aloud with `say`; while it's talking, watch the mic in small chunks and kill `say` the moment
    a real run of loud sound shows up, so a real interruption drops straight back into listening. Returns True
    when it was cut short, False when it finished (no sox, no speech, or SAMANTHA_HEADLESS=1: nothing audible
    and the mic is never opened)."""
    import tools
    if tools.HEADLESS:
        return False
    proc = subprocess.Popen(["say", text[:500]])
    rec = shutil.which("rec")
    if not rec:
        proc.wait()
        return False
    mic = subprocess.Popen([rec, "-q", "-t", "raw", "-r", "16000", "-e", "signed", "-b", "16", "-c", "1", "-"],
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    chunk_bytes = int(16000 * 2 * BARGE_CHUNK_SECONDS)
    levels, barged = [], False
    try:
        while proc.poll() is None:
            chunk = mic.stdout.read(chunk_bytes)
            if not chunk:
                break
            levels.append(_chunk_energy(chunk))
            if should_barge_in(levels[-BARGE_RUN:]):
                proc.kill()
                barged = True
                break
    finally:
        mic.kill()
        proc.wait()
    return barged


def converse(listen=None, say=None, show=print, turns=None, wake=None):
    """The voice loop: listen, show what was heard, answer through the harness and the answer chain, say it aloud.
    listen() returns one transcript; say(text) speaks; turns caps the loop (tests). wake, off by default, holds
    a wake word: every transcript that doesn't start with it is ignored instead of answered, same idle-until-named
    behavior as Alexa or "hey Siri", just Whisper doing the listening instead of a wake model. Returns how many
    questions it answered."""
    import chat
    import harness
    import tools

    def mic():
        """One turn from the microphone: a short chunk while idle for a wake word, the full window otherwise."""
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "turn.wav")
            if not record(path, seconds=WAKE_SECONDS if wake else MAX_SECONDS):
                return None
            return transcribe(path)

    listen = listen or mic
    say = say or speak
    session = harness.Session(confirm=harness._ask_yes, log=show)
    history, topic, subject, answered = [], False, None, 0
    show(f'Listening for "{wake}".' if wake else 'Listening. Say "goodbye" to stop.')
    while turns is None or turns > 0:
        if turns is not None:
            turns -= 1
        text = listen()
        if text is None:
            show("I can't hear the microphone: install sox (brew install sox) and allow microphone access for this terminal.")
            return answered
        if wake:
            matched, rest = wake_match(text, wake)
            if not matched:
                continue
            text = rest
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
