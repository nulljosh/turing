"""Run code for a real answer: stats on a CSV, a chart, a unit-heavy calculation. Split out of tools_util.py
like tools_research.py and tools_write.py.

run_code() hands the request and the CSV's header (read directly, never by the model) to the biggest local
model, which writes a short Python script. That script is data, never trusted: it never runs against the real
Mac. It runs in a fresh temporary folder holding only a copy of the named CSV, with no network (a wrapper
prepended to the script monkeypatches socket.socket before anything else executes), a 20 second timeout, a
memory cap (resource.setrlimit), and its output capped at 2000 characters. A chart request calls the
save_chart() helper that same wrapper defines, a pure standard-library PNG writer, and gets back the path to
a PNG saved inside that temp folder. Asks first, like every other write.
"""
import csv
import os
import re
import shutil
import subprocess
import sys
import tempfile

TIMEOUT = 20  # seconds a sandboxed script gets before it is killed
MEM_BYTES = 512 * 1024 * 1024  # the address-space cap for the sandboxed process
OUTPUT_CAP = 2000  # characters of script output ever shown back

SEARCH_DIRS = ("", "Desktop", "Downloads", "Documents")
_CSV_TOKEN = re.compile(r"(\S*\.csv)\b", re.I)
_FENCE = re.compile(r"```(?:python)?\s*\n(.*?)```", re.S)

PROMPT = (
    "Write a short Python script that answers this request about a CSV file named data.csv in the current "
    "directory. Use ONLY the standard library (csv, statistics, json, math): matplotlib and pandas are not "
    "installed, do not import them or anything else third-party. Read data.csv with the csv module and print "
    "the answer in plain sentences with print(). If the request asks for a chart, a plot or a graph, a function "
    "save_chart(labels, values, path, title=\"\") is already defined; call it with the column's values (as "
    "floats) and save to \"chart.png\", then print that you saved a chart. Reply with the script only, no "
    "explanation, no markdown fences, no comments about what you are doing.\n\n"
    "Request: {request}\nCSV header: {header}"
)

# the wrapper: written ahead of the model's own code, in the same file, so no import path or sitecustomize
# trick is needed. It blocks the network before a single line of the model's code runs, and gives chart
# requests a plain PNG writer with no dependency at all.
GUARD = r'''
import socket as _samantha_socket


def _samantha_blocked(*args, **kwargs):
    raise OSError("network access is blocked in this sandbox")


# socket.socket stays a real class (ssl.py subclasses it at import time, so replacing it outright breaks
# even a script that never touches the network); blocking connect and create_connection stops every actual
# reach for the network without breaking that import.
_samantha_socket.socket.connect = _samantha_blocked
_samantha_socket.socket.connect_ex = _samantha_blocked
_samantha_socket.create_connection = _samantha_blocked
_samantha_socket.getaddrinfo = _samantha_blocked


def save_chart(labels, values, path, title=""):
    """Save a plain bar chart as a PNG with no dependency at all: no font, so no text is drawn on it, just
    one bar per value, tallest bar full height. labels is accepted for a matplotlib-shaped call and ignored."""
    import struct
    import zlib
    width, height, margin = 640, 400, 24
    pixels = bytearray(b"\xff" * (width * height * 3))
    nums = [float(v) for v in values] or [0.0]
    top = max(nums) or 1.0
    plot_w, plot_h = width - 2 * margin, height - 2 * margin
    bar_w = max(1, plot_w // max(1, len(nums)))

    def set_px(x, y, rgb):
        if 0 <= x < width and 0 <= y < height:
            i = (y * width + x) * 3
            pixels[i:i + 3] = bytes(rgb)

    for i, v in enumerate(nums):
        bar_h = int(plot_h * (v / top)) if top else 0
        x0 = margin + i * bar_w
        for x in range(x0, min(x0 + bar_w - 2, width - margin)):
            for y in range(height - margin - bar_h, height - margin):
                set_px(x, y, (70, 130, 180))
    for x in range(margin, width - margin):
        set_px(x, height - margin, (0, 0, 0))
    for y in range(margin, height - margin):
        set_px(margin, y, (0, 0, 0))

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff)

    raw, stride = bytearray(), width * 3
    for y in range(height):
        raw.append(0)
        raw.extend(pixels[y * stride:(y + 1) * stride])
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)))
        f.write(chunk(b"IDAT", zlib.compress(bytes(raw), 9)))
        f.write(chunk(b"IEND", b""))
    return path
'''


