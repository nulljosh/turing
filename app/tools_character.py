"""Samantha's character family: her voice and her look, changed by asking. list_voices reads the ElevenLabs premade
voices her key can use, set_voice writes one into the character's character.json (voice.py reads it on the next
line she says), restyle renders a new portrait into a staging folder next to the live one, and keep_look promotes
it and re-renders her idle and talk loops. The renders run the character-creator skill's portrait.sh and loop.sh
(Higgsfield, which costs real money), so restyle and keep_look are WRITES, hidden from models, and the confirm names
the cost first. Headless (SAMANTHA_HEADLESS=1) never touches ElevenLabs or Higgsfield.
"""
import difflib
import json
import os
import re
import shutil
import subprocess
import time

from tools_apps import HEADLESS

_I = re.I
VOICES_URL = "https://api.elevenlabs.io/v2/voices?page_size=100"
PORTRAIT_COST = 0.05  # Higgsfield Soul v2, a few cents a portrait
LOOP_COST = 0.70  # Seedance at 480p, about $0.14 a second, five seconds a loop
LOOPS = ("idle", "talk")  # keep_look re-renders these two; face.py falls back to idle while listening
# What the harness adds to the confirm line, so nobody says yes to a render without seeing the price.
CONFIRM_NOTES = {"restyle": f"This makes a new portrait on Higgsfield, about {int(PORTRAIT_COST * 100)} cents.",
                 "keep_look": f"This renders two new video loops on Higgsfield, about ${LOOP_COST * len(LOOPS):.2f}."}


def _character():
    """The live character folder, read at call time so a test can point it somewhere safe."""
    return os.path.expanduser(os.environ.get("SAMANTHA_CHARACTER", "~/.samantha/characters/samantha"))


def _staging():
    """Where restyle puts a new portrait: beside the live one, never over it."""
    return os.path.join(_character(), "staged")


def _scripts():
    """The character-creator skill's scripts folder."""
    return os.path.expanduser(os.environ.get("SAMANTHA_CHARACTER_SCRIPTS", "~/.claude/skills/character-creator/scripts"))


