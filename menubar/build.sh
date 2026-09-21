#!/bin/sh
# Builds build/PaintBar.app. LSUIElement keeps it out of the Dock. PxmPath points at this repo's painter.
set -e
cd "$(dirname "$0")"
APP=build/PaintBar.app
rm -rf "$APP" && mkdir -p "$APP/Contents/MacOS"
swiftc -O -parse-as-library PaintBar.swift -o "$APP/Contents/MacOS/PaintBar"
cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleIdentifier</key><string>com.heyitsmejosh.samantha.paintbar</string>
<key>CFBundleName</key><string>PaintBar</string>
<key>CFBundleExecutable</key><string>PaintBar</string>
<key>CFBundlePackageType</key><string>APPL</string>
<key>CFBundleShortVersionString</key><string>1.0</string>
<key>LSMinimumSystemVersion</key><string>13.0</string>
<key>LSUIElement</key><true/>
<key>NSAppleEventsUsageDescription</key><string>PaintBar asks Pixelmator Pro to build your painting.</string>
<key>PxmPath</key><string>$(cd .. && pwd)/pixelmator/pxm.py</string>
</dict></plist>
PLIST
codesign --force --sign - "$APP" >/dev/null 2>&1 || true
"$APP/Contents/MacOS/PaintBar" --check
echo "built $APP"
