"""Samantha's Blender tools. blender_info reads a 3D file inside the home folder (.blend, .glb, .gltf, .obj, .fbx) and
says how many objects and vertices it holds, read only. render_blend (a write, asks first) renders frame 1 of a .blend
to a PNG named like it, in the same folder, never over an existing file. Both run Blender headless (blender -b).
Same home-folder rule as tools_files: home only, nothing hidden. tests/test_blender.py mocks subprocess, so no real
Blender run happens there.
"""
import glob
import json
import os
import re
import shutil
import subprocess
import tempfile

import tools_files

HOME = tools_files.HOME
_home = tools_files._home
_short = tools_files._short

_FORMATS = (".blend", ".glb", ".gltf", ".obj", ".fbx")
_NO_BLENDER = "Blender is not installed here, so I cannot open 3D files."

# Runs inside Blender (blender -b -P script.py -- file). Opens a .blend, or imports anything else into an empty scene,
# then prints one JSON line that blender_info reads back. Everything else Blender prints is ignored.
_INFO_SCRIPT = '''import bpy, json, sys
path = sys.argv[sys.argv.index("--") + 1]
if path.lower().endswith(".blend"):
    bpy.ops.wm.open_mainfile(filepath=path)
else:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    ext = path.lower().rsplit(".", 1)[-1]
    if ext in ("glb", "gltf"):
        bpy.ops.import_scene.gltf(filepath=path)
    elif ext == "obj":
        bpy.ops.wm.obj_import(filepath=path)
    else:
        bpy.ops.import_scene.fbx(filepath=path)
objs = list(bpy.data.objects)
meshes = [o for o in objs if o.type == "MESH"]
info = {"objects": len(objs), "vertices": sum(len(o.data.vertices) for o in meshes), "names": [o.name for o in objs][:20]}
print("BLENDINFO " + json.dumps(info))
'''


def _blender():
    """The path to the blender program, or None when this Mac has none."""
    return shutil.which("blender") or ("/opt/homebrew/bin/blender" if os.path.exists("/opt/homebrew/bin/blender") else None)


def blender_info(path):
    """What is in a 3D file inside the home folder (.blend, .glb, .gltf, .obj, .fbx): object count, object names and vertex total. Read only."""
    full = _home(path)
    if not full or not os.path.isfile(full) or not full.lower().endswith(_FORMATS):
        return f"No 3D file {path.strip()} I am allowed to open."
    exe = _blender()
    if not exe:
        return _NO_BLENDER
    with tempfile.TemporaryDirectory() as tmp:
        script = os.path.join(tmp, "info.py")
        with open(script, "w") as f:
            f.write(_INFO_SCRIPT)
        try:
            out = subprocess.run([exe, "-b", "-P", script, "--", full], capture_output=True, text=True, timeout=120).stdout
        except (OSError, subprocess.SubprocessError):
            return "Blender did not answer."
    line = next((x for x in out.splitlines() if x.startswith("BLENDINFO ")), None)
    try:
        info = json.loads(line[len("BLENDINFO "):]) if line else None
    except ValueError:
        info = None
    if not info:
        return f"Blender could not open {_short(full)}."
    names = ", ".join(info["names"]) or "none"
    more = info["objects"] - len(info["names"])
    tail = f", and {more} more" if more > 0 else ""
    return f"{_short(full)} has {info['objects']} objects and {info['vertices']:,} vertices: {names}{tail}."


def render_blend(path):
    """Render frame 1 of a .blend inside the home folder to a PNG named like it, in the same folder. Never overwrites. Asks first."""
    full = _home(path)
    if not full or not os.path.isfile(full) or not full.lower().endswith(".blend"):
        return f"No .blend file {path.strip()} I am allowed to render."
    out = os.path.splitext(full)[0] + ".png"
    if os.path.exists(out):
        return f"{_short(out)} already exists."
    if tools_files.HEADLESS:
        return f"Rendered frame 1 to {_short(out)}."
    exe = _blender()
    if not exe:
        return _NO_BLENDER
    with tempfile.TemporaryDirectory() as tmp:
        try:
            subprocess.run([exe, "-b", full, "-o", os.path.join(tmp, "frame_"), "-F", "PNG", "-f", "1"], capture_output=True, timeout=180)
        except (OSError, subprocess.SubprocessError):
            return "Blender did not finish the render."
        shots = sorted(glob.glob(os.path.join(tmp, "frame_*.png")))
        if not shots:
            return f"Blender made no image from {_short(full)}."
        if os.path.exists(out):
            return f"{_short(out)} already exists."
        shutil.move(shots[0], out)
    return f"Rendered frame 1 to {_short(out)}."


TOOLS = (blender_info, render_blend)

_I = re.I
# (pattern, tool name, what to hand it), same shape as tools_files.ROUTES. Only a path ending in a 3D extension or
# .blend matches, so "render my notes" and "inspect the logs" stay with the other tools.
ROUTES = (
    (re.compile(r"^(?:what(?:'s| is) in|inspect) (?:the |my )?(\S+\.(?:blend|glb|gltf|obj|fbx))$", _I), "blender_info", lambda m: m.group(1)),
    (re.compile(r"^render (?:the |my )?(\S+\.blend)$", _I), "render_blend", lambda m: m.group(1)),
)


def demo():
    """Self-check: the routes and the headless answer, no Blender run."""
    assert ROUTES[0][0].match("what's in ~/Documents/scene.blend") and ROUTES[0][0].match("inspect ~/x.glb")
    assert ROUTES[1][0].match("render ~/Documents/scene.blend") and not ROUTES[1][0].match("render my notes")
    assert "not" in blender_info("~/.ssh/key.blend") and "allowed" in render_blend("/etc/x.blend")
    assert all(f.__doc__ for f in TOOLS)
    print("tools_blender ok")


if __name__ == "__main__":
    demo()
