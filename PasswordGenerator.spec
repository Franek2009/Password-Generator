# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import sys


PROJECT_ROOT = Path(SPEC).resolve().parent
EXE_OPTIONS = (
    {"icon": str(PROJECT_ROOT / "assets" / "icon.ico")}
    if sys.platform == "win32"
    else {}
)


a = Analysis(
    [str(PROJECT_ROOT / "main.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=[
        (str(PROJECT_ROOT / "data" / "words.txt"), "data"),
        (str(PROJECT_ROOT / "assets" / "icon.png"), "assets"),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
EXCLUDED_QT_COMPONENTS = (
    "virtualkeyboard",
    "qt6qml",
    "qt6quick",
    "qt6pdf",
)
EXCLUDED_QT_PLUGINS = {
    "libqpdf.so",
    "qpdf.dll",
}


def include_qt_entry(entry):
    destination = entry[0].replace("\\", "/").lower()
    filename = destination.rsplit("/", 1)[-1]
    return (
        not any(component in destination for component in EXCLUDED_QT_COMPONENTS)
        and filename not in EXCLUDED_QT_PLUGINS
    )


a.binaries = [entry for entry in a.binaries if include_qt_entry(entry)]
a.datas = [entry for entry in a.datas if include_qt_entry(entry)]
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PasswordGenerator",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=sys.platform != "win32",
    **EXE_OPTIONS,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="PasswordGenerator",
)