def _load():
    """character.json as a dict; {} when there is none or it is broken."""
    try:
        with open(os.path.join(_character(), "character.json")) as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save(data):
    """Write character.json back, creating the folder if it is new."""
    os.makedirs(_character(), exist_ok=True)
    with open(os.path.join(_character(), "character.json"), "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def _fetch(url, key):
    """GET a JSON document from ElevenLabs. None in headless or on any failure. Tests replace this."""
    if HEADLESS:
        return None
    import urllib.request
    try:
        req = urllib.request.Request(url, headers={"xi-api-key": key, "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except Exception:
        return None


def _run(argv):
    """Run one skill script. (ok, last line of output). Headless never runs it. Tests replace this."""
    if HEADLESS:
        return False, "headless: no render"
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=900)
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, str(e)
    lines = (p.stdout + p.stderr).strip().splitlines()
    return p.returncode == 0, lines[-1] if lines else ""


def _premade():
    """(voices, error): the premade voices as [(name, id, one line)], or [] and a plain reason."""
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        return [], "I don't have an ElevenLabs key, so I only have the Mac's own voice. Set ELEVENLABS_API_KEY to pick one."
    got = _fetch(VOICES_URL, key)
    if not isinstance(got, dict):
        return [], "I couldn't reach ElevenLabs to list voices."
    out = []
    for v in got.get("voices") or []:
        if v.get("category") != "premade" or not v.get("voice_id"):
            continue
        name = str(v.get("name") or "").split(" - ")[0].strip()
        labels = v.get("labels") or {}
        line = v.get("description") or ", ".join(str(labels[k]) for k in ("gender", "age", "accent", "descriptive", "use_case") if labels.get(k))
        out.append((name, v["voice_id"], " ".join(str(line).split())[:80]))
    return out, None if out else "ElevenLabs gave me no premade voices."


def list_voices():
    """The ElevenLabs premade voices she can speak with, one per line: name and a short description. Read only."""
    voices, err = _premade()
    if err:
        return err
    now = _load().get("voice_id")
    return "\n".join(f"{n}{' (now)' if i == now else ''}: {d}" if d else n for n, i, d in voices)


def set_voice(name):
    """Switch her voice to a premade ElevenLabs voice by name, saved as voice_id in character.json. An unknown name
    changes nothing and names the close ones."""
    want = (name or "").strip().strip(".").lower()
    if not want:
        return "Which voice? Ask what voices I have."
    voices, err = _premade()
    if err:
        return err
    hit = next(((n, i) for n, i, _ in voices if n.lower() == want), None)
    if not hit:
        close = difflib.get_close_matches(want, [n.lower() for n, _, _ in voices], n=3, cutoff=0.5)
        names = [n for n, _, _ in voices if n.lower() in close] or [n for n, _, _ in voices[:5]]
        return f"I don't have a voice called {name.strip()}. Close ones: {', '.join(names)}."
    data = _load()
    data["voice_id"] = hit[1]
    _save(data)
    if os.environ.get("ELEVENLABS_VOICE"):
        return f"Saved {hit[0]} as my voice, but ELEVENLABS_VOICE is set and wins until you unset it."
    return f"Okay, I'm {hit[0]} now."


def restyle(description):
    """Make a new portrait of her from a description into a staging folder (never over the live one) with the
    character-creator skill's portrait.sh. Costs a few cents on Higgsfield; say keep that look to use it."""
    desc = (description or "").strip().strip(".")
    if not desc:
        return "Describe the look you want, like: make yourself ginger with glasses."
    look = _load().get("look") or "Head-and-shoulders portrait of a friendly adult woman, soft studio light, plain background, photorealistic"
    prompt = desc if len(desc.split()) > 15 else f"{look}. Change only this: {desc}."
    stage = _staging()
    shutil.rmtree(stage, ignore_errors=True)
    os.makedirs(stage)
    ok, said = _run([os.path.join(_scripts(), "portrait.sh"), stage, prompt])
    if not ok or not os.path.isfile(os.path.join(stage, "portrait.png")):
        shutil.rmtree(stage, ignore_errors=True)
        return f"I couldn't make the new portrait ({said or 'no output'}). Nothing changed."
    with open(os.path.join(stage, "look.txt"), "w") as f:
        f.write(prompt + "\n")
    return (f"New look ready at {os.path.join(stage, 'portrait.png')}. That cost about {int(PORTRAIT_COST * 100)} cents. "
            f"Say keep that look to make it mine (two video loops, about ${LOOP_COST * len(LOOPS):.2f}).")


def keep_look():
    """Promote the staged portrait to her live look and re-render her idle and talk loops with loop.sh (about
    $1.40 on Higgsfield). The live look is only replaced once both loops render; the old one is kept in old/."""
    stage, live = _staging(), _character()
    if not (os.path.isfile(os.path.join(stage, "portrait.png")) and os.path.isfile(os.path.join(stage, "portrait.url"))):
        return "There's no new look waiting. Ask me to change my look first."
    for kind in LOOPS:
        ok, said = _run([os.path.join(_scripts(), "loop.sh"), stage, kind])
        if not ok or not os.path.isfile(os.path.join(stage, f"{kind}.mp4")):
            return f"The {kind} loop didn't render ({said or 'no output'}). My old look stays; the new portrait is still staged."
    backup = os.path.join(live, "old", time.strftime("%Y%m%d-%H%M%S"))
    os.makedirs(backup, exist_ok=True)
    for name in ("portrait.png", "portrait.url", "idle.mp4", "listen.mp4", "talk.mp4"):
        if os.path.isfile(os.path.join(live, name)):
            shutil.move(os.path.join(live, name), os.path.join(backup, name))
    look = ""
    for name in os.listdir(stage):
        if name == "look.txt":
            with open(os.path.join(stage, name)) as f:
                look = f.read().strip()
        else:
            shutil.move(os.path.join(stage, name), os.path.join(live, name))
    shutil.rmtree(stage, ignore_errors=True)
    if look:
        data = _load()
        data["look"] = look
        _save(data)
    return f"That's me now. The two loops cost about ${LOOP_COST * len(LOOPS):.2f}; my old look is in {backup}."


TOOLS = (list_voices, set_voice, restyle, keep_look)

# (pattern, tool name, what to hand it), same shape as tools_system.ROUTES; spliced in ahead of the base router.
ROUTES = (
    (re.compile(r"^(?:what|which) voices (?:do you have|can you (?:use|do)|are there)\??$|^(?:list|show)(?: me)? (?:your |the )?voices$", _I),
     "list_voices", lambda m: None),
    (re.compile(r"^(?:change|switch|set) your voice to (.+?)\.?$", _I), "set_voice", lambda m: m.group(1)),
    (re.compile(r"^change your look(?::| to)? (.+)$|^make yourself (.+)$", _I), "restyle", lambda m: m.group(1) or m.group(2)),
    (re.compile(r"^keep (?:that|this|the new) look\.?$", _I), "keep_look", lambda m: None),
)


def demo():
    """Self-check: routes name real tools and every tool has a docstring. No network, no scripts."""
    names = {f.__name__ for f in TOOLS}
    assert all(name in names for _, name, _ in ROUTES)
    assert ROUTES[1][0].match("change your voice to George").group(1) == "George"
    assert ROUTES[2][0].match("make yourself ginger").group(2) == "ginger"
    assert all(f.__doc__ for f in TOOLS)
    print("tools_character ok")


if __name__ == "__main__":
    demo()
