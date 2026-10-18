"""Samantha's video tools. video_info reads a video inside the home folder (.mp4, .mov, .m4v, .mkv, .webm) and says how
long it is, how big, and its picture and sound, read only. trim_video (a write, asks first) cuts a clip between two
times, vertical_video (a write, asks first) centre-crops a video to 9:16 for a phone, and trim_audio (a write, asks
first) cuts a piece out of a sound file (.mp3, .m4a, .wav, .aac, .flac, .ogg), and extract_audio (a write, asks first)
pulls the sound out of a video into an .mp3, .m4a or .wav, and mute_video (a write, asks first) makes a silent copy of a video. Each write makes a new file
beside the original, never over an existing one. They run ffmpeg and ffprobe. Same home-folder rule as tools_files:
home only, nothing hidden. tests/test_video.py mocks subprocess, so no real ffmpeg run happens there.
"""
import json
import os
import re
import shutil
import subprocess

import tools_files

HOME = tools_files.HOME
_home = tools_files._home
_short = tools_files._short

_FORMATS = (".mp4", ".mov", ".m4v", ".mkv", ".webm")
_AUDIO = (".mp3", ".m4a", ".wav", ".aac", ".flac", ".ogg")
_NO_FFMPEG = "ffmpeg is not installed here, so I cannot work on videos."
_TIME = re.compile(r"^\d+(?::\d{1,2}){0,2}(?:\.\d+)?$")  # 25, 0:25, 1:02:03, 7.5


def _exe(name):
    """The path to ffmpeg or ffprobe, or None when this Mac has neither."""
    return shutil.which(name) or (f"/opt/homebrew/bin/{name}" if os.path.exists(f"/opt/homebrew/bin/{name}") else None)


def _video(path):
    """The real path of a video inside the home folder, or None."""
    full = _home(path)
    return full if full and os.path.isfile(full) and full.lower().endswith(_FORMATS) else None


def _clock(seconds):
    """83 -> 1:23, 3725 -> 1:02:05."""
    s = int(round(float(seconds)))
    h, m, s = s // 3600, s % 3600 // 60, s % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def video_info(path):
    """How long a video inside the home folder is, its size and its picture and sound (.mp4, .mov, .m4v, .mkv, .webm). Read only."""
    full = _video(path)
    if not full:
        return f"No video {path.strip()} I am allowed to open."
    exe = _exe("ffprobe")
    if not exe:
        return _NO_FFMPEG
    try:
        out = subprocess.run([exe, "-v", "error", "-show_entries", "format=duration,size:stream=codec_type,codec_name,width,height",
                              "-of", "json", full], capture_output=True, text=True, timeout=60).stdout
        info = json.loads(out)
        seconds = float(info["format"]["duration"])
    except (OSError, subprocess.SubprocessError):
        return "ffprobe did not answer."
    except (ValueError, KeyError):
        return f"I could not read {_short(full)} as a video."
    streams = info.get("streams", [])
    pic = next((s for s in streams if s.get("codec_type") == "video"), None)
    sound = next((s for s in streams if s.get("codec_type") == "audio"), None)
    look = f"{pic['width']}x{pic['height']} {pic['codec_name']}" if pic and "width" in pic else "no picture"
    hear = f"{sound['codec_name']} sound" if sound else "no sound"
    return f"{_short(full)} is {_clock(seconds)} long, {tools_files._size(int(info['format'].get('size', 0)))}, {look}, {hear}."


