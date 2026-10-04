"""Test the pure helpers in training/kaggle_train.py (no torch needed): prompt masking, padding, and bad-row handling."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "training"))
import kaggle_train as k

assert k.mask_prompt([1, 2], [1, 2, 3, 4]) == [-100, -100, 3, 4]
try:
    k.mask_prompt([1, 9], [1, 2, 3])
    raise SystemExit("mask_prompt accepted a prompt that is not a prefix")
except ValueError:
    pass
b = k.pad_batch([{"input_ids": [5, 6, 7], "labels": [-100, 6, 7]}, {"input_ids": [8], "labels": [8]}], 0)
assert b["input_ids"] == [[5, 6, 7], [8, 0, 0]] and b["labels"] == [[-100, 6, 7], [8, -100, -100]] and b["attention_mask"] == [[1, 1, 1], [1, 0, 0]]


class Tok:
    """A stand-in tokenizer: one token per character, chat template is 'user:...|assistant:'."""
    eos_token = "!"

    def apply_chat_template(self, messages, add_generation_prompt, tokenize):
        """Join message contents and end with the assistant marker."""
        return "|".join(m["content"] for m in messages) + "|assistant:"

    def __call__(self, text, add_special_tokens):
        """One id per character."""
        return {"input_ids": [ord(c) for c in text]}


row = k.encode(Tok(), [{"role": "system", "content": "s"}, {"role": "user", "content": "u"}, {"role": "assistant", "content": "{}"}])
assert row["labels"][-3:] == [ord("{"), ord("}"), ord("!")] and row["labels"][0] == -100
assert abs(k.dpo_logit(-1.0, -2.0, -3.0, -3.0, beta=0.1) - 0.1) < 1e-9  # chosen rose 1 nat over the reference, rejected held
assert k.dpo_logit(-2.0, -2.0, -1.0, -3.0, beta=0.5) < 0  # the policy moved toward the rejected call: negative margin
print("ok")

assert k.parse_tool('{"tool": "weather", "arg": "x"}') == "weather" and k.parse_tool("no pick") is None and k.parse_tool("{bad json}") is None
assert k.parse_tool('{"tool": null, "arg": ""}') is None
