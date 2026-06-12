# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for MarkItDown GUI.
# Build with:  pyinstaller markitdown_gui.spec

import sys
from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = [], [], []
# These packages ship data files (themes, ML models) that PyInstaller
# does not discover on its own.
for pkg in ("customtkinter", "magika", "markitdown", "tkinterdnd2"):
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        pass  # optional package not installed — skip

datas += [("assets/icon.png", "assets")]

a = Analysis(
    ["src/markitdown_gui/__main__.py"],
    pathex=["src"],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["pytest", "ruff"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="markitdown-gui" if sys.platform != "win32" else "MarkItDownGUI",
    debug=False,
    strip=False,
    upx=False,
    console=False,
    icon="assets/icon.ico" if sys.platform == "win32" else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="MarkItDownGUI" if sys.platform == "win32" else "markitdown-gui",
)
