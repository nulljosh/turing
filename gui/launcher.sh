#!/bin/sh
# The app's first-run setup: finds or creates Samantha's own Python env in Application Support
# (never inside the .app bundle, so Gatekeeper's read-only mount is never a problem), installs
# requirements.txt into it once, then hands off to chat_pipe.py over stdin/stdout.
#
# Model weights (the Qwen base model and Whisper) are not fetched here: mlx-lm and mlx-whisper
# pull and cache them from HuggingFace the same way the terminal's chat.py already does, lazily,
# the first time a question or a recording actually needs one.
#
# --check creates/verifies the env and exits without installing requirements or starting her, so
# this logic can be unit tested with no network and no Xcode (tests/test_launcher.py, mocked HOME).
set -e

: "${HOME:?HOME must be set}"
RESOURCES="$(cd "$(dirname "$0")" && pwd)"
APPSUP="$HOME/Library/Application Support/Samantha"
VENV="$APPSUP/venv"
CHECK=0
[ "$1" = "--check" ] && CHECK=1

if [ ! -x "$VENV/bin/python3" ]; then
    echo '{"working": "Setting up Samantha, about two minutes..."}'
    mkdir -p "$APPSUP"
    python3 -m venv "$VENV"
    if [ "$CHECK" -eq 0 ]; then
        "$VENV/bin/pip" install --quiet --disable-pip-version-check -r "$RESOURCES/app/requirements.txt"
    fi
fi

if [ "$CHECK" -eq 1 ]; then
    echo "launcher ok"
    exit 0
fi

exec "$VENV/bin/python3" -u "$RESOURCES/app/chat_pipe.py"
