#!/usr/bin/env python3
"""Rebuild the landing page's commercial (web/promo.mp4, promo.vtt, promo-poster.jpg) from the live demo.

It records the deployed page headlessly while typed prompts run through every family of what she can do, voices each segment
with her own ElevenLabs voice (cached by app/voice.py, so a rerun costs nothing), puts each line at the moment its segment
starts, writes captions from the same timestamps and muxes the lot with ffmpeg.

Run: ./.venv/bin/python scripts/make_promo.py [url=https://turing.heyitsmejosh.com]
Needs ELEVENLABS_API_KEY (environment or the fish secrets file), ffmpeg and playwright's Chromium. Nothing is written to web/ until the whole build worked."""
import glob
import json
import math
import os
import shutil
import subprocess
import sys
import struct
import tempfile
import time
import wave

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "app"))
import voice  # noqa: E402

URL = next((a for a in sys.argv[1:] if a.startswith("http")), "https://turing.heyitsmejosh.com")
W, H = 1280, 720
VW, VH = W, H  # the page is laid out at the recorded size: a smaller window squashes the painting
# (what she says over it, [what is typed into the demo while she says it]); each segment lasts at least as long as its line
# Five beats, about 45 seconds. The last two put a plain card over the demo: what only a real Mac can do (said as Mac-only, never faked),
# then her name, what she is, where to get her and how.
SEGMENTS = [
    ("Meet Samantha. She paints from thirty thousand squares.", ["paint the mona lisa"]),
    ("She runs your Mac.", ["set the volume to 40", "remind me to call mom tomorrow at 9"]),
    ("She does the math.", ["what is 17*23", "convert 72 f to c"]),
    ("On a real Mac, she researches, reads your screen, and clicks for you.", []),
    ("Samantha. Free, and private. Download her for Mac.", []),
]
# the least each beat stays on screen, in seconds: long enough for the painting to build, for a card to be read, for the end card to land
HOLD = [6.5, 7.0, 4.8, 5.2, 6.5]
# (text, size px, color) lines for the card over a segment, by segment index
CARDS = {
    3: [("research the history of the printing press", 34, "#151515"), ("what's on my screen", 34, "#151515"), ("click Sign in", 34, "#151515"), ("On a real Mac. She always asks first.", 22, "#666")],
    4: [("MARK", 0, ""), ("Samantha", 64, "#151515"), ("A small AI that lives on your Mac.", 28, "#151515"), ("Free  \u00b7  Private  \u00b7  Runs on your Mac", 22, "#666"),
        ("turing.heyitsmejosh.com", 34, "#151515"), ("Download the Mac app  \u00b7  Windows, Linux and phones install too", 22, "#666"),
        ("Open source  \u00b7  github.com/nulljosh/turing", 20, "#666")],
}


def clock(t):
    """Seconds as a WebVTT timestamp, mm:ss.mmm."""
    return f"{int(t // 60):02d}:{t % 60:06.3f}"


def duration(path):
    """Length of an audio file in seconds, from ffprobe."""
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path], capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def narrate(key):
    """One mp3 per segment, in her voice. Exits with a plain message when the key or the voice call is missing."""
    clips = []
    for text, _ in SEGMENTS:
        mp3 = voice.eleven_mp3(text, key)
        if not mp3:
            sys.exit("ElevenLabs did not return audio for: " + text)
        clips.append((mp3, duration(mp3)))
    return clips


