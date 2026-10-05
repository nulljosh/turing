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
import re


def _found(name, default):
    """The folder under /kaggle/input holding `name`, or default. Mounts move between Kaggle versions, and a notebook without internet must load the base from an attached Kaggle model (qwen-lm/qwen2.5/transformers/1.5b-instruct) instead of Hugging Face."""
    hits = glob.glob(f"/kaggle/input/**/{name}", recursive=True)
    return os.path.dirname(hits[0]) if hits else default


BASE = os.environ.get("BASE") or _found("config.json", "Qwen/Qwen2.5-1.5B-Instruct")
DATA = os.environ.get("DATA") or _found("train.jsonl", "/kaggle/input/samantha-hands")
OUT = os.environ.get("OUT", "/kaggle/working/hands-merged")
EPOCHS = float(os.environ.get("EPOCHS", "2"))
MAXLEN = int(os.environ.get("MAXLEN", "512"))
SCORE_N = int(os.environ.get("SCORE_N", "200"))  # rows scored in-kernel after each stage
BETA = float(os.environ.get("BETA", "0.1"))  # DPO: how far the policy may move from the SFT model on each preference pair


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
    prompt = tok.apply_chat_template(messages[:-1], add_generation_prompt=True, tokenize=False, enable_thinking=False)
    full = prompt + messages[-1]["content"] + tok.eos_token
    p, f = tok(prompt, add_special_tokens=False)["input_ids"], tok(full, add_special_tokens=False)["input_ids"]
    return {"input_ids": f[:MAXLEN], "labels": mask_prompt(p, f)[:MAXLEN]}


def dpo_logit(policy_chosen, ref_chosen, policy_rejected, ref_rejected, beta=BETA):
    """The DPO margin: how much more the policy (than the frozen SFT model) prefers the chosen call over the rejected one, times beta.
    Works on floats and on torch tensors; the loss is -logsigmoid of this."""
    return beta * ((policy_chosen - ref_chosen) - (policy_rejected - ref_rejected))


def parse_tool(raw):
    """The tool name in a model reply (the first {...} object's "tool"), or None when there is no pick or it is not JSON."""
    found = re.search(r"\{.*?\}", raw, re.S)
    try:
        return json.loads(found.group(0)).get("tool") if found else None
    except (ValueError, AttributeError):
        return None


