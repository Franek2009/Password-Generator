# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
from shutil import copy2, copytree
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

# PyInstaller 6 places normal data files in _internal. Distribution documents
# are copied after COLLECT so they remain easy to find next to the executable.
distribution_root = Path(coll.name)
copy2(PROJECT_ROOT / "LICENSE", distribution_root / "LICENSE")
copy2(
    PROJECT_ROOT / "THIRD_PARTY_NOTICES.md",
    distribution_root / "THIRD_PARTY_NOTICES.md",
)

common_license_files = (
    "APACHE-2.0.txt",
    "GPL-3.0.txt",
    "LGPL-3.0.txt",
    "PYTHON-3.14.txt",
)
platform_license_files = (
    (
        "GCC-RUNTIME-LIBRARY-EXCEPTION-3.1.txt",
        "ICU-73.2.txt",
        "LGPL-2.1.txt",
        "LIBCOM_ERR-1.47.0.txt",
    )
    if sys.platform.startswith("linux")
    else ()
)

licenses_root = distribution_root / "licenses"
licenses_root.mkdir(exist_ok=True)
for license_filename in common_license_files + platform_license_files:
    copy2(
        PROJECT_ROOT / "licenses" / license_filename,
        licenses_root / license_filename,
    )

if sys.platform.startswith("linux"):
    copytree(
        PROJECT_ROOT / "licenses" / "linux-ubuntu-24.04",
        licenses_root / "linux-ubuntu-24.04",
    )
