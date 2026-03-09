#!/usr/bin/env bash
set -euo pipefail

# One-click AppImage build for zcrazy.
# This script assumes it is run from the repository root.

APP_NAME="zcrazy"
SPEC_FILE="zcrazy.spec"
APPDIR="AppDir"
ICON_PNG="$APPDIR/${APP_NAME}.png"
DESKTOP_FILE="$APPDIR/${APP_NAME}.desktop"
RUNTIME_FILE="runtime-x86_64"
APPIMAGETOOL="appimagetool-x86_64.AppImage"
LINUXDEPLOY="linuxdeploy-x86_64.AppImage"
DIST_BIN="dist/${APP_NAME}"
OUT_APPIMAGE="${APP_NAME}-x86_64.AppImage"

if [[ ! -f "$SPEC_FILE" ]]; then
  echo "[ERROR] Missing $SPEC_FILE in current directory: $PWD"
  exit 1
fi

if [[ ! -f "$LINUXDEPLOY" ]]; then
  echo "[ERROR] Missing $LINUXDEPLOY in current directory."
  echo "Download: https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage"
  exit 1
fi

chmod +x "$LINUXDEPLOY"

echo "[1/7] Building PyInstaller binary..."
pyinstaller --noconfirm --clean "$SPEC_FILE"

if [[ ! -f "$DIST_BIN" ]]; then
  echo "[ERROR] Expected binary not found: $DIST_BIN"
  exit 1
fi

echo "[2/7] Preparing AppDir structure..."
mkdir -p "$APPDIR/usr/bin"
cp "$DIST_BIN" "$APPDIR/usr/bin/$APP_NAME"

echo "[3/7] Creating desktop entry..."
cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Type=Application
Name=$APP_NAME
Exec=$APP_NAME
Icon=$APP_NAME
Categories=Utility;
EOF

echo "[4/7] Ensuring valid PNG icon..."
if [[ ! -f "$ICON_PNG" ]]; then
  # Create a simple fallback icon with PyQt6, available in the project environment.
  python - << 'PY'
from PyQt6.QtGui import QImage, QColor
img = QImage(256, 256, QImage.Format.Format_ARGB32)
img.fill(QColor(30, 144, 255))
img.save('AppDir/zcrazy.png', 'PNG')
PY
fi

echo "[5/7] Running linuxdeploy to populate AppDir..."
"./$LINUXDEPLOY" --appdir "$APPDIR" -d "$DESKTOP_FILE" -i "$ICON_PNG"

echo "[6/7] Preparing appimagetool and runtime..."
if [[ ! -f "$RUNTIME_FILE" ]]; then
  curl -L --fail -o "$RUNTIME_FILE" \
    https://github.com/AppImage/type2-runtime/releases/download/continuous/runtime-x86_64
fi
if [[ ! -f "$APPIMAGETOOL" ]]; then
  curl -L --fail -o "$APPIMAGETOOL" \
    https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage
fi
chmod +x "$RUNTIME_FILE" "$APPIMAGETOOL"

echo "[7/7] Building final AppImage..."
"./$APPIMAGETOOL" --runtime-file "$RUNTIME_FILE" "$APPDIR" "$OUT_APPIMAGE"

ls -lh "$OUT_APPIMAGE"
echo "[DONE] AppImage generated: $OUT_APPIMAGE"
