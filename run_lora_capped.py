"""Run mlx_lm.lora with a hard Metal cache cap so it can't grow unbounded
across iterations and OOM this machine. Same CLI args, just capped.
"""
import sys
import mlx.core as mx

CACHE_LIMIT_BYTES = 512 * 1024 * 1024  # 512MB cache cap, leaves headroom on a tight machine

mx.set_cache_limit(CACHE_LIMIT_BYTES)
mx.set_memory_limit(4 * 1024 * 1024 * 1024)  # hard 4GB working-set ceiling

from mlx_lm.lora import main

if __name__ == "__main__":
    main()
