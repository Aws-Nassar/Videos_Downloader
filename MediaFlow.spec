# -*- mode: python ; coding: utf-8 -*-

import shutil
from pathlib import Path

project_dir = Path(SPECPATH)
icon_path = project_dir / "assets" / "mediaflow.ico"
asset_datas = []
if icon_path.exists():
    asset_datas.append((str(icon_path), "assets"))
png_icon_path = project_dir / "assets" / "mediaflow.png"
if png_icon_path.exists():
    asset_datas.append((str(png_icon_path), "assets"))

# ---------------------------------------------------------------------------
# Bundle FFmpeg binaries so the .exe works without a system FFmpeg install.
# It looks for ffmpeg.exe / ffprobe.exe in these locations (first match wins):
#   1. tools\ subfolder next to this spec file  (recommended – put them there)
#   2. Anywhere on the system PATH
# ---------------------------------------------------------------------------
binaries = []
ffmpeg_names = ["ffmpeg.exe", "ffprobe.exe", "ffplay.exe"]
tools_dir = project_dir / "tools"
for name in ffmpeg_names:
    candidate = tools_dir / name
    if candidate.exists():
        binaries.append((str(candidate), "."))  # bundle into root of the exe
    else:
        found = shutil.which(name)
        if found:
            binaries.append((found, "."))

a = Analysis(
    ["app.py"],
    pathex=[str(project_dir)],
    binaries=binaries,
    datas=asset_datas,
    hiddenimports=["yt_dlp", "PyQt5.sip"],
    hookspath=[],
    hooksconfig={},
    # Prepends _MEIPASS to PATH so bundled ffmpeg.exe is found automatically
    runtime_hooks=["hooks\\hook_ffmpeg_path.py"],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="MediaFlow",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icon_path) if icon_path.exists() else None,
)
