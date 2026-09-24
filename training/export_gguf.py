#!/usr/bin/env python3
"""Export the hands picker to GGUF so Windows and Linux can run her without MLX.

MLX only runs on Apple Silicon, so this is the second inference backend:
GGUF plus llama.cpp/Ollama, not a recompile of the Mac path. Three steps,
same shape mlx_lm ships:

1. `mlx_lm.fuse --dequantize` merges hands-adapter into the 4-bit base and
   writes full HF safetensors (fp16). Fusing first, then dequantizing, keeps
   the LoRA math exact; dequantizing the 4-bit base alone would not.
2. mlx_lm's own `--export-gguf` does not support Qwen2 yet (raises
   "Model type qwen2 not supported"), so this hands the fused HF folder to
   llama.cpp's convert_hf_to_gguf.py instead, quantized straight to Q8_0.
3. Older mlx-community tokenizer_config.json files carry a list-shaped
   `extra_special_tokens`; recent transformers expects a dict there and
   throws on load. Harmless field for a tool-picker prompt with no vision
   tokens, so this drops it before conversion.

Needs, once: `pip install gguf` and a llama.cpp checkout (for
convert_hf_to_gguf.py) somewhere OUTSIDE this repo, e.g.
/private/tmp/claude-loop/llama.cpp (git clone --depth 1
https://github.com/ggml-org/llama.cpp). Point --llama-cpp at it if it lives
elsewhere.

Run: python3 training/export_gguf.py [--llama-cpp PATH] [--adapter hands-adapter]
Output: models/samantha-hands.gguf (gitignored, a few hundred MB, Q8_0)
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_MODEL = "mlx-community/Qwen2.5-0.5B-Instruct-4bit"


def main():
    """Fuse hands-adapter into the base model, dequantize, then convert to GGUF Q8_0."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter", default="hands-adapter")
    ap.add_argument("--llama-cpp", default="/private/tmp/claude-loop/llama.cpp",
                     help="path to a llama.cpp checkout (for convert_hf_to_gguf.py)")
    ap.add_argument("--work-dir", default="/private/tmp/claude-loop/fused-hands",
                     help="scratch dir for the fused fp16 HF model (not in the repo)")
    ap.add_argument("--out", default=os.path.join(REPO, "models", "samantha-hands.gguf"))
    args = ap.parse_args()

    convert_script = os.path.join(args.llama_cpp, "convert_hf_to_gguf.py")
    if not os.path.isfile(convert_script):
        sys.exit(f"No convert_hf_to_gguf.py at {convert_script}. Clone llama.cpp there first:\n"
                  f"  git clone --depth 1 https://github.com/ggml-org/llama.cpp {args.llama_cpp}")
    try:
        import gguf  # noqa: F401
    except ImportError:
        sys.exit("pip install gguf first (and the packages in "
                  f"{args.llama_cpp}/requirements/requirements-convert_hf_to_gguf.txt)")

    adapter_path = args.adapter if os.path.isabs(args.adapter) else os.path.join(REPO, args.adapter)
    if not os.path.isdir(adapter_path):
        sys.exit(f"No adapter at {adapter_path}")

    print(f"1/3 fusing {adapter_path} into {BASE_MODEL} (dequantized, fp16)...")
    if os.path.isdir(args.work_dir):
        shutil.rmtree(args.work_dir)
    subprocess.run([sys.executable, "-m", "mlx_lm", "fuse",
                     "--model", BASE_MODEL, "--adapter-path", adapter_path,
                     "--save-path", args.work_dir, "--dequantize"], check=True)

    cfg_path = os.path.join(args.work_dir, "tokenizer_config.json")
    cfg = json.load(open(cfg_path))
    if isinstance(cfg.get("extra_special_tokens"), list):
        print("2/3 dropping list-shaped extra_special_tokens (transformers wants a dict here)...")
        del cfg["extra_special_tokens"]
        json.dump(cfg, open(cfg_path, "w"), indent=2)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    print(f"3/3 converting to GGUF Q8_0 at {args.out}...")
    subprocess.run([sys.executable, convert_script, args.work_dir,
                     "--outtype", "q8_0", "--outfile", args.out,
                     "--model-name", "samantha-hands"], check=True)

    size_mb = os.path.getsize(args.out) / 1e6
    print(f"done: {args.out} ({size_mb:.0f} MB)")


if __name__ == "__main__":
    main()