def score_slice(model, tok, rows, torch, n=SCORE_N):
    """Fraction of the first n chat rows whose greedy reply picks the same tool as the row's own answer. A cheap in-kernel stand-in for eval/hands.py, enough to see a collapse before anything is downloaded."""
    model.eval()
    right = total = 0
    for row in rows[:n]:
        msgs = row["messages"]
        want = parse_tool(msgs[-1]["content"])
        ids = tok(tok.apply_chat_template(msgs[:-1], add_generation_prompt=True, tokenize=False, enable_thinking=False), add_special_tokens=False, return_tensors="pt")["input_ids"].to(model.device)
        with torch.no_grad():
            out = model.generate(ids, max_new_tokens=48, do_sample=False, pad_token_id=tok.pad_token_id)
        right, total = right + (parse_tool(tok.decode(out[0][ids.shape[1]:], skip_special_tokens=True)) == want), total + 1
    return right / max(total, 1)


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
    import sys
    import torch
    if not torch.cuda.is_available():
        sys.exit("No GPU. On Kaggle: verify your phone in Settings, then Accelerator: GPU T4 x2.")
    # Kaggle's image ships a torchao too old for its own peft, and peft refuses to load; hiding it makes peft skip it.
    sys.modules.setdefault("torchao", None)
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments

    tok = AutoTokenizer.from_pretrained(BASE)
    tok.pad_token = tok.pad_token or tok.eos_token
    train, valid = load_rows(os.path.join(DATA, "train.jsonl"), tok), load_rows(os.path.join(DATA, "valid.jsonl"), tok)
    print(f"{len(train)} train rows, {len(valid)} valid rows, base {BASE}")
    model = AutoModelForCausalLM.from_pretrained(BASE, torch_dtype=torch.float16, device_map="auto")
    model = get_peft_model(model, LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05, target_modules="all-linear", task_type="CAUSAL_LM"))
    args = TrainingArguments(output_dir="/kaggle/working/run", num_train_epochs=EPOCHS, per_device_train_batch_size=8,
                             gradient_accumulation_steps=2, learning_rate=1e-4, lr_scheduler_type="cosine", warmup_steps=30,
                             fp16=True, logging_steps=25, eval_strategy="epoch", save_strategy="no", report_to=[], remove_unused_columns=False)
    Trainer(model=model, args=args, train_dataset=train, eval_dataset=valid, data_collator=lambda rows: {k: torch.tensor(v) for k, v in pad_batch(rows, tok.pad_token_id).items()}).train()
    merged = model.merge_and_unload()
    pairs_path = os.path.join(DATA, "pairs.jsonl")
    held = [json.loads(line) for line in open(os.path.join(DATA, "test.jsonl" if os.path.exists(os.path.join(DATA, "test.jsonl")) else "valid.jsonl"))]
    sft_score = score_slice(merged, tok, held, torch)
    print(f"SFT picks the right tool on {sft_score:.1%} of {min(SCORE_N, len(held))} held rows", flush=True)
    if os.path.exists(pairs_path):  # round twenty-eight: teacher preference pairs, "this call, not that one"
        merged.save_pretrained(OUT + "-sft")  # the SFT-only model, kept so a bad DPO stage costs nothing
        tok.save_pretrained(OUT + "-sft")
        sft_state = {k: v.detach().clone().cpu() for k, v in merged.state_dict().items()}
        merged = dpo_stage(merged, tok, [json.loads(line) for line in open(pairs_path)], torch, get_peft_model, LoraConfig)
        dpo_score = score_slice(merged, tok, held, torch)
        print(f"DPO picks the right tool on {dpo_score:.1%}", flush=True)
        if dpo_score < sft_score:  # round twenty-eight collapsed to abstaining (151/1960): never ship a DPO that scores worse
            print("DPO scored worse than SFT, shipping the SFT model", flush=True)
            merged.load_state_dict(sft_state)
    merged.save_pretrained(OUT)
    tok.save_pretrained(OUT)
    print("saved", OUT, "- zip it and download")


def dpo_stage(model, tok, pairs, torch, get_peft_model, LoraConfig, epochs=1, lr=5e-6):
    """DPO on {"messages": [system, user], "chosen": call, "rejected": call} pairs with a fresh LoRA on the SFT model.
    The SFT model itself is the reference: its log-probs come from the same weights with the adapter switched off."""
    model = get_peft_model(model, LoraConfig(r=16, lora_alpha=32, lora_dropout=0.0, target_modules="all-linear", task_type="CAUSAL_LM"))
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=lr)

    def logprob(messages, completion):
        """Sum of the completion's token log-probs after the prompt."""
        enc = encode(tok, messages + [{"role": "assistant", "content": completion}])
        ids = torch.tensor([enc["input_ids"]], device=model.device)
        labels = torch.tensor([enc["labels"]], device=model.device)[:, 1:]
        logits = model(ids).logits[:, :-1].float()
        mask = labels != -100
        lp = torch.log_softmax(logits, -1).gather(-1, labels.clamp(min=0).unsqueeze(-1)).squeeze(-1)
        return (lp * mask).sum()

    with torch.no_grad(), model.disable_adapter():
        refs = [(logprob(p["messages"], p["chosen"]).item(), logprob(p["messages"], p["rejected"]).item()) for p in pairs]
    model.train()
    for epoch in range(epochs):
        total, won = 0.0, 0
        for p, (rc, rr) in zip(pairs, refs):
            margin = dpo_logit(logprob(p["messages"], p["chosen"]), rc, logprob(p["messages"], p["rejected"]), rr)
            loss = -torch.nn.functional.logsigmoid(margin)
            loss.backward()
            opt.step()
            opt.zero_grad()
            total, won = total + loss.item(), won + (margin.item() > 0)
        print(f"dpo epoch {epoch + 1}: loss {total / len(pairs):.4f}, prefers chosen on {won}/{len(pairs)}", flush=True)
    return model.merge_and_unload()


if __name__ == "__main__":
    main()
