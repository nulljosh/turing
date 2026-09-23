"""Run mlx_lm.lora with a hard Metal cache cap so it can't grow unbounded
across iterations and OOM this machine. Same CLI args, just capped.
"""
import shutil
import sys

# 2026-09-21: a run on a disk with 3.7GB free pushed the Mac into swap, swap filled the disk, and every tool on the
# machine stopped, including the shell needed to clean up. Memory pressure lands on the disk. Refuse to start without room.
MIN_FREE_GB = 6
free_gb = shutil.disk_usage("/").free / 1e9
if free_gb < MIN_FREE_GB:
    sys.exit(f"Only {free_gb:.1f}GB free on the internal disk, need {MIN_FREE_GB}. Training swaps, and swap needs room. Free some space first.")

import mlx.core as mx

CACHE_LIMIT_BYTES = 512 * 1024 * 1024  # 512MB cache cap, leaves headroom on a tight machine

mx.set_cache_limit(CACHE_LIMIT_BYTES)
mx.set_memory_limit(4 * 1024 * 1024 * 1024)  # hard 4GB working-set ceiling

from mlx_lm.lora import main

if __name__ == "__main__":
    main()
