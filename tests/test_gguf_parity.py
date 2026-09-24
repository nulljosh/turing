"""Does the GGUF backend pick the same tool as MLX for the same 20 commands?

eval/gguf_fixture.json freezes what the MLX picker (hands-adapter, this Mac)
answered for 20 cases pulled from eval/actions.py, so CI on Linux can check
the GGUF/llama-cpp-python backend against a real Mac answer without needing
MLX at all. Skips cleanly, with a printed reason, when the pieces aren't
there: llama-cpp-python not installed, or models/samantha-hands.gguf absent
(it's gitignored, built locally by training/export_gguf.py).

Run: SAMANTHA_HEADLESS=1 python3 tests/test_gguf_parity.py
"""
import json
import os
import sys

os.environ["SAMANTHA_HEADLESS"] = "1"
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

GGUF = os.path.join(REPO, "models", "samantha-hands.gguf")
FIXTURE = os.path.join(REPO, "eval", "gguf_fixture.json")


def main():
    """Compare the llama-cpp-python/GGUF backend's picks against the frozen MLX fixture."""
    if not os.path.isfile(GGUF):
        print(f"SKIP: {GGUF} not built (gitignored; run training/export_gguf.py on a Mac with the adapter)")
        return
    try:
        import llama_cpp  # noqa: F401
    except ImportError:
        print("SKIP: llama-cpp-python not installed (pip install llama-cpp-python)")
        return

    from tools_agent import HANDS_SYSTEM, _generate_hands
    from llama_cpp import Llama
    import re

    model = Llama(model_path=GGUF, n_ctx=512, n_gpu_layers=0, verbose=False)
    cases = json.load(open(FIXTURE))
    agree, total = 0, len(cases)
    for c in cases:
        raw = _generate_hands("llama_cpp", model, None, c["cmd"])
        m = re.search(r"\{.*?\}", raw, re.S)
        got = json.loads(m.group(0)) if m else {}
        ok = got.get("tool") == c["tool"] and str(got.get("arg") or "").strip() == c["arg"]
        agree += ok
        if not ok:
            print(f"  DIFF {c['cmd']!r}: mlx picked {c['tool']}({c['arg']!r}), gguf picked {got.get('tool')}({got.get('arg')!r})")
    print(f"{agree}/{total} passed")
    if agree < total:
        sys.exit(1)


if __name__ == "__main__":
    main()
