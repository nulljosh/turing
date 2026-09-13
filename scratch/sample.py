import json, os
import mlx.core as mx
from model import TinyGPT

D = os.path.dirname(__file__)
chars = json.load(open(f"{D}/vocab.json"))
stoi = {c: i for i, c in enumerate(chars)}
itos = {i: c for i, c in enumerate(chars)}

model = TinyGPT(vocab_size=len(chars), dim=128, n_layers=4, n_heads=4, max_len=128)
model.load_weights(f"{D}/ada1-scratch.safetensors")

prompt = "Turing is"
idx = mx.array([[stoi[c] for c in prompt]])
for _ in range(150):
    logits = model(idx[:, -128:])
    next_id = mx.argmax(logits[:, -1, :], axis=-1)
    idx = mx.concatenate([idx, next_id[:, None]], axis=1)

print("".join(itos[i.item()] for i in idx[0]))
