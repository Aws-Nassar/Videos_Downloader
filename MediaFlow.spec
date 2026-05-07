# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

project_dir = Path(SPECPATH)
icon_path = project_dir / "assets" / "mediaflow.ico"
asset_datas = []
if icon_path.exists():
    asset_datas.append((str(icon_path), "assets"))
png_icon_path = project_dir / "assets" / "mediaflow.png"
if png_icon_path.exists():
    asset_datas.append((str(png_icon_path), "assets"))

a = Analysis(
    ["app.py"],
    pathex=[str(project_dir)],
    binaries=[],
    datas=asset_datas,
    hiddenimports=["yt_dlp"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
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
