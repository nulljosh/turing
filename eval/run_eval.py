"""Run the eval prompts through a given adapter, print results for manual scoring.
Not automated grading, we're at 8 prompts, a human reading the output is faster
and more honest than building an LLM-judge pipeline for this scale.
"""
import json, subprocess, sys, os

D = os.path.dirname(__file__)
PROMPTS = f"{D}/prompts.jsonl"


def main(model, adapter_path):
    prompts = [json.loads(l) for l in open(PROMPTS)]
    for p in prompts:
        out = subprocess.run(
            [
                "../.venv/bin/mlx_lm.generate",
                "--model", model,
                "--adapter-path", adapter_path,
                "--prompt", p["prompt"],
                "--max-tokens", "80",
            ],
            cwd=D,
            capture_output=True, text=True,
        )
        gen = out.stdout.split("==========")[1].strip() if "==========" in out.stdout else out.stdout.strip()
        print(f"PROMPT: {p['prompt']}")
        print(f"EXPECT: {p['expects']}")
        print(f"GOT:    {gen}")
        print("-" * 60)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: run_eval.py <model> <adapter_path>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
