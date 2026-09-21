"""From-scratch structured tool picker: char transformer, tool head, arg-class head, span head.
Random init, char vocab from our own data, no pretrained anything.
Run: SAMANTHA_HEADLESS=1 ../.venv/bin/python train.py --name exp1 [--aug] [--dim 192 --layers 4 --minutes 15]
"""
import json, os, sys, time, random, math
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
os.environ["SAMANTHA_HEADLESS"] = "1"
sys.path[:0] = [REPO, os.path.join(REPO, "eval")]
import numpy as np
import mlx.core as mx
import mlx.nn as nn
import mlx.optimizers as optim

MAXLEN = 128


def flag(n, d=None):
    return type(d)(sys.argv[sys.argv.index(n) + 1]) if n in sys.argv and d is not None else (sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d)


class Block(nn.Module):
    def __init__(self, d, h):
        super().__init__()
        self.ln1, self.ln2 = nn.LayerNorm(d), nn.LayerNorm(d)
        self.attn = nn.MultiHeadAttention(d, h)
        self.mlp = nn.Sequential(nn.Linear(d, 4 * d), nn.GELU(), nn.Linear(4 * d, d))

    def __call__(self, x, mask):
        y = self.ln1(x)
        x = x + self.attn(y, y, y, mask=mask)
        return x + self.mlp(self.ln2(x))


class Picker(nn.Module):
    def __init__(self, vocab, n_tool, n_arg, d=192, layers=4, heads=4):
        super().__init__()
        self.emb = nn.Embedding(vocab, d)
        self.pos = nn.Embedding(MAXLEN, d)
        self.blocks = [Block(d, heads) for _ in range(layers)]
        self.ln = nn.LayerNorm(d)
        self.tool = nn.Linear(d, n_tool)
        self.argc = nn.Linear(d, n_arg)
        self.span = nn.Linear(d, 2)

    def __call__(self, ids, pad):
        # ids (B,T); pad (B,T) True where real. Position 0 is a CLS slot.
        x = self.emb(ids) + self.pos(mx.arange(ids.shape[1]))
        mask = mx.where(pad[:, None, None, :], 0.0, -1e9)
        for b in self.blocks:
            x = b(x, mask)
        x = self.ln(x)
        return self.tool(x[:, 0]), self.argc(x[:, 0]), self.span(x)  # span (B,T,2)


def build_vocab(texts):
    chars = sorted({c for t in texts for c in t})
    return {c: i + 2 for i, c in enumerate(chars)}  # 0 pad, 1 unk/cls


def encode(text, vocab):
    ids = [1] + [vocab.get(c, 1) for c in text[:MAXLEN - 1]]
    return ids


def load_rows(aug, seeds, per):
    import gen_hands_data as g
    from actions import CASES
    from basic_questions import CASES as Q
    reserved = {c[0].lower() for c in CASES} | {q[0].lower() for q in Q}
    test = {json.loads(l)["messages"][1]["content"].lower() for l in open(os.path.join(REPO, "hands-data", "test.jsonl"))}
    prompts = {json.loads(l).get("prompt", "").lower() for l in open(os.path.join(REPO, "eval", "prompts.jsonl"))}
    rows = {}
    for s in seeds:
        for t, c in g.build(0, per, s).items():
            k = t.lower().rstrip(".?!")
            if k in reserved or t.lower() in test or t.lower() in prompts:
                continue
            rows[t] = json.loads(c)
    out = list(rows.items())
    if aug:
        r = random.Random(5)
        extra = []
        for t, c in out:
            x = r.random()
            if x < .15: extra.append((t.lower(), c))
            elif x < .25: extra.append((t.upper() if False else t.capitalize(), c))
            elif x < .35: extra.append((t.rstrip(".?!") , c))
            elif x < .45: extra.append((t + r.choice([".", "!", " please", " thanks", " pls"]), c))
            elif x < .55: extra.append((r.choice(["hey ", "ok ", "so ", "um ", "yo ", "samantha, ", "hey samantha "]) + t, c))
            elif x < .62 and len(t) > 6:  # a typo: drop or swap one inner char (only if arg not touched)
                i = r.randrange(1, len(t) - 2)
                if not c["arg"] or t.lower().find(c["arg"].lower()) == -1 or not (t.lower().find(c["arg"].lower()) <= i <= t.lower().find(c["arg"].lower()) + len(c["arg"])):
                    extra.append((t[:i] + t[i + 1:], c))
        for t, c in extra:
            if c["arg"] and c["arg"].lower() not in t.lower() and not t.lower().startswith(("hey", "ok")):
                pass
            rows.setdefault(t, c)
        out = list(rows.items())
    return out


def make_labels(rows):
    tools = sorted({c["tool"] or "null" for _, c in rows})
    canon = sorted({c["arg"].lower() for t, c in rows if c["arg"] and c["arg"].lower() not in t.lower()})
    argclasses = ["EMPTY", "SPAN"] + ["=" + a for a in canon]
    return tools, argclasses


