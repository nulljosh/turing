"""Samantha's Blender tools. blender_info reads a 3D file inside the home folder (.blend, .glb, .gltf, .obj, .fbx) and
says how many objects and vertices it holds, read only. render_blend (a write, asks first) renders frame 1 of a .blend
to a PNG named like it, in the same folder, never over an existing file. convert_3d (a write, asks first) turns one
3D file into glb, obj, stl, ply or fbx beside it, never over an existing file. make_3d (a write, asks first) makes a cube, sphere, cone, cylinder or torus as a new
3D file, never over an existing one. All run Blender headless (blender -b).
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

_FORMATS = (".blend", ".glb", ".gltf", ".obj", ".fbx", ".stl", ".ply")
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
    elif ext == "stl":
        bpy.ops.wm.stl_import(filepath=path)
    elif ext == "ply":
        bpy.ops.wm.ply_import(filepath=path)
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
    """What is in a 3D file inside the home folder (.blend, .glb, .gltf, .obj, .fbx, .stl, .ply): object count, object names and vertex total. Read only."""
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


_IN = (".blend", ".glb", ".gltf", ".obj", ".fbx", ".stl", ".ply")
_OUT = ("glb", "obj", "stl", "ply", "fbx")

# Runs inside Blender (blender -b -P script.py -- source out_dir ext). Opens or imports the source, then exports the
# whole scene as one new file named like it into out_dir (an .obj also writes its .mtl beside it).
_CONVERT_SCRIPT = '''import bpy, os, sys
src, out_dir, ext = sys.argv[sys.argv.index("--") + 1:][:3]
low = src.lower()
if low.endswith(".blend"):
    bpy.ops.wm.open_mainfile(filepath=src)
else:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if low.endswith((".glb", ".gltf")):
        bpy.ops.import_scene.gltf(filepath=src)
    elif low.endswith(".obj"):
        bpy.ops.wm.obj_import(filepath=src)
    elif low.endswith(".stl"):
        bpy.ops.wm.stl_import(filepath=src)
    elif low.endswith(".ply"):
        bpy.ops.wm.ply_import(filepath=src)
    else:
        bpy.ops.import_scene.fbx(filepath=src)
dest = os.path.join(out_dir, os.path.splitext(os.path.basename(src))[0] + "." + ext)
if ext == "glb":
    bpy.ops.export_scene.gltf(filepath=dest, export_format="GLB")
elif ext == "obj":
    bpy.ops.wm.obj_export(filepath=dest)
elif ext == "stl":
    bpy.ops.wm.stl_export(filepath=dest)
elif ext == "ply":
    bpy.ops.wm.ply_export(filepath=dest)
else:
    bpy.ops.export_scene.fbx(filepath=dest)
'''


def convert_3d(spec):
    """Convert a 3D file inside the home folder (.blend, .glb, .gltf, .obj, .fbx, .stl, .ply) to glb, obj, stl, ply or fbx: "PATH\\tFORMAT". A new file beside the original, never over one. Asks first."""
    path, _, fmt = (spec or "").partition("\t")
    fmt = fmt.strip().lower().lstrip(".")
    full = _home(path)
    if not full or not os.path.isfile(full) or not full.lower().endswith(_IN):
        return f"No 3D file {path.strip()} I am allowed to convert."
    if fmt not in _OUT:
        return f"I can make glb, obj, stl, ply or fbx, not {fmt or 'nothing'}."
    if full.lower().endswith("." + fmt):
        return f"{_short(full)} is already {fmt}."
    out = os.path.splitext(full)[0] + "." + fmt
    if os.path.exists(out):
        return f"{_short(out)} already exists."
    if tools_files.HEADLESS:
        return f"Converted to {_short(out)}."
    exe = _blender()
    if not exe:
        return _NO_BLENDER
    with tempfile.TemporaryDirectory() as tmp:
        script = os.path.join(tmp, "convert.py")
        with open(script, "w") as f:
            f.write(_CONVERT_SCRIPT)
        made_dir = os.path.join(tmp, "out")
        os.makedirs(made_dir)
        try:
            subprocess.run([exe, "-b", "-P", script, "--", full, made_dir, fmt], capture_output=True, timeout=300)
        except (OSError, subprocess.SubprocessError):
            return "Blender did not finish the conversion."
        made = sorted(os.listdir(made_dir))
        if os.path.basename(out) not in made:
            return f"Blender could not convert {_short(full)} to {fmt}."
        beside = [os.path.join(os.path.dirname(full), name) for name in made]
        if any(os.path.exists(b) for b in beside):  # an .obj's .mtl counts too: nothing already there is ever replaced
            return f"{_short(next(b for b in beside if os.path.exists(b)))} already exists."
        for name, dest in zip(made, beside):
            shutil.move(os.path.join(made_dir, name), dest)
    extra = f" (and {', '.join(os.path.basename(b) for b in beside if b != out)})" if len(beside) > 1 else ""
    return f"Converted to {_short(out)}{extra}."


_SHAPES = ("cube", "sphere", "cone", "cylinder", "torus")

# Runs inside Blender: an empty scene, one primitive, exported by the extension of the file asked for.
_MAKE_SCRIPT = '''import bpy, os, sys
shape, out = sys.argv[sys.argv.index("--") + 1:][:2]
bpy.ops.wm.read_factory_settings(use_empty=True)
add = {"cube": bpy.ops.mesh.primitive_cube_add, "sphere": bpy.ops.mesh.primitive_uv_sphere_add, "cone": bpy.ops.mesh.primitive_cone_add,
       "cylinder": bpy.ops.mesh.primitive_cylinder_add, "torus": bpy.ops.mesh.primitive_torus_add}[shape]
add()
ext = out.lower().rsplit(".", 1)[-1]
if ext == "glb":
    bpy.ops.export_scene.gltf(filepath=out, export_format="GLB")
elif ext == "obj":
    bpy.ops.wm.obj_export(filepath=out)
elif ext == "stl":
    bpy.ops.wm.stl_export(filepath=out)
elif ext == "ply":
    bpy.ops.wm.ply_export(filepath=out)
elif ext == "fbx":
    bpy.ops.export_scene.fbx(filepath=out)
else:
    bpy.ops.wm.save_as_mainfile(filepath=out)
'''


def make_3d(spec):
    """Make a simple 3D shape (cube, sphere, cone, cylinder or torus) as a new .glb, .obj, .stl, .ply, .fbx or .blend file inside the home folder: "SHAPE\\tPATH". Never over an existing file. Asks first."""
    shape, _, path = (spec or "").partition("\t")
    shape = shape.strip().lower()
    full = _home(path)
    if shape not in _SHAPES:
        return f"I can make a cube, sphere, cone, cylinder or torus, not {shape or 'nothing'}."
    if not full or not full.lower().endswith(_FORMATS) or not os.path.isdir(os.path.dirname(full)):
        return f"I can only make a {shape} as a .glb, .obj, .stl, .ply, .fbx or .blend file in a folder I am allowed to use."
    if os.path.exists(full):
        return f"{_short(full)} already exists."
    if tools_files.HEADLESS:
        return f"Made a {shape} at {_short(full)}."
    exe = _blender()
    if not exe:
        return _NO_BLENDER
    with tempfile.TemporaryDirectory() as tmp:
        script = os.path.join(tmp, "make.py")
        with open(script, "w") as f:
            f.write(_MAKE_SCRIPT)
        made_dir = os.path.join(tmp, "out")
        os.makedirs(made_dir)
        try:
            subprocess.run([exe, "-b", "-P", script, "--", shape, os.path.join(made_dir, os.path.basename(full))], capture_output=True, timeout=180)
        except (OSError, subprocess.SubprocessError):
            return "Blender did not finish making it."
        made = sorted(os.listdir(made_dir))
        if os.path.basename(full) not in made:
            return f"Blender could not make a {shape}."
        beside = [os.path.join(os.path.dirname(full), name) for name in made]
        if any(os.path.exists(b) for b in beside):  # an .obj's .mtl counts too: nothing already there is ever replaced
            return f"{_short(next(b for b in beside if os.path.exists(b)))} already exists."
        for name, dest in zip(made, beside):
            shutil.move(os.path.join(made_dir, name), dest)
    return f"Made a {shape} at {_short(full)}."


TOOLS = (blender_info, render_blend, convert_3d, make_3d)

_I = re.I
# (pattern, tool name, what to hand it), same shape as tools_files.ROUTES. Only a path ending in a 3D extension or
# .blend matches, so "render my notes" and "inspect the logs" stay with the other tools.
ROUTES = (
    (re.compile(r"^(?:what(?:'s| is) in|inspect) (?:the |my )?(\S+\.(?:blend|glb|gltf|obj|fbx|stl|ply))$", _I), "blender_info", lambda m: m.group(1)),
    (re.compile(r"^render (?:the |my )?(\S+\.blend)$", _I), "render_blend", lambda m: m.group(1)),
    (re.compile(r"^(?:make|create|build) (?:me )?(?:a |an )?(?:3d |3-d )?(cube|sphere|cone|cylinder|torus)(?: (?:at|as|in|to|called|named))? (?:the |my )?(\S+\.(?:blend|glb|gltf|obj|fbx|stl|ply))$", _I), "make_3d", lambda m: m.group(1).lower() + "\t" + m.group(2)),
    (re.compile(r"^convert (?:the |my )?(\S+\.(?:blend|glb|gltf|obj|fbx|stl|ply)) (?:to|into) (?:a |an )?\.?(glb|obj|stl|ply|fbx)$", _I), "convert_3d", lambda m: m.group(1) + "\t" + m.group(2)),
)


def demo():
    """Self-check: the routes and the headless answer, no Blender run."""
    assert ROUTES[0][0].match("what's in ~/Documents/scene.blend") and ROUTES[0][0].match("inspect ~/x.glb")
    assert ROUTES[1][0].match("render ~/Documents/scene.blend") and not ROUTES[1][0].match("render my notes")
    assert ROUTES[2][0].match("convert ~/a.glb to obj") and not ROUTES[2][0].match("convert cat.png to jpg")
    assert "not" in blender_info("~/.ssh/key.blend") and "allowed" in render_blend("/etc/x.blend") and "allowed" in convert_3d("/etc/x.glb\tobj")
    assert all(f.__doc__ for f in TOOLS)
    print("tools_blender ok")


if __name__ == "__main__":
    demo()
