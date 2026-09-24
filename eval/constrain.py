"""Constrained decoding for the tool-name stage of the picker's JSON reply.

The picker replies {"tool": "<name>", "arg": "..."}. A wrong-shaped pick
(a made-up tool name, a typo) is caught after the fact today by the guard
in tools.py. This makes it impossible instead: a token-level trie built
from the tokenizer's own encoding of every real tool name (plus null, for
"not a command") masks the logits for the tool-name tokens only. Once the
trie hits a leaf, the mask turns off and the rest of the JSON (the arg)
generates freely, unconstrained, same as today.

Ships behind a flag: eval/hands.py --constrain. Argument stage untouched.
"""
import mlx.core as mx


def build_trie(tokenizer, tool_names):
    """Tokenize `"<name>"` for every tool plus `null`, and build a trie of token ids."""
    trie = {}
    for name in list(tool_names) + [None]:
        text = "null" if name is None else f'"{name}"'
        ids = tokenizer.encode(text, add_special_tokens=False)
        node = trie
        for tid in ids:
            node = node.setdefault(tid, {})
        node[-1] = True  # leaf marker
    return trie


class ToolNameConstraint:
    """A logits_processor (see mlx_lm.generate) that walks the trie one token at a time.

    Stateful across a single generate() call. Create a fresh instance per prompt.
    """

    def __init__(self, tokenizer, tool_names):
        self.trie = build_trie(tokenizer, tool_names)
        self.node = self.trie
        self.done = False
        self._seen = None  # baseline length set on first call: the prompt (incl. forced prefix), not our choice

    def __call__(self, tokens, logits):
        if self.done:
            return logits
        # tokens is every token seen so far (mlx_lm concatenates prompt + generated on first call).
        # The first call's tokens are the prompt itself, already fixed by us; only tokens after
        # that baseline are the model's own choices, and only those should walk the trie.
        n = tokens.shape[-1] if hasattr(tokens, "shape") else len(tokens)
        if self._seen is None:
            self._seen = n
            allowed = [k for k in self.node.keys() if k != -1]
            mask = mx.full(logits.shape, -float("inf"))
            idx = mx.array(allowed)
            mask[..., idx] = logits[..., idx]
            return mask
        if n > self._seen:
            new_ids = tokens[self._seen:n].tolist() if hasattr(tokens, "tolist") else tokens[self._seen:n]
            for tid in new_ids:
                if tid in self.node:
                    self.node = self.node[tid]
                else:
                    # model stepped off the trie (should not happen once masked); stop constraining
                    self.done = True
                    return logits
                if -1 in self.node:
                    self.done = True
                    return logits
            self._seen = n
        allowed = [k for k in self.node.keys() if k != -1]
        if not allowed:
            self.done = True
            return logits
        mask = mx.full(logits.shape, -float("inf"))
        idx = mx.array(allowed)
        mask[..., idx] = logits[..., idx]
        return mask
