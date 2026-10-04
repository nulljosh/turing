#!/bin/sh
# Refresh her Hugging Face page (trommatic/samantha-hands-gguf): the model card from docs/HF_CARD.md and, with --model, the GGUF too.
# Run after every release; the GGUF only changes when the shipped picker does. Needs `hf auth login` once (a write token).
set -e
cd "$(dirname "$0")/.."
V="$(cat VERSION)"
T="$(mktemp -d)"
sed "s/__VERSION__/$V/" docs/HF_CARD.md > "$T/README.md"
[ "$1" = "--model" ] && cp models/samantha-hands.gguf "$T/samantha-hands.gguf"
env -u HF_TOKEN uvx --from huggingface_hub hf upload trommatic/samantha-hands-gguf "$T" . --commit-message "Turing v$V"
rm -rf "$T"
