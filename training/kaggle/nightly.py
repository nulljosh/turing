"""Train forever on Kaggle, no Claude and no Mac: run by .github/workflows/train.yml every few hours.

Each run: if the Kaggle kernel is still busy, do nothing. Otherwise read the finished run's log, append one line to
eval/kaggle-nightly.log (when it ran, base, seed, the in-kernel SFT and DPO scores), then push the next round with
the next base and seed in the rotation. Kaggle's free GPU quota (about 30 hours a week) is the only limit; a run
that hits it errors out and is logged like any other.

The scores are the kernel's own check on 200 held rows: a nightly signal, not a ship decision. Shipping a picker
still means the pooled dev sets, one sealed-set read and a yes from Joshua. Base, seed and data are logged, so any
winning run can be trained again to fetch its weights.

    python3 training/kaggle/nightly.py           # needs KAGGLE_API_TOKEN
    python3 training/kaggle/nightly.py --check   # self-check, no network
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
LOG = os.path.join(ROOT, "eval", "kaggle-nightly.log")
KERNEL = json.load(open(os.path.join(HERE, "kernel-metadata.json")))["id"]
# ponytail: a fixed rotation; add a base here when one earns a slot (Gemma 4 and Granite need more disk to score on the Mac)
BASES = ["Qwen/Qwen3.5-2B", "Qwen/Qwen2.5-1.5B-Instruct", "Qwen/Qwen3.5-0.8B"]


def kaggle(*args):
    """Run the kaggle CLI, return its stdout ('' on failure)."""
    done = subprocess.run(["kaggle", *args], capture_output=True, text=True, timeout=600)
    return done.stdout if done.returncode == 0 else ""


def scores(text):
    """(base, sft, dpo) from a kernel log; any of them None when the run did not get that far."""
    base = re.search(r"base (\S+?)(?:\\n|\"|\s|$)", text)
    sft = re.search(r"SFT picks the right tool on ([\d.]+)%", text)
    dpo = re.search(r"DPO picks the right tool on ([\d.]+)%", text)
    return (base.group(1) if base else None, float(sft.group(1)) if sft else None, float(dpo.group(1)) if dpo else None)


def next_round(lines):
    """(base, seed) for the next run: walk the rotation by how many rounds are logged, a new seed each lap."""
    n = len(lines)
    return BASES[n % len(BASES)], 100 + n


def launch(base, seed):
    """Push kaggle_train.py with this base and seed baked in (a script kernel has no environment of its own)."""
    with tempfile.TemporaryDirectory() as d:
        src = open(os.path.join(ROOT, "training", "kaggle_train.py")).read()
        head = f'import os\nos.environ.setdefault("BASE", "{base}")\nos.environ.setdefault("SEED", "{seed}")\n'
        open(os.path.join(d, "kernel.py"), "w").write(head + src)
        shutil.copy(os.path.join(HERE, "kernel-metadata.json"), d)
        return kaggle("kernels", "push", "-p", d)


def main():
    """Log the finished round, start the next one. Prints one line saying which."""
    status = kaggle("kernels", "status", KERNEL)
    if re.search(r"RUNNING|QUEUED", status):
        return print("busy:", status.strip())
    lines = open(LOG).read().splitlines() if os.path.exists(LOG) else []
    with tempfile.TemporaryDirectory() as d:
        kaggle("kernels", "output", KERNEL, "-p", d, "-o", "--file-pattern", r".*\.log$")
        text = "".join(open(os.path.join(d, f), errors="replace").read() for f in os.listdir(d) if f.endswith(".log"))
    base, sft, dpo = scores(text)
    state = "error" if "ERROR" in status else "complete"
    line = f"{time.strftime('%Y-%m-%d %H:%M', time.gmtime())} {state} base={base} sft={sft} dpo={dpo}"
    lines.append(line)
    with open(LOG, "w") as f:
        f.write("\n".join(lines) + "\n")
    base, seed = next_round(lines)
    print(line)
    print("launched", base, "seed", seed, "->", launch(base, seed).strip()[:120])


def demo():
    """Self-check of the log parsing and the rotation, no network."""
    log = '{"data": "7644 train rows, 80 valid rows, base Qwen/Qwen3.5-2B\\n"}{"data": "SFT picks the right tool on 91.5% of 200 held rows"}'
    assert scores(log) == ("Qwen/Qwen3.5-2B", 91.5, None), scores(log)
    assert scores("nothing") == (None, None, None)
    assert scores("DPO picks the right tool on 92.0%")[2] == 92.0
    assert next_round([]) == (BASES[0], 100) and next_round(["a"] * 4) == (BASES[1], 104)
    print("nightly ok")


if __name__ == "__main__":
    demo() if "--check" in sys.argv else main()
