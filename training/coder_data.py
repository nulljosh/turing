"""Her coder's training set: our own code, from every git repo under ~/Documents/Code, as plain text chunks for an
MLX LoRA (mlx_lm lora, {"text": ...} rows). Only files git tracks, only source extensions, no lockfiles, no minified or
generated files, nothing from vault/, _attic/, _external/ or the jt-* worktrees, and any file that looks like it holds
a secret is dropped whole. Files are split by a hash of their path, so a held-out file never reaches training:
about 5 percent valid and 5 percent test.

    python3 training/coder_data.py [OUT_DIR]     # default data/coder: train.jsonl, valid.jsonl, test.jsonl
"""
import hashlib
import json
import os
import re
import subprocess
import sys

ROOT = os.path.expanduser("~/Documents/Code")
EXT = {".py", ".swift", ".js", ".mjs", ".ts", ".html", ".css", ".c", ".h", ".sh", ".rs", ".go", ".kt"}
SKIP_DIRS = re.compile(r"(^|/)(vault|_attic|_external|node_modules|build|dist|vendor|\.venv|third_party)(/|$)")
SKIP_FILES = re.compile(r"(\.min\.(js|css)$|lock|_weights\.h$|_golden\.h$|generated|\.pb\.)", re.I)
SECRET = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY|AKIA[0-9A-Z]{16}|\bsk-[A-Za-z0-9_-]{20,}|\bghp_[A-Za-z0-9]{30,}"
                    r"|\bre_[A-Za-z0-9]{20,}|(?i:(api_?key|secret|token|password)\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,})")
CHUNK = 3000          # characters, about 1,000 tokens: fits --max-seq-length 1024
MAX_FILE = 60000      # a bigger file is almost always data or generated
PER_REPO = 400000     # characters, so one huge repo cannot drown the others


def repos():
    """Every git repo under ROOT (labs itself included), skipping the jt-* worktrees and private folders."""
    out = [ROOT]
    for d in sorted(os.listdir(ROOT)):
        p = os.path.join(ROOT, d)
        if d.startswith(("jt-", ".", "_")) or d == "vault" or not os.path.isdir(os.path.join(p, ".git")):
            continue
        out.append(p)
    return out


def files(repo):
    """Tracked source files in one repo, as (relative path, text)."""
    try:
        names = subprocess.run(["git", "-C", repo, "ls-files"], capture_output=True, text=True, timeout=60).stdout.split("\n")
    except (subprocess.SubprocessError, OSError):
        return []
    for rel in names:
        if os.path.splitext(rel)[1].lower() not in EXT or SKIP_DIRS.search(rel) or SKIP_FILES.search(os.path.basename(rel)):
            continue
        path = os.path.join(repo, rel)
        try:
            if os.path.islink(path) or os.path.getsize(path) > MAX_FILE:
                continue
            text = open(path, encoding="utf-8").read()
        except (OSError, UnicodeDecodeError):
            continue
        if text.strip() and not SECRET.search(text):
            yield rel, text


def chunks(text):
    """Split at line ends into pieces of at most CHUNK characters."""
    out, cur = [], ""
    for line in text.splitlines(keepends=True):
        if cur and len(cur) + len(line) > CHUNK:
            out.append(cur)
            cur = ""
        cur += line[:CHUNK]
    return out + ([cur] if cur.strip() else [])


def split(name):
    """train, valid or test for a file, fixed by its path so reruns agree."""
    h = int(hashlib.sha1(name.encode()).hexdigest(), 16) % 100
    return "test" if h < 5 else "valid" if h < 10 else "train"


def build(out):
    """Write the three jsonl files and print the counts."""
    os.makedirs(out, exist_ok=True)
    rows = {"train": [], "valid": [], "test": []}
    for repo in repos():
        name, used = os.path.basename(repo) if repo != ROOT else "labs", 0
        for rel, text in files(repo):
            if used >= PER_REPO:
                break
            used += len(text)
            for c in chunks(text):
                rows[split(f"{name}/{rel}")].append({"text": f"// file: {name}/{rel}\n{c}"})
    for k, v in rows.items():
        with open(os.path.join(out, f"{k}.jsonl"), "w") as f:
            f.writelines(json.dumps(r) + "\n" for r in v)
    print({k: len(v) for k, v in rows.items()})


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "data/coder")
