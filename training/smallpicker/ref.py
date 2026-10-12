"""Small picker, Python reference. Hashed word + char-trigram features, linear classifier, integer weights.
Trained on training rows only. The C port in Joshua Tree must match pick() exactly (integer math, no floats).
Usage: ref.py train TRAIN.jsonl OUT.json | ref.py eval WEIGHTS.json"""
import json, sys, glob, re
import numpy as np
B = 2048          # hash buckets
SCALE = 16        # weights are round(w * SCALE) before pruning
PRUNE = 16        # drop weights below this (in SCALE units), the kernel has room for about 40KB
DIV = 4           # then divide and round so every weight fits an int8
OOS = "null"

def fnv(s):
    h = 2166136261
    for c in s.encode():
        h = ((h ^ c) * 16777619) & 0xFFFFFFFF
    return h

def feats(text):
    t = " " + re.sub(r"[^a-z0-9~/._ ]", " ", text.lower()) + " "
    f = set()
    for w in t.split():
        f.add(fnv("w" + w) % B)
    for i in range(len(t) - 2):
        f.add(fnv("c" + t[i:i+3]) % B)
    return sorted(f)

def pick(W, bias, tools, text):
    s = list(bias)
    for h in feats(text):
        row = W[h]
        for k in range(len(s)):
            s[k] += row[k]
    best = max(range(len(s)), key=lambda k: (s[k], -k))
    return tools[best]

def load_train(p):
    X, y = [], []
    for l in open(p):
        m = json.loads(l)["messages"]
        t = json.loads(m[2]["content"])["tool"] or OOS
        X.append(feats(m[1]["content"])); y.append(t)
    return X, y

def fit(p, epochs=12):
    X, y = load_train(p)
    tools = sorted(set(y)); ti = {t: i for i, t in enumerate(tools)}; K = len(tools)
    W = np.zeros((B, K)); b = np.zeros(K)
    lr = 0.5
    rng = np.random.default_rng(0)
    for ep in range(epochs):
        for i in rng.permutation(len(X)):
            f = X[i]; s = b + W[f].sum(0); k = ti[y[i]]
            s2 = s.copy(); s2[k] = -1e9; j = int(s2.argmax())
            if s[k] - s[j] < 1.0:      # margin perceptron
                W[f, k] += lr; W[f, j] -= lr; b[k] += lr; b[j] -= lr
        lr *= 0.8
    return tools, W, b

def quantize(W, b):
    Wi = np.rint(W * SCALE).astype(np.int64)
    Wi = np.where(np.abs(Wi) < PRUNE, 0, Wi)
    Wi = np.rint(Wi / DIV).astype(np.int64)
    bi = np.rint(b * SCALE / DIV).astype(np.int64)
    assert np.abs(Wi).max() <= 127
    return Wi, bi

def train(p, out):
    tools, W, b = fit(p)
    Wi, bi = quantize(W, b)
    json.dump({"tools": tools, "W": Wi.tolist(), "bias": bi.tolist()}, open(out, "w"))
    print("trained", len(tools), "classes,", int((Wi != 0).sum()), "weights")

def evaluate(wp):
    d = json.load(open(wp)); W, bias, tools = d["W"], d["bias"], d["tools"]
    tot = right = 0
    for n in ["", "2", "3", "5", "6", "8", "9", "10", "11"]:
        for l in open(f"eval/heldout{n}.jsonl"):
            r = json.loads(l); tot += 1
            right += pick(W, bias, tools, r["text"]) == (r["tool"] or OOS)
    print(f"pooled dev tool-level: {right}/{tot} right")

if __name__ == "__main__":
    train(sys.argv[2], sys.argv[3]) if sys.argv[1] == "train" else evaluate(sys.argv[2])
