"""Her memory in your own iCloud Drive, only when you ask (7.0: remembers, and nothing of ours in a cloud).

    keep my memory in icloud          keep my memory on this mac

The memory file is plain JSON, the facts you told her. By default it lives on this Mac (~/.samantha/memory.json). "Keep my memory in
icloud" copies it to iCloud Drive/Samantha/memory.json, merging with a copy already there, and points her at it, so your own iCloud
carries it to your other devices. It is your iCloud, not a server of ours. "Keep my memory on this mac" brings it back and leaves the
iCloud copy for you to delete in Files. She asks first (a write), a model never picks it, and she never touches iCloud on her own:
macOS may show its own folder-access prompt the first time, and that prompt is yours to answer.
"""
import json
import os
import re

_I = re.I
POINTER = "~/.samantha/memory-location"
LOCAL = "~/.samantha/memory.json"
CLOUD = "~/Library/Mobile Documents/com~apple~CloudDocs"


def _read(path):
    """The facts in a memory file: a list of strings, or nothing for a missing or broken file."""
    try:
        with open(path) as f:
            got = json.load(f)
    except (OSError, ValueError):
        return []
    return [x for x in got if isinstance(x, str)] if isinstance(got, list) else []


def _merge(first, second):
    """Both lists, oldest first, each fact once (same words in any case count as the same fact), the last 500."""
    seen, out = set(), []
    for fact in first + second:
        if fact.lower() not in seen:
            seen.add(fact.lower())
            out.append(fact)
    return out[-500:]


def _write(path, facts):
    """Write a memory file, creating its folder."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(facts, f, indent=1)


def keep_memory(where):
    """"Keep my memory in icloud" or "keep my memory on this mac": moves her memory file there (merged, nothing lost) and
    remembers where it is. Asks first; only the two places, and iCloud only if iCloud Drive is on for this Mac."""
    pointer, local = os.path.expanduser(POINTER), os.path.expanduser(LOCAL)
    here = _read(local)
    if os.path.exists(pointer):
        with open(pointer) as f:
            here = _read(f.read().strip())
    if where == "icloud":
        drive = os.path.expanduser(CLOUD)
        if not os.path.isdir(drive):
            return "iCloud Drive is not turned on for this Mac, so I left your memory where it is."
        dest = os.path.join(drive, "Samantha", "memory.json")
        merged = _merge(_read(dest), here)
        _write(dest, merged)
        os.makedirs(os.path.dirname(pointer), exist_ok=True)
        with open(pointer, "w") as f:
            f.write(dest)
        return f"Done. Your memory ({len(merged)} things) now lives in iCloud Drive, in the Samantha folder. It is your iCloud, not a server of ours."
    merged = _merge(_read(local), here)
    _write(local, merged)
    if os.path.exists(pointer):
        os.remove(pointer)
    return f"Done. Your memory ({len(merged)} things) is on this Mac again. The iCloud copy is still in the Samantha folder; delete it in Files if you want it gone."


TOOLS = (keep_memory,)

# (pattern, tool name, what to hand it), same shape as tools_system.ROUTES; spliced in ahead of the base router.
ROUTES = (
    (re.compile(r"^(?:keep|put|store|sync|save) my (?:memory|facts)(?: in| with| to| on) icloud$", _I), "keep_memory", lambda m: "icloud"),
    (re.compile(r"^(?:keep|put|store|move) my (?:memory|facts) (?:on|to) this mac$|^stop syncing my (?:memory|facts)(?: with icloud)?$", _I),
     "keep_memory", lambda m: "mac"),
)


def demo():
    """Self-check against a throwaway home: icloud merges and points, mac brings it back, and no iCloud folder means no change."""
    import tempfile
    home = tempfile.mkdtemp()
    os.environ["HOME"] = home
    _write(os.path.join(home, ".samantha", "memory.json"), ["my dog is called Biscuit"])
    assert "not turned on" in keep_memory("icloud")
    os.makedirs(os.path.join(home, "Library", "Mobile Documents", "com~apple~CloudDocs"))
    assert "1 things" in keep_memory("icloud") and os.path.exists(os.path.join(home, ".samantha", "memory-location"))
    assert _read(os.path.join(home, "Library", "Mobile Documents", "com~apple~CloudDocs", "Samantha", "memory.json")) == ["my dog is called Biscuit"]
    assert "on this Mac again" in keep_memory("mac") and not os.path.exists(os.path.join(home, ".samantha", "memory-location"))
    assert _merge(["A b"], ["a B", "c"]) == ["A b", "c"]
    print("tools_profile ok")


if __name__ == "__main__":
    demo()
