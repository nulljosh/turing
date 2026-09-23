#!/bin/bash
# Self-healing training loop. Restarts on crash (OOM, Metal error) with
# backoff, resumes from the last saved adapter checkpoint instead of
# starting over, caps retries so a bad config can't crash-loop forever.
# Still no daemon: you run this by hand, it exits when done or out of retries.
#
# Usage: ./train_resilient.sh <model> <adapter-path> <iters> [max_retries]
# DATA=./data/stage picks another folder of train.jsonl + valid.jsonl (default ./data).

set -u
MODEL="${1:?model required}"
ADAPTER="${2:?adapter-path required}"
ITERS="${3:?iters required}"
MAX_RETRIES="${4:-6}"
LOG="${ADAPTER}.resilient.log"
MIN_FREE_MB=500

cd "$(dirname "$0")"

log() { echo "[$(date +%H:%M:%S)] $1" | tee -a "$LOG"; }

attempt=0
while [ "$attempt" -lt "$MAX_RETRIES" ]; do
  attempt=$((attempt + 1))

  FREE_MB=$(( $(vm_stat | awk '/Pages free/ {gsub("\\.","",$3); print $3}') * 16384 / 1048576 ))
  if [ "$FREE_MB" -lt "$MIN_FREE_MB" ]; then
    WAIT=$((attempt * 20))
    log "attempt $attempt: only ${FREE_MB}MB free, waiting ${WAIT}s before trying"
    sleep "$WAIT"
    continue
  fi

  RESUME_FLAG=""
  if [ -f "${ADAPTER}/adapters.safetensors" ]; then
    RESUME_FLAG="--resume-adapter-file ${ADAPTER}/adapters.safetensors"
  fi

  log "attempt $attempt: starting (free=${FREE_MB}MB, resume=${RESUME_FLAG:+yes})"
  ./.venv/bin/python run_lora_capped.py \
    --model "$MODEL" \
    --train --data "${DATA:-./data}" --iters "$ITERS" \
    --grad-checkpoint $RESUME_FLAG \
    --adapter-path "$ADAPTER" \
    >> "$LOG" 2>&1

  CODE=$?
  if [ "$CODE" -eq 0 ]; then
    log "attempt $attempt: finished cleanly"
    exit 0
  fi

  log "attempt $attempt: exited with code $CODE, will retry"
  sleep $((attempt * 10))
done

log "gave up after $MAX_RETRIES attempts"
exit 1
