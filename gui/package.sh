#!/bin/sh
# Packages the distributable SamanthaGUI.app: builds the app, bundles a self-contained copy of her
# code plus a first-run launcher (launcher.sh) that creates her own Python env in Application
# Support on first open, signs it, then zips and (when a notary keychain profile exists) submits
# it for notarization and staples the ticket.
#
# Unlike gui/build.sh (a dev build wired straight to this checkout's own .venv, for fast local
# iteration), this is what a stranger downloads: no path on their Mac points back at your repo.
#
# Usage: ./gui/package.sh
# Output: gui/dist/SamanthaGUI.app (signed) and gui/dist/SamanthaGUI.zip (signed, notarized if possible)
set -e
cd "$(dirname "$0")"
ROOT="$(cd .. && pwd)"
DEV_APP=build/SamanthaGUI.app
DIST=dist
APP="$DIST/SamanthaGUI.app"
ZIP="$DIST/SamanthaGUI.zip"

rm -rf "$DIST"
mkdir -p "$DIST"

# Build the binary the usual way first (also proves --check still passes), then repackage it with
# its own Info.plist and its own copy of the source, instead of the dev build's checkout paths.
./build.sh
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources/app"
cp "$DEV_APP/Contents/MacOS/SamanthaGUI" "$APP/Contents/MacOS/SamanthaGUI"

# Only her root-level code (CLAUDE.md's Layout: ask_*, tools_*, chat, harness, serve, mcp_server,
# library, voice) plus requirements.txt. No training/, web/, docs/, tests/, gui/, menubar/, swift/,
# pixelmator/, .git, or the gitignored data/ and ada-1-adapter/ (private, never published; chat_pipe.py's
# answer chain already degrades to her ungrounded voice when the adapter is missing, it never crashes).
for f in "$ROOT"/*.py "$ROOT/requirements.txt"; do
    [ -f "$f" ] && cp "$f" "$APP/Contents/Resources/app/"
done
cp launcher.sh "$APP/Contents/Resources/launcher.sh"
chmod +x "$APP/Contents/Resources/launcher.sh"

cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleIdentifier</key><string>com.heyitsmejosh.samantha.gui</string>
<key>CFBundleName</key><string>Samantha</string>
<key>CFBundleExecutable</key><string>SamanthaGUI</string>
<key>CFBundlePackageType</key><string>APPL</string>
<key>CFBundleShortVersionString</key><string>$(cat "$ROOT/VERSION" 2>/dev/null || echo 1.0)</string>
<key>LSMinimumSystemVersion</key><string>13.0</string>
<key>LauncherScript</key><string>launcher.sh</string>
</dict></plist>
PLIST

# Prefer a real Developer ID Application identity (the only one Gatekeeper will run for a stranger
# with no dev tools installed). Fall back to Apple Development only so this script still produces
# something to inspect locally; that build will NOT open on another Mac without Gatekeeper trouble.
IDENTITY=$(security find-identity -v -p codesigning 2>/dev/null | grep '"Developer ID Application' | head -1 | sed -E 's/.*"(.*)"/\1/')
FALLBACK=0
if [ -z "$IDENTITY" ]; then
    IDENTITY=$(security find-identity -v -p codesigning 2>/dev/null | grep '"Apple Development' | head -1 | sed -E 's/.*"(.*)"/\1/')
    FALLBACK=1
fi
[ -n "$IDENTITY" ] || { echo "no codesigning identity found (security find-identity -v -p codesigning)"; exit 1; }
if [ "$FALLBACK" -eq 1 ]; then
    echo "WARNING: no Developer ID Application identity on this Mac, signing with Apple Development instead: $IDENTITY"
    echo "WARNING: this will not pass Gatekeeper for a stranger. Get a Developer ID Application certificate to ship for real."
fi

codesign --force --deep --options runtime --timestamp --sign "$IDENTITY" "$APP"
codesign --verify --deep --strict "$APP"
echo "signed $APP with: $IDENTITY"

ditto -c -k --keepParent "$APP" "$ZIP"
echo "packaged $ZIP"

# A notarytool keychain profile is stored once, by hand, with `xcrun notarytool store-credentials`;
# there is no API to list profile names, so try the one this project uses before giving up.
PROFILE="samantha-notary"
if xcrun notarytool history --keychain-profile "$PROFILE" >/dev/null 2>&1; then
    xcrun notarytool submit "$ZIP" --keychain-profile "$PROFILE" --wait
    xcrun stapler staple "$APP"
    rm -f "$ZIP"
    ditto -c -k --keepParent "$APP" "$ZIP"
    echo "notarized and stapled $ZIP"
else
    cat <<EOF
No notarytool keychain profile named "$PROFILE" found, so notarization did not run.
Stopping at the signed zip: $ZIP

Joshua, run this once on this Mac to store a profile (an app-specific password from
appleid.apple.com, not your regular Apple ID password):

  xcrun notarytool store-credentials $PROFILE --apple-id <your Apple ID email> --team-id <your Team ID> --password <app-specific password>

Then re-run ./gui/package.sh and it will notarize and staple automatically.
EOF
fi
