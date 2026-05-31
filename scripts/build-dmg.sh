#!/usr/bin/env bash
# Build a downloadable LazyClaude DMG.
#
# Wraps tools/build_macos_app.sh in SELF_CONTAINED mode — the resulting
# LazyClaude.app carries its own project source in Contents/Resources/app, so a
# user who downloads the DMG can run it without cloning the repo. It still relies
# on the system python3 (LazyClaude is stdlib-only); no Python runtime is bundled.
#
# Output: build/LazyClaude-<version>.dmg
#
# Usage:
#   scripts/build-dmg.sh        # or: make dmg
#
# Notes:
#   - hdiutil / sips / iconutil / rsync are all macOS built-ins; no extra deps.
#   - The .app is unsigned. Downloaders must right-click → Open the first time
#     (or run `xattr -dr com.apple.quarantine /Applications/LazyClaude.app`).

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="$(tr -d '[:space:]' < "$ROOT/VERSION")"
BUILD_DIR="$ROOT/build"
STAGE="$BUILD_DIR/dmg-stage"
DMG_OUT="$BUILD_DIR/LazyClaude-$VERSION.dmg"
VOL_NAME="LazyClaude $VERSION"

echo "▶ building DMG for LazyClaude v$VERSION"

# ── 1. clean staging area ───────────────────────────────────────────────────
rm -rf "$STAGE" "$DMG_OUT"
mkdir -p "$STAGE"

# ── 2. build the self-contained .app straight into the staging area ──────────
SELF_CONTAINED=1 APP_OUT="$STAGE" bash "$ROOT/tools/build_macos_app.sh"

if [[ ! -d "$STAGE/LazyClaude.app" ]]; then
  echo "✗ expected $STAGE/LazyClaude.app — build_macos_app.sh did not produce it" >&2
  exit 1
fi

# ── 3. drag-to-install affordance ───────────────────────────────────────────
ln -s /Applications "$STAGE/Applications"

# ── 4. compressed, read-only DMG ────────────────────────────────────────────
hdiutil create \
  -volname "$VOL_NAME" \
  -srcfolder "$STAGE" \
  -fs HFS+ \
  -format UDZO \
  -ov \
  "$DMG_OUT" >/dev/null

# ── 5. summary ──────────────────────────────────────────────────────────────
SIZE="$(du -h "$DMG_OUT" | awk '{print $1}')"
echo "✅ built $DMG_OUT ($SIZE)"
echo "   open the DMG, drag LazyClaude.app to Applications, then right-click → Open"
echo "   (first launch only — the .app is unsigned)"
