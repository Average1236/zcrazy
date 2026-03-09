# Packaging Guide

This document describes how to package this project as:
- Linux AppImage
- Windows EXE

## 1. Prerequisites

### Common
- Project root: this folder (`zcrazy`)
- Python environment with project dependencies installed
- `pyinstaller` installed in that environment

### Linux AppImage
- `linuxdeploy-x86_64.AppImage` in project root
- Network access (first run downloads `runtime-x86_64` and `appimagetool-x86_64.AppImage`)

### Windows EXE
- Run on Windows
- Optional icon file: `game_1bpp.ico`

## 2. Linux AppImage (Recommended: one-click script)

### 2.1 Run script

```bash
chmod +x build_appimage.sh
./build_appimage.sh
```

### 2.2 Output

- Final artifact: `zcrazy-x86_64.AppImage`

### 2.3 What the script does

1. Build executable with `pyinstaller --clean zcrazy.spec`
2. Put binary into `AppDir/usr/bin/zcrazy`
3. Generate desktop file `AppDir/zcrazy.desktop`
4. Ensure valid icon `AppDir/zcrazy.png`
5. Run `linuxdeploy` to populate AppDir
6. Download (if missing):
   - `runtime-x86_64`
   - `appimagetool-x86_64.AppImage`
7. Run `appimagetool --runtime-file ...` to create AppImage

### 2.4 Why not `linuxdeploy --output appimage`

In some networks/environments, the appimage plugin fails to download runtime automatically.
This project uses a more stable two-step approach:
- `linuxdeploy` for AppDir
- `appimagetool --runtime-file` for final AppImage

## 3. Manual Linux AppImage Commands

If you do not want the script, use:

```bash
pyinstaller --noconfirm --clean zcrazy.spec
mkdir -p AppDir/usr/bin
cp dist/zcrazy AppDir/usr/bin/zcrazy

cat > AppDir/zcrazy.desktop << 'EOF'
[Desktop Entry]
Type=Application
Name=zcrazy
Exec=zcrazy
Icon=zcrazy
Categories=Utility;
EOF

./linuxdeploy-x86_64.AppImage --appdir AppDir -d AppDir/zcrazy.desktop -i AppDir/zcrazy.png
./appimagetool-x86_64.AppImage --runtime-file runtime-x86_64 AppDir zcrazy-x86_64.AppImage
```

## 4. Windows EXE

Build on Windows:

```powershell
pyinstaller --noconfirm --clean zcrazy.spec
```

Output:
- `dist\\zcrazy.exe` (onefile) or `dist\\zcrazy\\` (onedir), depending on spec

## 5. Runtime Resource Notes

`main.py` uses `resource_path(...)` for packaged mode (`_MEIPASS`).
Therefore these resource files must be included by `zcrazy.spec` in `datas`:
- `main.qml`
- `UI.qml`
- `ZGroupBox.qml`
- `ZText.qml`
- `qtquickcontrols2.conf`
- `zcrazy.txt`

## 6. Quick Verification

### Linux AppImage

```bash
chmod +x zcrazy-x86_64.AppImage
./zcrazy-x86_64.AppImage
```

### Windows EXE

Run generated EXE directly and verify UI starts and robot command panel works.
