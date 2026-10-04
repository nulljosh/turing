#!/usr/bin/env python3
"""Train Samantha's picker on a free Kaggle or Colab GPU, on a bigger base than this Mac can train, then merge to one folder.

Paste this file into a Kaggle notebook (GPU on), with hands-data's train.jsonl and valid.jsonl uploaded as a dataset named
samantha-hands. It LoRA-trains the base on the same chat rows the Mac uses (system, user words, assistant tool call), masks the
prompt so only the tool call is learned, merges the adapter into the base and writes OUT as one folder to download.
Steps for the Mac side (convert, score, compare) are in docs/KAGGLE.md. Untested on a real GPU until Joshua runs it.
Settings come from the environment: BASE, DATA, OUT, EPOCHS, MAXLEN. ponytail: plain Trainer, no quantization; a 1.5B fits a 16 GB card."""
import glob
import json
import os


def _found(name, default):
    """The folder under /kaggle/input holding `name`, or default. Mounts move between Kaggle versions, and a notebook without internet must load the base from an attached Kaggle model (qwen-lm/qwen2.5/transformers/1.5b-instruct) instead of Hugging Face."""
    hits = glob.glob(f"/kaggle/input/**/{name}", recursive=True)
    return os.path.dirname(hits[0]) if hits else default


BASE = os.environ.get("BASE") or _found("config.json", "Qwen/Qwen2.5-1.5B-Instruct")
DATA = os.environ.get("DATA") or _found("train.jsonl", "/kaggle/input/samantha-hands")
OUT = os.environ.get("OUT", "/kaggle/working/hands-merged")
EPOCHS = float(os.environ.get("EPOCHS", "2"))
MAXLEN = int(os.environ.get("MAXLEN", "512"))


def mask_prompt(prompt_ids, full_ids):
    """Labels for one row: the prompt tokens are -100 (ignored), the tool call after them is learned. Raises if the prompt is not a prefix."""
    if list(full_ids[:len(prompt_ids)]) != list(prompt_ids):
        raise ValueError("prompt is not a prefix of the full text")
    return [-100] * len(prompt_ids) + list(full_ids[len(prompt_ids):])


def pad_batch(rows, pad_id):
    """Pad a list of {input_ids, labels} dicts to the longest row: input padded with pad_id, labels with -100, mask 0 on padding."""
    width = max(len(r["input_ids"]) for r in rows)
    out = {"input_ids": [], "labels": [], "attention_mask": []}
    for r in rows:
        gap = width - len(r["input_ids"])
        out["input_ids"].append(list(r["input_ids"]) + [pad_id] * gap)
        out["labels"].append(list(r["labels"]) + [-100] * gap)
        out["attention_mask"].append([1] * len(r["input_ids"]) + [0] * gap)
    return out


def encode(tok, messages):
    """One chat row to {input_ids, labels}, cut to MAXLEN. The prompt is everything up to the assistant turn."""
    prompt = tok.apply_chat_template(messages[:-1], add_generation_prompt=True, tokenize=False)
    full = prompt + messages[-1]["content"] + tok.eos_token
    p, f = tok(prompt, add_special_tokens=False)["input_ids"], tok(full, add_special_tokens=False)["input_ids"]
    return {"input_ids": f[:MAXLEN], "labels": mask_prompt(p, f)[:MAXLEN]}


def load_rows(path, tok):
    """Read a jsonl of {"messages": [...]} rows and encode them, skipping any row that is malformed instead of dying on it."""
    rows = []
    for line in open(path):
        try:
            rows.append(encode(tok, json.loads(line)["messages"]))
        except (ValueError, KeyError, TypeError):
            continue
    return rows


def main():
    """Train, merge and save. Heavy imports live here so the helpers above are testable without torch."""
    import torch
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments

    tok = AutoTokenizer.from_pretrained(BASE)
    tok.pad_token = tok.pad_token or tok.eos_token
    train, valid = load_rows(os.path.join(DATA, "train.jsonl"), tok), load_rows(os.path.join(DATA, "valid.jsonl"), tok)
    print(f"{len(train)} train rows, {len(valid)} valid rows, base {BASE}")
    model = AutoModelForCausalLM.from_pretrained(BASE, torch_dtype=torch.float16, device_map="auto")
    model = get_peft_model(model, LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05, target_modules="all-linear", task_type="CAUSAL_LM"))
    args = TrainingArguments(output_dir="/kaggle/working/run", num_train_epochs=EPOCHS, per_device_train_batch_size=8,
                             gradient_accumulation_steps=2, learning_rate=1e-4, lr_scheduler_type="cosine", warmup_ratio=0.03,
                             fp16=True, logging_steps=25, eval_strategy="epoch", save_strategy="no", report_to=[], remove_unused_columns=False)
    Trainer(model=model, args=args, train_dataset=train, eval_dataset=valid, data_collator=lambda rows: {k: torch.tensor(v) for k, v in pad_batch(rows, tok.pad_token_id).items()}).train()
    merged = model.merge_and_unload()
    merged.save_pretrained(OUT)
    tok.save_pretrained(OUT)
    print("saved", OUT, "- zip it and download")


if __name__ == "__main__":
    main()
