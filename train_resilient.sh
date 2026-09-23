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

# One heavy job at a time: local chat servers keep big models resident (oMLX's 9B, Ollama's reader), which left
# training 2.6GB on 2026-09-22. Unload them first; each reloads on its next question.
for id in $(curl -s -m 3 localhost:8000/v1/models 2>/dev/null | python3 -c "import json,sys; [print(m['id']) for m in json.load(sys.stdin).get('data',[])]" 2>/dev/null); do
  curl -s -m 10 -o /dev/null -X POST "localhost:8000/v1/models/${id}/unload" && log "unloaded ${id} from oMLX"
done
for m in $(curl -s -m 3 localhost:11434/api/ps 2>/dev/null | python3 -c "import json,sys; [print(m['name']) for m in json.load(sys.stdin).get('models',[])]" 2>/dev/null); do
  curl -s -m 10 -o /dev/null localhost:11434/api/generate -d "{\"model\": \"${m}\", \"keep_alive\": 0}" && log "unloaded ${m} from Ollama"
done

attempt=0
while [ "$attempt" -lt "$MAX_RETRIES" ]; do
  attempt=$((attempt + 1))

  # free + inactive + speculative + purgeable: macOS keeps spare memory "inactive" and hands it back at once, so
  # counting only "free" pages refused to start with ~35% of memory available (2026-09-22, six waits, gave up)
  FREE_MB=$(( $(vm_stat | awk '/Pages (free|inactive|speculative|purgeable)/ {gsub("\\.","",$NF); s+=$NF} END {print s}') * 16384 / 1048576 ))
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
