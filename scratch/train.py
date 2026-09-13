"""Train TinyGPT from zero on our own text. Char-level, no borrowed weights."""
import glob, json, time, os
import mlx.core as mx
import mlx.nn as nn
import mlx.optimizers as optim
import numpy as np
from model import TinyGPT

DATA = os.path.expanduser("~/Documents/Code/turing/data/train.jsonl")
OUT = os.path.expanduser("~/Documents/Code/turing/scratch/scratch.log")
CKPT = os.path.expanduser("~/Documents/Code/turing/scratch/ada1-scratch.safetensors")

BLOCK = 128
BATCH = 32
STEPS = 3000
LR = 3e-4


def load_text():
    text = []
    for line in open(DATA):
        text.append(json.loads(line)["text"])
    return "\n".join(text)


def main():
    text = load_text()
    chars = sorted(set(text))
    stoi = {c: i for i, c in enumerate(chars)}
    data = np.array([stoi[c] for c in text], dtype=np.int32)
    n = int(len(data) * 0.9)
    train_data, val_data = data[:n], data[n:]

    model = TinyGPT(vocab_size=len(chars), dim=128, n_layers=4, n_heads=4, max_len=BLOCK)
    mx.eval(model.parameters())
    opt = optim.AdamW(learning_rate=LR)

    def get_batch(d):
        ix = np.random.randint(0, len(d) - BLOCK - 1, BATCH)
        x = mx.array(np.stack([d[i:i+BLOCK] for i in ix]))
        y = mx.array(np.stack([d[i+1:i+BLOCK+1] for i in ix]))
        return x, y

    def loss_fn(model, x, y):
        logits = model(x)
        return nn.losses.cross_entropy(logits.reshape(-1, len(chars)), y.reshape(-1), reduction="mean")

    loss_and_grad = nn.value_and_grad(model, loss_fn)

    log = open(OUT, "w")
    log.write(f"vocab_size={len(chars)} chars, train_chars={len(train_data)}\n")
    t0 = time.time()
    for step in range(1, STEPS + 1):
        x, y = get_batch(train_data)
        loss, grads = loss_and_grad(model, x, y)
        opt.update(model, grads)
        mx.eval(model.parameters(), opt.state)
        if step % 50 == 0:
            vx, vy = get_batch(val_data)
            vloss = loss_fn(model, vx, vy)
            msg = f"step {step}: train_loss {loss.item():.3f} val_loss {vloss.item():.3f} ({time.time()-t0:.0f}s)"
            print(msg)
            log.write(msg + "\n")
            log.flush()

    model.save_weights(CKPT)
    with open(os.path.expanduser("~/Documents/Code/turing/scratch/vocab.json"), "w") as f:
        json.dump(chars, f)
    log.write("done\n")


if __name__ == "__main__":
    main()