def record(clips, out_dir):
    """Drive the live demo through every segment and return (video path, [segment start seconds]) with the video clock."""
    from playwright.sync_api import sync_playwright
    starts = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        t0 = time.time()
        ctx = browser.new_context(viewport={"width": VW, "height": VH}, record_video_dir=out_dir, record_video_size={"width": W, "height": H}, color_scheme="light")
        page = ctx.new_page()
        # the painting is a fixed batch per animation frame and finishes in under a second, too fast to read on video:
        # while window.__slow is set, every animation frame waits 80 ms, so the 30,000 squares arrive over a few seconds
        page.add_init_script("(() => { const raf = window.requestAnimationFrame.bind(window); window.requestAnimationFrame = cb => window.__slow ? raf(() => setTimeout(() => raf(cb), 80)) : raf(cb); })()")
        page.goto(URL)
        # bigger type for a 1280 wide video; the layout and the painting are left alone
        page.add_style_tag(content="#chat-transcript{font-size:19px!important;line-height:1.5!important}#chat-input{font-size:20px!important}.chat-tool-call{font-size:15px!important}.desk-bar{font-size:15px!important}#chat-send{font-size:18px!important}.hero .sub{font-size:20px!important}")
        page.wait_for_selector("#chat-input")
        page.wait_for_timeout(900)  # the page's idle reel starts on its own at 500 ms and is mid-sentence by now
        page.focus("#chat-input")
        page.keyboard.press("Shift")  # any key stops the reel for good; then wipe what it had typed
        page.fill("#chat-input", "")
        page.wait_for_timeout(400)
        for idx, ((mp3, seconds), (line, prompts)) in enumerate(zip(clips, SEGMENTS)):
            seg_start = time.time()
            page.evaluate("window.__slow = " + ("true" if idx == 0 else "false"))
            starts.append(seg_start - t0)
            for prompt in prompts:
                seen = page.evaluate("document.querySelectorAll('#chat-transcript .chat-message').length")
                page.fill("#chat-input", "")
                page.type("#chat-input", prompt, delay=10)
                page.press("#chat-input", "Enter")
                for _ in range(120):
                    page.wait_for_timeout(100)
                    if page.evaluate("document.querySelectorAll('#chat-transcript .chat-message').length") >= seen + 2:
                        break
                page.wait_for_timeout(300)
            if idx in CARDS:
                page.evaluate("""(lines) => { const d = document.createElement('div');
                  d.style.cssText = 'position:fixed;inset:0;z-index:99;background:#fff;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:16px;font-family:-apple-system,Helvetica,sans-serif;font-weight:600;text-align:center;opacity:0;transition:opacity .7s ease';
                  d.innerHTML = lines.map(l => l[0] === 'MARK' ? '<img src="/samantha-logo.png" alt="" width="132" height="132" style="border-radius:28px;margin-bottom:6px">' : '<div style="font-size:' + l[1] + 'px;color:' + l[2] + '">' + l[0] + '</div>').join('');
                  document.body.appendChild(d); requestAnimationFrame(() => requestAnimationFrame(() => { d.style.opacity = 1; })); }""", CARDS[idx])
            spent = time.time() - seg_start
            page.wait_for_timeout(int(max(0, max(seconds + 0.7, HOLD[idx]) - spent) * 1000))
        page.wait_for_timeout(2500)
        ctx.close()
        browser.close()
    return glob.glob(os.path.join(out_dir, "*.webm"))[0], starts