def label(t, c, tools, argclasses, canonset):
    a = c["arg"]
    tool = tools.index(c["tool"] or "null")
    if not a:
        return tool, 0, -1, -1
    if a.lower() in canonset:
        return tool, argclasses.index("=" + a.lower()), -1, -1
    i = t.lower().find(a.lower())
    if i < 0:
        return tool, 0, -1, -1
    return tool, 1, i + 1, i + len(a)  # +1 for CLS offset


def batchify(items, vocab):
    L = min(MAXLEN, max(len(t) for t, *_ in items) + 1)
    ids = np.zeros((len(items), L), np.int32)
    for i, (t, *_) in enumerate(items):
        e = encode(t, vocab)[:L]
        ids[i, :len(e)] = e
    return ids


def main():
    name = flag("--name", "exp")
    dim, layers, minutes = int(flag("--dim", 192)), int(flag("--layers", 4)), float(flag("--minutes", 12.0))
    per, nseeds = int(flag("--per", 9)), int(flag("--seeds", 1))
    aug = "--aug" in sys.argv
    rows = load_rows(aug, list(range(7, 7 + nseeds)), per)
    print("train rows", len(rows), flush=True)
    vocab = build_vocab([t for t, _ in rows])
    tools, argclasses = make_labels(rows)
    canonset = {a[1:] for a in argclasses[2:]}
    # allowed arg classes per tool, learned from train only
    allowed = {}
    labs = [label(t, c, tools, argclasses, canonset) for t, c in rows]
    for (tl, ac, _, _) in labs:
        allowed.setdefault(tools[tl], set()).add(ac)
    T = np.array([[l[0], l[1], l[2], l[3]] for l in labs], np.int32)
    ids_all = batchify(rows, vocab)
    if ids_all.shape[1] < MAXLEN:
        ids_all = np.pad(ids_all, ((0, 0), (0, MAXLEN - ids_all.shape[1])))
    ids_all = ids_all[:, :MAXLEN]
    mx.random.seed(0)
    model = Picker(len(vocab) + 2, len(tools), len(argclasses), dim, layers, 4)
    nparams = sum(v.size for _, v in nn.utils.tree_flatten(model.parameters()))
    print("params", nparams, "tools", len(tools), "argclasses", len(argclasses), flush=True)
    bs = 64
    steps_per_epoch = len(rows) // bs
    opt = optim.AdamW(learning_rate=optim.cosine_decay(1e-3, 1), weight_decay=0.01)

    def loss_fn(m, ids, y):
        pad = ids > 0
        lt, la, sp = m(ids, pad)
        l = nn.losses.cross_entropy(lt, y[:, 0]).mean() + nn.losses.cross_entropy(la, y[:, 1]).mean()
        sp = mx.where(pad[:, :, None], sp, -1e9)
        has = (y[:, 2] >= 0).astype(mx.float32)
        ys, ye = mx.maximum(y[:, 2], 0), mx.maximum(y[:, 3], 0)
        ls = nn.losses.cross_entropy(sp[:, :, 0], ys) + nn.losses.cross_entropy(sp[:, :, 1], ye)
        return l + (ls * has).sum() / mx.maximum(has.sum(), 1)

    vg = nn.value_and_grad(model, loss_fn)
    t0 = time.time()
    # time-budgeted schedule: lr follows elapsed fraction
    budget = minutes * 60
    step, rng = 0, np.random.default_rng(0)
    done = False
    while not done:
        perm = rng.permutation(len(rows))
        for i in range(steps_per_epoch):
            frac = (time.time() - t0) / budget
            if frac >= 1:
                done = True
                break
            lr = 1e-3 * min(1, step / 200) * (0.5 * (1 + math.cos(math.pi * frac)) * 0.98 + 0.02)
            opt.learning_rate = lr
            idx = perm[i * bs:(i + 1) * bs]
            loss, grads = vg(model, mx.array(ids_all[idx]), mx.array(T[idx]))
            opt.update(model, grads)
            mx.eval(model.parameters(), opt.state, loss)
            step += 1
            if step % 200 == 0:
                print(f"step {step} ep {step / steps_per_epoch:.1f} loss {loss.item():.4f} {time.time() - t0:.0f}s", flush=True)
    mins = (time.time() - t0) / 60
    out = os.path.join(HERE, name)
    os.makedirs(out, exist_ok=True)
    model.save_weights(os.path.join(out, "weights.npz"))
    json.dump({"vocab": vocab, "tools": tools, "argclasses": argclasses, "allowed": {k: sorted(v) for k, v in allowed.items()},
               "dim": dim, "layers": layers, "params": nparams, "train_minutes": mins, "rows": len(rows), "steps": step},
              open(os.path.join(out, "meta.json"), "w"))
    print(f"done {mins:.1f} min, {step} steps", flush=True)


if __name__ == "__main__":
    main()
