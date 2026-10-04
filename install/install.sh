#!/bin/sh
# Samantha on Linux (and any Mac without Apple silicon): one command.
#   curl -fsSL https://raw.githubusercontent.com/nulljosh/turing/main/install/install.sh | sh
# Puts her in ~/samantha, builds a Python env, downloads her tool picker (a small GGUF) and starts chat.
# The parts that drive your screen and apps stay on the Mac; chat, her tool picker and the portable tools run here.
set -e
DIR="${SAMANTHA_DIR:-$HOME/samantha}"
GGUF_URL="https://github.com/nulljosh/turing/releases/download/portable/samantha-hands.gguf"
command -v python3 >/dev/null || { echo "Samantha needs python3. Install it, then run this again."; exit 1; }
command -v git >/dev/null || { echo "Samantha needs git. Install it, then run this again."; exit 1; }
if [ -d "$DIR/.git" ]; then git -C "$DIR" pull -q; else git clone -q --depth 1 https://github.com/nulljosh/turing "$DIR"; fi
cd "$DIR"
python3 -m venv .venv
./.venv/bin/pip install -q --upgrade pip
# prebuilt CPU wheel first, so no compiler is needed
./.venv/bin/pip install -q llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
mkdir -p models
[ -f models/samantha-hands.gguf ] || curl -fL --progress-bar -o models/samantha-hands.gguf "$GGUF_URL"
echo "Ready. Starting Samantha. Run it again any time with: cd $DIR && ./.venv/bin/python app/chat.py"
exec ./.venv/bin/python app/chat.py
