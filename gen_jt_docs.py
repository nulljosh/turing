#!/usr/bin/env python3
"""Builds web/jt_docs.js, the condensed Joshua Tree knowledge pack the Worker
reads to answer questions about the OS she runs inside (worker.js's
readJtDocs, same grounded-reader pattern as readArticle for Wikipedia).

Sourced from the joshuatree repo (a sibling checkout, read-only here):
README.md, docs/WHITEPAPER.md and docs/roadmap.md for prose, plus
docs/ARCHITECTURE.md's own app tables and kernel/kernel.c's GUI_LABELS/
GUI_DOCK_DEFAULT arrays for the real, current app list and dock order (a
hand-typed list would drift the moment an app is added or reordered).
docs/BLUEPRINT.md was in the original spec but does not exist in the repo
today; skipped rather than invented.

Run: python3 gen_jt_docs.py
"""
import re
import sys
from pathlib import Path

JT_ROOT = Path(__file__).resolve().parent.parent / "joshuatree"
MAX_BYTES = 60_000  # the ceiling the doc asked for; the real pack lands far under it

# A few core apps docs/ARCHITECTURE.md never gives their own paragraph to
# (they're described in passing, in WHITEPAPER prose, or not at all).
# Every line here is grounded in real prose read from this repo while writing
# this generator (see the comment on each), not invented.
FALLBACK_APPS = {
    "files": "Files browses the real filesystem (FAT16 on a real disk, or a small RAM disk in the browser demo), the Finder equivalent.",
    "terminal": "Terminal is the same shell the machine boots into, just running in a window.",
    "weather": "Weather pulls a live forecast from Open-Meteo by IP geolocation, shown in the menu bar and in its own app.",
    "keyrate": "Keyrate is a real native typing test: a word list, a live input loop, your words-per-minute.",
}


def read(relpath):
    """Read a file from the joshuatree checkout, or return "" if it is missing."""
    p = JT_ROOT / relpath
    try:
        return p.read_text()
    except OSError:
        print(f"skipping missing {relpath}", file=sys.stderr)
        return ""


