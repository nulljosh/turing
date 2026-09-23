#!/bin/sh
# Builds build/SamanthaGUI.app. PythonPath and ChatPipePath point at this repo's own venv and chat_pipe.py,
# so the app drives the exact same answer chain as the terminal, one process, kept warm for the whole session.
set -e
cd "$(dirname "$0")"
APP=build/SamanthaGUI.app
rm -rf "$APP" && mkdir -p "$APP/Contents/MacOS"
swiftc -O -parse-as-library SamanthaGUI.swift -o "$APP/Contents/MacOS/SamanthaGUI"
cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleIdentifier</key><string>com.heyitsmejosh.samantha.gui</string>
<key>CFBundleName</key><string>Samantha</string>
<key>CFBundleExecutable</key><string>SamanthaGUI</string>
<key>CFBundlePackageType</key><string>APPL</string>
<key>CFBundleShortVersionString</key><string>1.0</string>
<key>LSMinimumSystemVersion</key><string>13.0</string>
<key>PythonPath</key><string>$(cd .. && pwd)/.venv/bin/python</string>
<key>ChatPipePath</key><string>$(cd .. && pwd)/chat_pipe.py</string>
</dict></plist>
PLIST
codesign --force --sign - "$APP" >/dev/null 2>&1 || true
"$APP/Contents/MacOS/SamanthaGUI" --check
echo "built $APP"
