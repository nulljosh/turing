"""Voice in: talk to her, she listens, answers, and says it aloud. Whisper (large-v3-turbo on MLX) turns speech into
text on this Mac, sox records until you stop talking, and every turn goes through the same harness as typing, so
anything that writes still asks first (answer y or n out loud or on the keyboard). Nothing leaves the Mac.

    python3 app/chat.py --voice                  # talk; say "goodbye" or press Ctrl+C to stop
    python3 app/chat.py --voice --wake samantha  # idle until you say the wake word, then listen (off unless passed)
    python3 app/voice.py file.wav                # transcribe one recording

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


ELEVEN_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice}?output_format=mp3_44100_128"
ELEVEN_VOICE = "EXAVITQu4vr4xnSDxMaL"  # Sarah, a premade voice the free plan can use: the fallback when nothing else names one
CACHE_DIR = os.path.expanduser(os.environ.get("SAMANTHA_VOICE_CACHE", "~/.samantha/voice-cache"))  # one mp3 per line she has said


def current_voice():
    """The ElevenLabs voice id she speaks with: ELEVENLABS_VOICE when set, else the current character's
    character.json "voice_id" (set_voice writes it), else Sarah."""
    if os.environ.get("ELEVENLABS_VOICE"):
        return os.environ["ELEVENLABS_VOICE"]
    import json
    path = os.path.join(os.path.expanduser(os.environ.get("SAMANTHA_CHARACTER", "~/.samantha/characters/samantha")), "character.json")
    try:
        with open(path) as f:
            return json.load(f).get("voice_id") or ELEVEN_VOICE
    except (OSError, ValueError, AttributeError):
        return ELEVEN_VOICE


SECRETS = os.path.expanduser("~/.config/fish/secrets.fish")


def eleven_key(secrets=None):
    """The ElevenLabs key: the environment first, else the line in the fish secrets file, so the Mac app and any
    shell that never loaded fish still get her real voice instead of falling back to say. None when neither has one."""
    import re
    key = os.environ.get("ELEVENLABS_API_KEY")
    if key:
        return key
    try:
        with open(secrets or SECRETS) as f:
            m = re.search(r"^\s*set\s+-gx\s+ELEVENLABS_API_KEY\s+['\"]?([^'\"\s]+)", f.read(), re.M)
        return m.group(1) if m else None
    except OSError:
        return None


def eleven_mp3(text, key, fetch=None):
    """Her words as an ElevenLabs mp3 on disk, or None on any failure. Opt-in: only runs when ELEVENLABS_API_KEY
    is set, and it is the one path where her reply leaves the Mac (the text goes to ElevenLabs to be voiced).
    Every line is cached in CACHE_DIR by voice and text, so a line she has said before replays for free."""
    import hashlib
    import json
    import urllib.request
    voice_id = current_voice()
    cache = os.path.join(CACHE_DIR, hashlib.sha256(f"{voice_id}|eleven_flash_v2_5|{text}".encode()).hexdigest() + ".mp3")
    if os.path.isfile(cache) and os.path.getsize(cache) > 0:
        return cache  # said this exact line before: replay it, no second credit
    try:
        req = urllib.request.Request(ELEVEN_URL.format(voice=voice_id), method="POST",
                                     data=json.dumps({"text": text, "model_id": "eleven_flash_v2_5"}).encode(),
                                     headers={"xi-api-key": key, "Content-Type": "application/json", "Accept": "audio/mpeg"})
        audio = (fetch or (lambda r: urllib.request.urlopen(r, timeout=15).read()))(req)
    except Exception:
        return None
    if not audio:
        return None
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(cache, "wb") as f:
        f.write(audio)
    return cache


def speaker(text, fetch=None):
    """The command that says text aloud: ElevenLabs through afplay when a key is set and the call works,
    macOS `say` otherwise. Either way it's one killable process, so barging in works the same."""
    key = eleven_key()
    mp3 = eleven_mp3(text, key, fetch) if key else None
    return ["afplay", mp3] if mp3 else ["say", text]


MOUTH_STEP = 0.1  # seconds per talking-or-silent step of her audio


def speaking_steps(samples, rate, step=MOUTH_STEP, floor=0.12):
    """For each step of 16-bit samples, True when she is making sound (louder than floor times the loudest step)."""
    n = max(1, int(rate * step))
    levels = []
    for i in range(0, len(samples), n):
        chunk = samples[i:i + n]
        levels.append((sum(x * x for x in chunk) / len(chunk)) ** 0.5 if len(chunk) else 0.0)
    peak = max(levels, default=0.0) or 1.0
    return [level > floor * peak for level in levels]


def envelope(path, step=MOUTH_STEP):
    """speaking_steps for an audio file on disk, decoded with macOS afconvert; None when it can't be read."""
    import array
    import wave
    wav = path + ".mouth.wav"
    try:
        subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@16000", "-c", "1", path, wav], check=True, capture_output=True, timeout=20)
        with wave.open(wav) as w:
            data = array.array("h", w.readframes(w.getnframes()))
            rate = w.getframerate()
        return speaking_steps(data, rate, step)
    except Exception:
        return None
    finally:
        if os.path.exists(wav):
            os.remove(wav)


def _mouth(proc, steps, face, step=MOUTH_STEP):
    """While her audio plays, freeze the talking video in the gaps between words and run it while she speaks."""
    import time
    start = time.monotonic()
    while proc.poll() is None:
        i = int((time.monotonic() - start) / step)
        face.set_state("talk" if i >= len(steps) or steps[i] else "hold")
        time.sleep(step / 2)


def speak(text):
    """Speak text aloud with `say`; while it's talking, watch the mic in small chunks and kill `say` the moment
    a real run of loud sound shows up, so a real interruption drops straight back into listening. Returns True
    when it was cut short, False when it finished (no sox, no speech, or SAMANTHA_HEADLESS=1: nothing audible
    and the mic is never opened)."""
    import tools
    if tools.HEADLESS:
        return False
    import face
    face.set_state("talk")
    cmd = speaker(text[:500])
    proc = subprocess.Popen(cmd)
    steps = envelope(cmd[1]) if cmd[0] == "afplay" else None
    if steps:
        import threading
        threading.Thread(target=_mouth, args=(proc, steps, face), daemon=True).start()
    rec = shutil.which("rec")
    if not rec:
        proc.wait()
        face.set_state("idle")
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
        face.set_state("idle")
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
        import face
        face.set_state("listen")
        text = listen()
        face.set_state("idle")
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
