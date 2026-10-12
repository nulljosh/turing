"""She writes a Shortcut for you (7.0: she comes to you, but nothing runs behind your back).

    make a shortcut that says good morning          make a shortcut called Hello that opens https://example.com
    make a shortcut that shows a notification saying stand up      make a shortcut that sets the volume to 30

She lists the steps first, in plain words, and the harness asks before this runs (it is a WRITE). Then the Shortcut is built
from a fixed menu of four simple actions (speak, notification, open a link, volume), signed with Apple's own `shortcuts sign`,
saved to Downloads and opened, so the Shortcuts app shows its own "Add Shortcut" sheet: that sheet is the second yes. She never
installs anything herself, never schedules it, and never runs it. A model never picks this tool (NOT_FOR_MODELS), only the words above do.
Headless runs (tests, evals) describe the Shortcut and write nothing.
"""
import os
import plistlib
import re
import subprocess
import tempfile

_I = re.I
_SPEAK = re.compile(r"^(?:says?|speaks?|reads? out|reads?)\s+(.+)$", _I)
_NOTE = re.compile(r"^(?:shows?|sends?|posts?) (?:me )?(?:a )?notifications?(?: saying| that says| with)?\s+(.+)$", _I)
_LINK = re.compile(r"^opens?\s+(https?://\S+)$", _I)
_VOLUME = re.compile(r"^sets? (?:the )?volume to (\d{1,3})(?: ?%| percent)?$", _I)
_ASK = re.compile(r"^(?:make|create|build|write) (?:me )?a shortcut(?: called ([\w ]{1,40}?))?(?: that| to| which)\s+(.+)$", _I)
_MAX = 200


def parse(request):
    """(name, [step, ...]) from the words after "make a shortcut", or None when no step is one of the four she can build.
    A step is (action identifier, parameters, the plain sentence shown first)."""
    m = _ASK.match(request.strip())
    if not m:
        return None
    name, rest = (m.group(1) or "").strip(), m.group(2).strip()
    steps = []
    for part in re.split(r"\s+and then\s+|\s+then\s+", rest, flags=_I):
        part = part.strip().rstrip(".")
        if (s := _SPEAK.match(part)):
            text = s.group(1)[:_MAX].strip("\"'")
            steps.append(("is.workflow.actions.speaktext", {"WFText": text}, f'Speak "{text}".'))
        elif (s := _NOTE.match(part)):
            text = s.group(1)[:_MAX].strip("\"'")
            steps.append(("is.workflow.actions.notification", {"WFNotificationActionTitle": "Samantha", "WFNotificationActionBody": text},
                          f'Show a notification: "{text}".'))
        elif (s := _LINK.match(part)):
            url = s.group(1)[:_MAX]
            steps.append(("is.workflow.actions.url", {"WFURLActionURL": url}, f"Take the link {url}."))
            steps.append(("is.workflow.actions.openurl", {}, "Open it."))
        elif (s := _VOLUME.match(part)) and int(s.group(1)) <= 100:
            steps.append(("is.workflow.actions.setvolume", {"WFVolume": int(s.group(1)) / 100}, f"Set the volume to {int(s.group(1))} percent."))
        else:
            return None
    if not steps:
        return None
    return name or "Samantha " + re.sub(r"[^\w ]", "", rest)[:24].strip(), steps


def workflow(steps):
    """The Shortcut as the dictionary the Shortcuts app reads: one action per step, nothing that runs on a timer or an event."""
    return {"WFWorkflowClientVersion": "900", "WFWorkflowClientRelease": "2.0", "WFWorkflowMinimumClientVersion": 900,
            "WFWorkflowMinimumClientVersionString": "900",
            "WFWorkflowIcon": {"WFWorkflowIconStartColor": 431817727, "WFWorkflowIconGlyphNumber": 59511},
            "WFWorkflowImportQuestions": [], "WFWorkflowTypes": [], "WFWorkflowInputContentItemClasses": [],
            "WFWorkflowActions": [{"WFWorkflowActionIdentifier": ident, "WFWorkflowActionParameters": params} for ident, params, _ in steps]}


def make_shortcut(request):
    """"Make a shortcut that says good morning": lists the steps, then (after the harness asked) builds, signs, saves to
    Downloads and opens the Shortcut so the Shortcuts app asks you to add it. Only four simple actions: say, notify, open a
    link, set the volume. It never runs the Shortcut and never schedules it."""
    got = parse(request)
    if not got:
        return ("I can build a Shortcut from: say something, show a notification, open a link, or set the volume. "
                'Try "make a shortcut that says good morning".')
    name, steps = got
    plan = "\n".join(f"{i}. {s}" for i, (_, _, s) in enumerate(steps, 1))
    if os.environ.get("SAMANTHA_HEADLESS"):
        return f'Shortcut "{name}" would do:\n{plan}'
    safe = re.sub(r"[^\w ]", "", name).strip() or "Samantha Shortcut"
    out = os.path.join(os.path.expanduser("~"), "Downloads", safe + ".shortcut")
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "in.shortcut")   # the sign command only reads a file named like a Shortcut
        with open(src, "wb") as f:
            f.write(plistlib.dumps(workflow(steps), fmt=plistlib.FMT_BINARY))
        try:
            done = subprocess.run(["shortcuts", "sign", "-m", "people-who-know-me", "-i", src, "-o", out], capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.SubprocessError):
            return "I could not reach the Shortcuts tool on this Mac, so nothing was made."
    if done.returncode or not os.path.exists(out):
        return "The Shortcuts tool would not sign it, so nothing was made."
    subprocess.run(["open", out], timeout=15)
    return f'Shortcut "{name}":\n{plan}\nSaved to Downloads and opened. Shortcuts will ask you to add it; it runs only when you run it.'


TOOLS = (make_shortcut,)

# (pattern, tool name, what to hand it), same shape as tools_system.ROUTES; spliced in ahead of the base router.
ROUTES = (
    (re.compile(r"^((?:make|create|build|write) (?:me )?a shortcut\b.+)$", _I), "make_shortcut", lambda m: m.group(1)),
)


def demo():
    """Self-check: the four actions parse, anything else is declined, the plist round-trips, and headless writes nothing."""
    name, steps = parse("make a shortcut called Hello that says good morning and then sets the volume to 30")
    assert name == "Hello" and [s[0] for s in steps] == ["is.workflow.actions.speaktext", "is.workflow.actions.setvolume"], steps
    assert parse("make a shortcut that opens https://example.com")[1][1][0] == "is.workflow.actions.openurl"
    assert parse("make a shortcut that deletes my files") is None and parse("make a shortcut that sets the volume to 300") is None
    wf = plistlib.loads(plistlib.dumps(workflow(steps)))
    assert wf["WFWorkflowActions"][1]["WFWorkflowActionParameters"]["WFVolume"] == 0.3 and wf["WFWorkflowTypes"] == []
    os.environ["SAMANTHA_HEADLESS"] = "1"
    assert make_shortcut("make a shortcut that says hi").startswith('Shortcut "Samantha says hi" would do:')
    assert "I can build a Shortcut" in make_shortcut("make a shortcut that does a backflip")
    print("tools_shortcut ok")


if __name__ == "__main__":
    demo()
