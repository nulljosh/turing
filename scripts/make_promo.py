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
# (what she says over it, [what is typed into the demo while she says it]); each segment lasts at least as long as its line
# lines shown on a card over the last demo segment: the things the web stand-in cannot do, said plainly as Mac-only, never faked
MAC_ONLY = ["research the history of the printing press", "what's on my screen", "click Sign in"]
SEGMENTS = [
    ("This is Samantha. A small AI that lives on your Mac. Free, and private.", []),
    ("She paints from thirty thousand squares. She draws anything you can name.", ["paint the mona lisa", "draw a lighthouse at dusk"]),
    ("She runs your Mac. Volume, screenshots, your apps.", ["set the volume to 40", "take a screenshot"]),
    ("She keeps your notes and reminders.", ["remind me to call mom tomorrow at 9"]),
    ("She finds your files.", ["find budget.pdf"]),
    ("She does the math and converts units.", ["what is 17*23", "convert 72 f to c"]),
    ("Ask her anything. On a real Mac she researches with sources, reads your screen and clicks for you. She always asks first.", []),
    ("Free. Private. Download her for Mac.", []),
]


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
        ctx = browser.new_context(viewport={"width": W, "height": H}, record_video_dir=out_dir, record_video_size={"width": W, "height": H}, color_scheme="light")
        page = ctx.new_page()
        page.goto(URL)
        page.wait_for_selector("#chat-input")
        page.focus("#chat-input")  # a click would re-arm the page's idle reel, which then types over the script; typing stops it for good
        page.wait_for_timeout(1200)
        for (mp3, seconds), (line, prompts) in zip(clips, SEGMENTS):
            seg_start = time.time()
            starts.append(seg_start - t0)
            for prompt in prompts:
                seen = page.evaluate("document.querySelectorAll('#chat-transcript .chat-message').length")
                page.fill("#chat-input", "")
                page.type("#chat-input", prompt, delay=30)
                page.press("#chat-input", "Enter")
                for _ in range(48):
                    page.wait_for_timeout(250)
                    if page.evaluate("document.querySelectorAll('#chat-transcript .chat-message').length") >= seen + 2:
                        break
                page.wait_for_timeout(1200)
            if line.startswith("Ask her anything"):
                page.evaluate("""(lines) => { const d = document.createElement('div');
                  d.style.cssText = 'position:fixed;inset:0;z-index:99;background:#fff;color:#151515;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:18px;font:600 34px -apple-system,Helvetica,sans-serif;text-align:center';
                  d.innerHTML = lines.map(l => '<div>' + l + '</div>').join('') + '<div style="font:500 22px -apple-system,Helvetica,sans-serif;color:#666;margin-top:14px">On a real Mac. She always asks first.</div>';
                  document.body.appendChild(d); }""", MAC_ONLY)
            spent = time.time() - seg_start
            page.wait_for_timeout(int(max(0, seconds + 0.7 - spent) * 1000))
        page.wait_for_timeout(800)
        ctx.close()
        browser.close()
    return glob.glob(os.path.join(out_dir, "*.webm"))[0], starts


def music(seconds, path, rate=22050):
    """A soft synthesized bed under her voice: a slow C, Am, F, G arpeggio in triangle-ish tones with a long decay, no samples and
    nothing to license. Written as a mono wav of the given length; the mux mixes it far below the narration."""
    chords = [(130.81, [261.63, 329.63, 392.0, 523.25]), (110.0, [220.0, 261.63, 329.63, 440.0]),
              (87.31, [174.61, 261.63, 349.23, 440.0]), (98.0, [196.0, 246.94, 293.66, 392.0])]
    step, n, frames = 60 / 84 / 2, int(seconds * rate), []
    for i in range(n):
        t = i / rate
        k = int(t / step)
        bar = (k // 8) % len(chords)
        bass, notes = chords[bar]
        local = t - k * step
        f = notes[k % len(notes)]
        v = 0.5 * math.exp(-local * 3.2) * (math.sin(2 * math.pi * f * t) + 0.25 * math.sin(4 * math.pi * f * t))
        v += 0.35 * math.sin(2 * math.pi * bass * t) * (0.6 + 0.4 * math.sin(2 * math.pi * 0.12 * t))
        frames.append(struct.pack("<h", int(max(-1, min(1, v * 0.6)) * 32767)))
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"".join(frames))
    return path


def build(webm, starts, clips, out_dir):
    """Mux the recording with each narration clip delayed to its segment start, write captions, cut a poster. Returns the three file paths."""
    total = starts[-1] + clips[-1][1] + 1.5
    bed = music(total, os.path.join(out_dir, "bed.wav"))
    inputs, filters = ["-i", webm, "-i", bed], []
    for i, ((mp3, _), start) in enumerate(zip(clips, starts)):
        inputs += ["-i", mp3]
        filters.append(f"[{i + 2}:a]adelay={int(start * 1000)}|{int(start * 1000)}[a{i}]")
    voice_mix = "".join(f"[a{i}]" for i in range(len(clips))) + f"amix=inputs={len(clips)}:normalize=0[voice]"
    # the bed sits about 15 dB under her voice, fades in and out, and gets a little echo so it reads as a room, not a beep
    bed_chain = f"[1:a]aecho=0.8:0.6:380:0.25,volume=0.34,afade=t=in:d=2,afade=t=out:st={total - 3:.2f}:d=3[bed]"
    mix = voice_mix + ";" + bed_chain + ";[voice][bed]amix=inputs=2:normalize=0:duration=longest[aout]"
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
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(starts[1] + 6), "-i", mp4, "-frames:v", "1", "-q:v", "4", poster], check=True)
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
