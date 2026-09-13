# Troubleshooting

## MLX memory crashes on long runs

Ran into this training the Qwen3.5-0.8B comparison base, worth knowing if you hit it too. Two distinct failure modes, easy to confuse:

**1. Straightforward OOM at startup.** Free system RAM too low before you even start (check with `vm_stat`, or just `top`). Fix: close other memory-heavy apps, or lower `--batch-size` and `--max-seq-length`, or add `--grad-checkpoint`. Standard stuff.

**2. Metal cache growing unbounded across iterations.** This one's sneakier: training starts fine, memory looks healthy, then climbs steadily iteration over iteration until it OOMs mid-run, even with `--batch-size 1` and `--grad-checkpoint` already set. This happened to us three times before we found the cause. MLX's lazy-eval graph caches intermediate Metal buffers and doesn't automatically release them fast enough during a long training loop on a memory-constrained machine. It's not a bug in `mlx_lm.lora`, it's a real gap between "how MLX's cache is meant to behave" (release under pressure) and "how it actually behaves during a tight sustained loop" on a machine this small.

**Fix:** cap the cache explicitly with `mx.set_cache_limit()` before training starts. `run_lora_capped.py` in this repo does exactly that:

```python
import mlx.core as mx
mx.set_cache_limit(512 * 1024 * 1024)   # 512MB cache cap
mx.set_memory_limit(4 * 1024 * 1024 * 1024)  # 4GB hard working-set ceiling
from mlx_lm.lora import main
main()
```

It imports `mlx_lm.lora`'s own `main()` unmodified, just sets the caps first. No patch to the `mlx-lm` package itself, so it survives `pip install --upgrade mlx-lm` with zero maintenance. If you don't have this problem (more RAM, smaller model), the caps are cheap insurance, not a real cost.

For long unattended runs, use `train_resilient.sh` instead of calling `run_lora_capped.py` directly, it wraps the same thing with auto-restart-on-crash (with backoff), a memory check before each attempt, and resumes from the last checkpoint instead of starting over:

```
./train_resilient.sh mlx-community/Qwen2.5-0.5B-Instruct-4bit ./ada-1-adapter 500
```

Still no daemon, no cron. You run it and it exits when done or out of retries.

## Training data dominated by the wrong subject

If eval scores look bad and the model answers in a completely different project's voice (README badges, unrelated app names, iOS build statuses), check `prep_data.py`'s source weighting. Globbing the whole fleet with no cap means this repo's own facts become a tiny minority of the training data, and the model learns "generic fleet README voice" instead of anything specific to this project. Fix: oversample this repo's own docs, cap how much of the wider fleet gets pulled in. See `roadmap.md`'s progress log, run 3, for the concrete example.