def music(seconds, path, rate=32000):
    """A bright, bouncy minimal-pop bed, original and sample free: plucked arpeggios over C, G, Am, F at 116 bpm, a soft pulse that
    comes in after a few bars, off-beat ticks, a little bell on each bar, and a lift into one last hit when the end card lands.
    Written as a mono wav of the given length; the mux mixes it under her voice."""
    import numpy as np
    n = int(seconds * rate)
    t = np.arange(n) / rate
    out = np.zeros(n)
    beat = 60 / 116
    chords = [(65.41, [261.63, 329.63, 392.0, 523.25]), (49.0, [246.94, 293.66, 392.0, 493.88]),
              (55.0, [261.63, 329.63, 440.0, 523.25]), (43.65, [220.0, 261.63, 349.23, 440.0])]
    pattern = [0, 1, 2, 3, 2, 1, 2, 3]

    def put(start, wave):
        """Add a rendered sound into the mix at a time in seconds."""
        i = int(start * rate)
        if 0 <= i < n:
            m = min(len(wave), n - i)
            out[i:i + m] += wave[:m]

    def tone(f, dur, decay, harm=(1, 0.5, 0.25)):
        """A plucked tone: a few harmonics with a fast exponential decay."""
        x = np.arange(int(dur * rate)) / rate
        return sum(h * np.sin(2 * np.pi * f * (k + 1) * x) for k, h in enumerate(harm)) * np.exp(-x * decay)

    bars = int(seconds / (beat * 4)) + 1
    for bar in range(bars):
        t0 = bar * beat * 4
        root, notes = chords[bar % 4]
        for k, idx in enumerate(pattern):  # eighth-note plucks
            put(t0 + k * beat / 2, 0.30 * tone(notes[idx], 0.5, 9))
        put(t0, 0.55 * tone(root * 2, beat * 2, 2.5, (1, 0.2)))  # bass on the bar
        put(t0 + beat * 2, 0.40 * tone(root * 2, beat * 2, 2.5, (1, 0.2)))
        put(t0, 0.10 * tone(notes[3] * 2, 1.2, 3, (1, 0.3)))  # bell
        if bar >= 1:  # soft pulse on every beat, a snare-ish tick on 2 and 4, a hat on every off-beat
            for b in range(4):
                x = np.arange(int(0.16 * rate)) / rate
                put(t0 + b * beat, 0.55 * np.sin(2 * np.pi * (45 + 70 * np.exp(-x * 40)) * x) * np.exp(-x * 20))
                rng = np.random.default_rng(bar * 4 + b)
                if b in (1, 3):
                    y = np.arange(int(0.12 * rate)) / rate
                    put(t0 + b * beat, 0.16 * rng.standard_normal(len(y)) * np.exp(-y * 28))
                y = np.arange(int(0.04 * rate)) / rate
                put(t0 + b * beat + beat / 2, 0.08 * rng.standard_normal(len(y)) * np.exp(-y * 90))
    lift = max(0, seconds - 6.5)  # a riser into the end card, then one last chord
    r = t >= lift
    out += r * 0.10 * np.random.default_rng(7).standard_normal(n) * np.clip((t - lift) / 5.0, 0, 1) ** 2
    for f in (261.63, 329.63, 392.0, 523.25):
        put(seconds - 5.0, 0.30 * tone(f, 4.8, 1.1))
    out *= 0.9 / max(1e-6, np.max(np.abs(out)))
    pcm = (np.clip(out, -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm.tobytes())
    return path


def build(webm, starts, clips, out_dir):
    """Mux the recording with each narration clip delayed to its segment start, write captions, cut a poster. Returns the three file paths."""
    total = starts[-1] + clips[-1][1] + 1.5
    bed = music(total, os.path.join(out_dir, "bed.wav"))
    inputs, filters = ["-i", webm, "-i", bed], []
    for i, ((mp3, _), start) in enumerate(zip(clips, starts)):
        inputs += ["-i", mp3]
        filters.append(f"[{i + 2}:a]adelay={int(start * 1000)}|{int(start * 1000)}[a{i}]")
    voice_mix = "".join(f"[a{i}]" for i in range(len(clips))) + f"amix=inputs={len(clips)}:normalize=0[voice0];[voice0]asplit=2[voice][vkey]"
    # the bed sits about 15 dB under her voice, fades in and out, and gets a little echo so it reads as a room, not a beep
    bed_chain = f"[1:a]aecho=0.8:0.6:380:0.25,volume=0.75,afade=t=in:d=1,afade=t=out:st={total - 3:.2f}:d=3[bed]"
    # the music stays up in the gaps and ducks under her voice, the way a spot is mixed: her words key a compressor on the bed
    duck = "[bed][vkey]sidechaincompress=threshold=0.02:ratio=10:attack=15:release=500[ducked]"
    mix = voice_mix + ";" + bed_chain + ";" + duck + ";[voice][ducked]amix=inputs=2:normalize=0:duration=longest[mixed];[mixed]loudnorm=I=-16:TP=-1.5:LRA=11[aout]"
    mp4 = os.path.join(out_dir, "promo.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(filters + [mix]), "-map", "0:v", "-map", "[aout]",
                    "-c:v", "libx264", "-crf", "30", "-preset", "slow", "-pix_fmt", "yuv420p", "-vf", "scale=1280:-2", "-c:a", "aac", "-b:a", "96k",
                    "-movflags", "+faststart", "-shortest", mp4], check=True)
    vtt = os.path.join(out_dir, "promo.vtt")
    with open(vtt, "w") as f:
        f.write("WEBVTT\n\n")
        ends = starts[1:] + [duration(mp4)]
        for (text, _), start, end in zip(SEGMENTS, starts, ends):
            f.write(f"{clock(start)} --> {clock(end - 0.05)}\n{text}\n\n")
    poster = os.path.join(out_dir, "promo-poster.jpg")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(starts[0] + 5), "-i", mp4, "-frames:v", "1", "-q:v", "4", poster], check=True)
    return mp4, vtt, poster


def main():
    """Narrate, record, build, then copy the three files into web/."""
    key = voice.eleven_key()
    if not key:
        sys.exit("No ELEVENLABS_API_KEY in the environment or the fish secrets file.")
    work = tempfile.mkdtemp()
    clips = narrate(key)
    webm, starts = record(clips, work)
    mp4, vtt, poster = build(webm, starts, clips, work)
    for path in (mp4, vtt, poster):
        shutil.copy(path, os.path.join(REPO, "web", os.path.basename(path)))
    print(json.dumps({"seconds": round(duration(mp4), 1), "mb": round(os.path.getsize(mp4) / 1e6, 2), "segments": [round(s, 1) for s in starts]}))


if __name__ == "__main__":
    main()