def _make(full, suffix, args):
    """Run ffmpeg on a video into <name>-<suffix>.mp4 beside it, never over a file. Returns the output path or a plain reason."""
    out = os.path.splitext(full)[0] + "-" + suffix + ".mp4"
    if os.path.exists(out):
        return None, f"{_short(out)} already exists."
    if tools_files.HEADLESS:
        return out, ""
    exe = _exe("ffmpeg")
    if not exe:
        return None, _NO_FFMPEG
    tmp = out + ".part.mp4"
    try:
        done = subprocess.run([exe, "-hide_banner", "-loglevel", "error", "-i", full, *args, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", tmp],
                              capture_output=True, timeout=900)
    except (OSError, subprocess.SubprocessError):
        return None, "ffmpeg did not finish."
    if done.returncode != 0 or not os.path.exists(tmp):
        if os.path.exists(tmp):
            os.remove(tmp)
        return None, f"ffmpeg could not make that from {_short(full)}."
    os.replace(tmp, out)
    return out, ""


def trim_video(request):
    """Cut a clip out of a video inside the home folder. Takes 'path<TAB>start<TAB>end' with times like 0:10 or 25. Makes <name>-clip.mp4 beside it. Asks first."""
    parts = [p.strip() for p in request.split("\t")]
    if len(parts) != 3:
        return "Say which video and the two times, like: trim ~/Movies/a.mp4 from 0:10 to 0:25."
    full = _video(parts[0])
    if not full:
        return f"No video {parts[0]} I am allowed to open."
    start, end = parts[1], parts[2]
    if not (_TIME.match(start) and _TIME.match(end)):
        return "Give the times like 0:10 or 25."
    out, why = _make(full, "clip", ["-ss", start, "-to", end])
    return why or f"Cut {start} to {end} into {_short(out)}."


def vertical_video(path):
    """Centre-crop a video inside the home folder to 9:16 for a phone, 1080x1920. Makes <name>-vertical.mp4 beside it. Asks first."""
    full = _video(path)
    if not full:
        return f"No video {path.strip()} I am allowed to open."
    out, why = _make(full, "vertical", ["-vf", "crop=w='min(iw,ih*9/16)':h='min(ih,iw*16/9)',scale=1080:1920"])
    return why or f"Made a vertical version at {_short(out)}."


def trim_audio(request):
    """Cut a piece out of a sound file inside the home folder (.mp3, .m4a, .wav, .aac, .flac, .ogg). Takes 'path<TAB>start<TAB>end' with times like 0:10 or 25. Makes <name>-clip beside it, same format. Asks first."""
    parts = [p.strip() for p in request.split("\t")]
    if len(parts) != 3:
        return "Say which sound file and the two times, like: trim ~/Music/a.mp3 from 0:10 to 0:25."
    full = _home(parts[0])
    if not full or not os.path.isfile(full) or not full.lower().endswith(_AUDIO):
        return f"No sound file {parts[0]} I am allowed to open."
    start, end = parts[1], parts[2]
    if not (_TIME.match(start) and _TIME.match(end)):
        return "Give the times like 0:10 or 25."
    base, ext = os.path.splitext(full)
    out = base + "-clip" + ext
    if os.path.exists(out):
        return f"{_short(out)} already exists."
    if tools_files.HEADLESS:
        return f"Cut {start} to {end} into {_short(out)}."
    exe = _exe("ffmpeg")
    if not exe:
        return _NO_FFMPEG
    tmp = base + "-clip.part" + ext  # the extension picks the codec
    try:
        done = subprocess.run([exe, "-hide_banner", "-loglevel", "error", "-i", full, "-ss", start, "-to", end, "-vn", tmp], capture_output=True, timeout=300)
    except (OSError, subprocess.SubprocessError):
        return "ffmpeg did not finish."
    if done.returncode != 0 or not os.path.exists(tmp):
        if os.path.exists(tmp):
            os.remove(tmp)
        return f"ffmpeg could not cut that from {_short(full)}."
    os.replace(tmp, out)
    return f"Cut {start} to {end} into {_short(out)}."


def extract_audio(request):
    """Pull the sound out of a video inside the home folder into an .mp3, .m4a or .wav. Takes 'path<TAB>format'. Makes <name>.<format> beside it, never over a file. Asks first."""
    path, _, fmt = request.partition("\t")
    fmt = fmt.strip().lower().lstrip(".")
    full = _video(path)
    if not full:
        return f"No video {path.strip()} I am allowed to open."
    if fmt not in ("mp3", "m4a", "wav"):
        return f"I can make mp3, m4a or wav, not {fmt or 'nothing'}."
    out = os.path.splitext(full)[0] + "." + fmt
    if os.path.exists(out):
        return f"{_short(out)} already exists."
    if tools_files.HEADLESS:
        return f"Pulled the sound into {_short(out)}."
    exe = _exe("ffmpeg")
    if not exe:
        return _NO_FFMPEG
    tmp = os.path.splitext(full)[0] + ".part." + fmt  # the extension picks the codec
    try:
        done = subprocess.run([exe, "-hide_banner", "-loglevel", "error", "-i", full, "-vn", tmp], capture_output=True, timeout=900)
    except (OSError, subprocess.SubprocessError):
        return "ffmpeg did not finish."
    if done.returncode != 0 or not os.path.exists(tmp):
        if os.path.exists(tmp):
            os.remove(tmp)
        return f"ffmpeg could not pull sound from {_short(full)}."
    os.replace(tmp, out)
    return f"Pulled the sound into {_short(out)}."


def mute_video(path):
    """Make a silent copy of a video inside the home folder: <name>-muted.mp4 beside it, never over a file. Asks first."""
    full = _video(path)
    if not full:
        return f"No video {path.strip()} I am allowed to open."
    out, why = _make(full, "muted", ["-an"])
    return why or f"Made a silent copy at {_short(out)}."


TOOLS = (video_info, trim_video, vertical_video, trim_audio, extract_audio, mute_video)

_I = re.I
_EXT = r"(\S+\.(?:mp4|mov|m4v|mkv|webm))"
# (pattern, tool name, what to hand it), same shape as tools_files.ROUTES. Only a path ending in a video extension
# matches, so "trim my hedge" and "how long is the movie" stay with the other tools.
ROUTES = (
    (re.compile(r"^(?:how long is|what(?:'s| is) in|inspect) (?:the |my )?" + _EXT + "$", _I), "video_info", lambda m: m.group(1)),
    (re.compile(r"^(?:trim|cut|clip) (?:the |my )?" + _EXT + r" from (\S+) (?:to|until) (\S+)$", _I), "trim_video", lambda m: "\t".join(m.groups())),
    (re.compile(r"^make (?:the |my )?" + _EXT + r" (?:vertical|portrait)$", _I), "vertical_video", lambda m: m.group(1)),
    (re.compile(r"^make a (?:vertical|portrait) (?:version|copy) of (?:the |my )?" + _EXT + "$", _I), "vertical_video", lambda m: m.group(1)),
    (re.compile(r"^(?:trim|cut|clip) (?:the |my )?(\S+\.(?:mp3|m4a|wav|aac|flac|ogg)) from (\S+) (?:to|until) (\S+)$", _I), "trim_audio", lambda m: "\t".join(m.groups())),
    (re.compile(r"^(?:extract|pull|rip|get) (?:the )?(?:audio|sound) (?:out )?(?:of|from) (?:the |my )?" + _EXT + r"(?: (?:as|to|into) (?:an? )?\.?(mp3|m4a|wav))?$", _I), "extract_audio",
     lambda m: m.group(1) + "\t" + (m.group(2) or "mp3")),
    (re.compile(r"^(?:mute|silence) (?:the |my )?" + _EXT + "$", _I), "mute_video", lambda m: m.group(1)),
    (re.compile(r"^(?:remove|strip|drop) the (?:audio|sound) (?:from|of) (?:the |my )?" + _EXT + "$", _I), "mute_video", lambda m: m.group(1)),
)


def demo():
    """Self-check: the routes, the clock and the refusals, no ffmpeg run."""
    assert ROUTES[0][0].match("how long is ~/Movies/a.mov") and not ROUTES[0][0].match("how long is the movie")
    assert ROUTES[1][0].match("trim ~/Movies/a.mp4 from 0:10 to 0:25") and not ROUTES[1][0].match("trim my hedge")
    assert ROUTES[2][0].match("make ~/a.mp4 vertical") and ROUTES[3][0].match("make a vertical version of ~/a.mp4")
    assert ROUTES[-2][0].match("mute ~/Movies/a.mp4") and ROUTES[-1][0].match("remove the audio from ~/a.mov") and not ROUTES[-2][0].match("mute the volume")
    assert _clock(83) == "1:23" and _clock(3725) == "1:02:05"
    assert "allowed" in video_info("~/.ssh/a.mp4") and "allowed" in vertical_video("/etc/a.mp4") and "allowed" in mute_video("~/.ssh/a.mp4")
    assert all(f.__doc__ for f in TOOLS)
    print("tools_video ok")


if __name__ == "__main__":
    demo()
