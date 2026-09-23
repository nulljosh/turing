"""Parse mlx_lm train.log into status.json (loss history) for the landing page."""
import re, json, os

LOG = os.path.expanduser("~/Documents/Code/turing/ada-1-adapter.resilient.log")
OUT = os.path.expanduser("~/Documents/Code/turing/web/status.json")

train_re = re.compile(r"Iter (\d+): Train loss ([\d.]+)")
val_re = re.compile(r"Iter (\d+): Val loss ([\d.]+)")

def parse():
    """Parse training log and write loss history plus roadmap to web/status.json."""
    text = open(LOG, errors="ignore").read()
    # the resilient wrapper appends every run to the same file and iter numbers
    # restart at 1 each run, only chart the most recent run's segment
    starts = [m.start() for m in re.finditer(r"attempt \d+: starting", text)]
    text = text[starts[-1]:] if starts else text

    train, val = [], []
    for line in text.splitlines():
        for m in train_re.finditer(line):
            train.append({"iter": int(m.group(1)), "loss": float(m.group(2))})
        for m in val_re.finditer(line):
            val.append({"iter": int(m.group(1)), "loss": float(m.group(2))})
    done = "Saved final" in text or "Saving final" in text
    status = {
        "model": "Samantha",
        "project": "Turing",
        "base": "Qwen2.5-0.5B-Instruct-4bit",
        "train_loss": train,
        "val_loss": val,
        "status": "done" if done else ("training" if train else "starting"),
        "roadmap": [
            {"phase": 0, "name": "Pipeline proof", "done": True},
            {"phase": 1, "name": "More data, same model", "done": True},
            {"phase": 2, "name": "Evaluate like it matters", "done": True},
            {"phase": 3, "name": "Bigger base, same recipe", "done": False},
            {"phase": 4, "name": "Retrieval instead of memorization", "done": True},
            {"phase": 5, "name": "Give it a job", "done": False},
            {"phase": 6, "name": "Distillation, not scale", "done": False},
        ],
    }
    json.dump(status, open(OUT, "w"), indent=2)
    print(f"wrote {OUT}: {len(train)} train points, {len(val)} val points, status={status['status']}")

if __name__ == "__main__":
    parse()
