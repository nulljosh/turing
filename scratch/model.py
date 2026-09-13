"""Ada-1-scratch: a small transformer, trained from zero. No borrowed weights.

Character-level GPT, MLX (Apple Silicon). Deliberately tiny — this won't be
fluent, it's a real working model with genuinely our own parameters, not a
fine-tune of someone else's base.
"""
import mlx.core as mx
import mlx.nn as nn


class Block(nn.Module):
    def __init__(self, dim, n_heads):
        super().__init__()
        self.ln1 = nn.LayerNorm(dim)
        self.attn = nn.MultiHeadAttention(dim, n_heads)
        self.ln2 = nn.LayerNorm(dim)
        self.mlp = nn.Sequential(nn.Linear(dim, 4 * dim), nn.GELU(), nn.Linear(4 * dim, dim))

    def __call__(self, x, mask):
        x = x + self.attn(self.ln1(x), self.ln1(x), self.ln1(x), mask=mask)
        x = x + self.mlp(self.ln2(x))
        return x


class TinyGPT(nn.Module):
    def __init__(self, vocab_size, dim=128, n_layers=4, n_heads=4, max_len=256):
        super().__init__()
        self.tok_emb = nn.Embedding(vocab_size, dim)
        self.pos_emb = nn.Embedding(max_len, dim)
        self.blocks = [Block(dim, n_heads) for _ in range(n_layers)]
        self.ln_f = nn.LayerNorm(dim)
        self.head = nn.Linear(dim, vocab_size)
        self.max_len = max_len

    def __call__(self, idx):
        b, t = idx.shape
        pos = mx.arange(t)
        x = self.tok_emb(idx) + self.pos_emb(pos)
        mask = nn.MultiHeadAttention.create_additive_causal_mask(t)
        for block in self.blocks:
            x = block(x, mask)
        x = self.ln_f(x)
        return self.head(x)
