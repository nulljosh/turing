#!/bin/sh
# Builds build/SamanthaGUI.app. PythonPath and ChatPipePath point at this repo's own venv and app/chat_pipe.py,
# so the app drives the exact same answer chain as the terminal, one process, kept warm for the whole session.
set -e
cd "$(dirname "$0")"
APP=build/SamanthaGUI.app
rm -rf "$APP" && mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
# her flower as a Liquid Glass icon (Samantha.icon, made in Icon Composer); actool also writes the .icns older macOS reads
xcrun actool Samantha.icon --compile "$APP/Contents/Resources" --app-icon Samantha --platform macosx --target-device mac \
  --minimum-deployment-target 13.0 --output-partial-info-plist "$APP/Contents/Resources/icon.plist" >/dev/null 2>&1 || echo "no actool: built without her icon"
rm -f "$APP/Contents/Resources/icon.plist"
swiftc -O -parse-as-library SamanthaGUI.swift -o "$APP/Contents/MacOS/SamanthaGUI"
cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleIdentifier</key><string>com.heyitsmejosh.samantha.gui</string>
<key>CFBundleName</key><string>Samantha</string>
<key>CFBundleExecutable</key><string>SamanthaGUI</string>
<key>CFBundlePackageType</key><string>APPL</string>
<key>CFBundleIconFile</key><string>Samantha</string>
<key>CFBundleIconName</key><string>Samantha</string>
<key>CFBundleShortVersionString</key><string>1.0</string>
<key>LSMinimumSystemVersion</key><string>13.0</string>
<key>PythonPath</key><string>$(cd .. && pwd)/.venv/bin/python</string>
<key>ChatPipePath</key><string>$(cd .. && pwd)/app/chat_pipe.py</string>
</dict></plist>
PLIST
codesign --force --sign - "$APP" >/dev/null 2>&1 || true
"$APP/Contents/MacOS/SamanthaGUI" --check
echo "built $APP"
