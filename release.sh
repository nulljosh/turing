#!/bin/sh
# Cut a release: run the checks, bump the version, tag, push, publish on GitHub, deploy the site.
# Usage: ./release.sh 0.8.0 "what shipped, one line"
# Patch for a fix, minor for a new ability, major when she changes shape.
set -e
cd "$(dirname "$0")"
V="$1"; NOTE="$2"
[ -n "$V" ] && [ -n "$NOTE" ] || { echo 'usage: ./release.sh X.Y.Z "what shipped"'; exit 2; }
echo "$V" | grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+$' || { echo "version must look like 1.2.3"; exit 2; }
git rev-parse "v$V" >/dev/null 2>&1 && { echo "v$V already exists"; exit 1; }
# scratch/ holds a weights file git always calls changed. Everything else must be committed.
[ -z "$(git status --porcelain | grep -v ' scratch/')" ] || { echo "commit your work first"; exit 1; }

# Never release on top of a red build. v0.9.0 shipped over five failing runs because nothing looked.
CI=$(gh run list --branch main -L 1 --json status,conclusion -q '.[0] | .status + " " + (.conclusion // "")')
case "$CI" in
  "completed success") ;;
  completed*) echo "CI is red on main ($CI). Fix it first."; exit 1 ;;
  *) echo "CI is still running on main. Wait for it, then release."; exit 1 ;;
esac
./gate.sh --full

echo "$V" > VERSION
python3 stats.py >/dev/null
git add VERSION web/stats.json
git commit -qm "Release v$V: $NOTE"
git tag -a "v$V" -m "$NOTE"
git push -q --follow-tags
gh release create "v$V" --title "v$V" --notes "$NOTE" --generate-notes
npx wrangler deploy 2>&1 | tail -1
echo "released v$V"