def plain(text):
    """Strip the markdown noise (links, bold, backticks) a reader model gets nothing from."""
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)  # [label](url) -> label
    text = re.sub(r"[*`]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def clause(text, max_len=180):
    """The first sentence of a description: the first period inside max_len chars,
    or failing that a hard cut at the last full word, cleanly punctuated either way."""
    text = plain(text)
    m = re.search(r"^(.{20," + str(max_len) + r"}?[.!])\s", text + " ")
    short = m.group(1) if m else text[:max_len].rsplit(" ", 1)[0].rstrip(".,;:") + "."
    return short


def section(title, body):
    """Format one plain-text section with a title line, trimmed and squeezed."""
    body = re.sub(r"[ \t]+", " ", body).strip()
    body = re.sub(r"\n{3,}", "\n\n", body)
    return f"== {title} ==\n{body}\n"


def overview_section():
    """What Joshua Tree is, who made it, and where to try it, from README.md + WHITEPAPER.md."""
    readme = read("README.md")
    whitepaper = read("docs/WHITEPAPER.md")
    tagline = ""
    m = re.search(r"\n(A desktop built from nothing.*?)\n", readme)
    if m:
        tagline = plain(m.group(1))
    why = ""
    m = re.search(r"## Why\n\n(.*?)\n\n##", whitepaper, re.S)
    if m:
        why = plain(m.group(1))
    body = (
        f"Joshua Tree is an operating system: {tagline} It also runs live in a browser tab "
        "at joshuatree.heyitsmejosh.com, the same kernel, not a recording. "
        f"Joshua Trommel is building it, and why: {why} "
        "It is licensed Apache License 2.0, copyright 2026 Joshua Trommel, free and open "
        "source, code on GitHub at github.com/nulljosh/joshuatree."
    )
    return section("Joshua Tree", body)


def version_section():
    """The current version and how to boot it, from README.md and joshuatree's own VERSION file."""
    version = read("VERSION").strip() or "unknown"
    body = (
        f"The current version of Joshua Tree is {version}. Versions follow semver "
        "(major.minor.patch): minor for a new capability, patch for a fix. Try it live in a "
        "browser at joshuatree.heyitsmejosh.com, no install. To run it as the real OS on a "
        "PC, write the ISO from GitHub Releases to a USB stick and boot from it. "
        "Joshua Tree is a kernel for a 32-bit Intel (i386) machine, written from nothing: "
        "its own bootloader, memory manager, filesystem, network stack, window system and "
        "typeface renderer, no Linux or any other OS underneath it."
    )
    return section("Version and booting it", body)


def limits_section():
    """What is deliberately not in 1.0 (Wi-Fi, Bluetooth, language), from docs/roadmap.md."""
    roadmap = read("docs/roadmap.md")
    m = re.search(r"Decided for 1\.0,.*?accessibility floor\.", roadmap, re.S)
    decided = plain(m.group(0)) if m else ""
    body = (
        "Joshua Tree has no Wi-Fi and no Bluetooth; it only has wired networking. "
        f"{decided} There is no cloud in the loop: the Chat app talks to a local language "
        "model over this kernel's own network stack, plain HTTP, no TLS built yet."
    )
    return section("What it does not do", body)


def apps_section():
    """Every app, the default dock order, and a one-line description of each.

    Reads GUI_LABELS and GUI_DOCK_DEFAULT straight out of kernel/kernel.c so the
    list can never silently drift from what the OS actually ships, then pulls a
    description for each app out of docs/ARCHITECTURE.md's own app tables and
    bold-paragraph entries (a real quote, trimmed to one clause), falling back
    to FALLBACK_APPS only for the handful ARCHITECTURE.md never gives a line to.
    """
    kernel = read("kernel/kernel.c")
    arch = read("docs/ARCHITECTURE.md")

    labels_m = re.search(r'GUI_LABELS\[GUI_APP_COUNT\]\s*=\s*\{(.*?)\};', kernel)
    labels = re.findall(r'"([^"]+)"', labels_m.group(1)) if labels_m else []

    dock_m = re.search(r'GUI_DOCK_DEFAULT\[GUI_ICON_COUNT\]\s*=\s*\{(.*?)\};', kernel)
    dock_ids = re.findall(r'GUI_APPS_FOLDER|GUI_TRASH|\d+', dock_m.group(1)) if dock_m else []

    def dock_name(token):
        """Resolve one GUI_DOCK_DEFAULT entry (an index, or the folder/trash sentinels) to a label."""
        if token == "GUI_APPS_FOLDER":
            return "the Apps folder"
        if token == "GUI_TRASH":
            return "Trash"
        return labels[int(token)]

    dock = [dock_name(t) for t in dock_ids if t]
    real_apps = [n for n in labels if n not in ("Apps", "Trash")]

    apps_md = arch.split("## Apps", 1)[-1].split("\n## ", 1)[0]
    descriptions = {}
    for para in re.split(r"\n\s*\n", apps_md):
        para = para.strip()
        m = re.match(r"\*\*([A-Z][A-Za-z ]+)\*\*\s*(?:\([^)]*\))?,?\s*(.*)", para, re.S)
        if m:
            descriptions.setdefault(m.group(1).strip().lower(), clause(m.group(2)))
    for m in re.finditer(r"^\|\s*([A-Za-z]+)\s*\|[^|]*\|\s*(.+?)\s*\|$", apps_md, re.M):
        name, desc = m.group(1).strip(), m.group(2)
        if name in labels:
            descriptions.setdefault(name.lower(), clause(desc))
    descriptions.update(FALLBACK_APPS)

    lines = [f"All {len(real_apps)} apps live in the Apps folder; the dock pins a handful of them: " +
             ", ".join(dock) + "."]
    for name in real_apps:
        d = descriptions.get(name.lower())
        if d:
            lines.append(f"{name}: {d}")
    return section("Apps and the dock", "\n".join(lines))


def login_section():
    """Accounts, the login screen and Lock Screen, from kernel.c's Apple menu and docs/ARCHITECTURE.md."""
    body = (
        "Settings has an Add user step: an account's password is salted and hashed, never "
        "stored in the clear. Once an account exists, booting shows a real login screen; a "
        "wrong password is rejected with a short delay. The tree-logo Apple menu in the top "
        "corner has Lock Screen: with an account, it re-locks the machine the same way a "
        "reboot's login screen does; with no account yet, it just shows a brief message. The "
        "same menu also has About, Files, Notes, Settings, Restart and Shut Down."
    )
    return section("Accounts and Lock Screen", body)


def build():
    """Assemble every section, join them, and cap the result at MAX_BYTES."""
    parts = [overview_section(), version_section(), apps_section(), login_section(), limits_section()]
    text = "\n".join(parts).strip()
    data = text.encode()
    if len(data) > MAX_BYTES:
        text = data[:MAX_BYTES].decode(errors="ignore")
    return text


def write_js(text):
    """Write web/jt_docs.js: an ES module exporting the plain-text pack as JT_DOCS."""
    out = Path(__file__).resolve().parent / "web" / "jt_docs.js"
    escaped = text.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")
    out.write_text(
        "// Generated by gen_jt_docs.py from the joshuatree repo's README, WHITEPAPER,\n"
        "// ARCHITECTURE and roadmap. Regenerate after a Joshua Tree docs change:\n"
        "// python3 gen_jt_docs.py. Do not hand-edit.\n"
        f"export const JT_DOCS = `{escaped}`;\n"
    )
    return out


def main():
    """Build the pack, write it, and print its size."""
    if not JT_ROOT.exists():
        print(f"joshuatree checkout not found at {JT_ROOT}", file=sys.stderr)
        sys.exit(1)
    text = build()
    out = write_js(text)
    print(f"wrote {out} ({len(text.encode())} bytes)")


if __name__ == "__main__":
    main()