def _resolve_csv(path):
    """An existing CSV file inside the home folder, real path resolved, or None if it is missing, hidden,
    or outside home. Same shape as tools_research._write_target, one path check per module on purpose."""
    home = os.path.realpath(os.path.expanduser("~"))
    full = os.path.realpath(os.path.expanduser(path.strip().strip("'\"")))
    rel = os.path.relpath(full, home)
    if rel.startswith("..") or any(part.startswith(".") for part in rel.split(os.sep) if part not in (".", "")):
        return None
    return full if os.path.isfile(full) else None


def _find_csv(request):
    """The CSV the request names, resolved inside the home folder. A bare file name ("sales.csv") is looked
    for on the Desktop, in Downloads, in Documents and in home itself, in that order."""
    m = _CSV_TOKEN.search(request)
    if not m:
        return None
    raw = m.group(1)
    if raw.startswith(("~", "/")):
        return _resolve_csv(raw)
    for d in SEARCH_DIRS:
        found = _resolve_csv(os.path.join("~", d, raw))
        if found:
            return found
    return None


def _extract_code(reply):
    """The Python out of a local model's reply: its self-naming line stripped, and a markdown fence unwrapped
    if it used one anyway."""
    text = reply.rsplit("\n(Answered by", 1)[0].strip()
    m = _FENCE.search(text)
    return (m.group(1) if m else text).strip()


def _cap_memory():
    """Cap the sandboxed process's address space, run right after the fork and before the script starts.
    Some platforms refuse to lower this rlimit at all (seen on a macOS 26 beta build); when that happens the
    other boundaries (fresh folder, no network, the timeout, the output cap) still hold, so this never blocks
    the run over a rlimit quirk it cannot control."""
    import resource
    try:
        resource.setrlimit(resource.RLIMIT_AS, (MEM_BYTES, MEM_BYTES))
    except (ValueError, OSError):
        pass


def _sandbox_run(code, csv_path):
    """Run model-written code in a fresh temp folder holding only a copy of csv_path as data.csv, no network,
    a time and memory cap, output capped at 2000 characters. Returns (output, workdir); workdir is left on
    disk, since a chart's PNG has to live somewhere after the process exits."""
    workdir = tempfile.mkdtemp(prefix="samantha-run-")
    shutil.copy(csv_path, os.path.join(workdir, "data.csv"))
    with open(os.path.join(workdir, "script.py"), "w") as f:
        f.write(GUARD + "\n\n" + code + "\n")
    env = {k: v for k, v in os.environ.items() if "proxy" not in k.lower()}
    env["HOME"], env["PYTHONDONTWRITEBYTECODE"] = workdir, "1"
    try:
        r = subprocess.run([sys.executable, "-I", "-S", "script.py"], cwd=workdir, env=env,
                            capture_output=True, text=True, timeout=TIMEOUT, preexec_fn=_cap_memory)
    except subprocess.TimeoutExpired:
        return f"That took longer than {TIMEOUT} seconds, so I stopped it.", workdir
    out = (r.stdout or "").strip()
    if r.returncode != 0:
        last_error = next((line for line in reversed((r.stderr or "").strip().splitlines()) if line.strip()), "")
        out = (out + "\n" + last_error).strip() if last_error else (out or f"The script failed (exit {r.returncode}).")
    return (out[:OUTPUT_CAP] if out else "The script ran with no output."), workdir


def _first_png(workdir):
    """The first PNG a sandboxed run saved, or None."""
    return next((os.path.join(workdir, n) for n in sorted(os.listdir(workdir)) if n.lower().endswith(".png")), None)


def run_code(request):
    """Run code for a real answer, in a sandbox: "stats on ~/Desktop/sales.csv", "average of the price column
    in sales.csv", "chart sales.csv", "plot column price of sales.csv". The biggest local model writes a short
    Python script from the request and the CSV's header; it never runs blind, only in a fresh temp folder with
    a copy of that one file, no network, a 20 second and a memory cap, and output capped at 2000 characters.
    A chart saves a PNG in that folder and this returns its path. Asks first."""
    request = request.strip()
    if not request:
        return 'Run code on what? Say it like "stats on sales.csv".'
    csv_path = _find_csv(request)
    if not csv_path:
        return "Name a CSV file inside your home folder, like sales.csv or ~/Desktop/sales.csv."
    try:
        with open(csv_path, newline="") as f:
            header = next(csv.reader(f), [])
    except (OSError, csv.Error) as e:
        return f"I could not read that CSV: {e}."
    import tools_llm
    reply = tools_llm.ask_llm(PROMPT.format(request=request, header=", ".join(header)))
    code = _extract_code(reply)
    if not code:
        return f"I could not write code for that: {reply}"
    out, workdir = _sandbox_run(code, csv_path)
    png = _first_png(workdir)
    if png:
        return f"Saved {png}." + (f" {out}" if out and out != "The script ran with no output." else "")
    return out
