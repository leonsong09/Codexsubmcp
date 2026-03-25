# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules


PROJECT_ROOT = Path.cwd()
PYSIDE6_DATA = collect_data_files("PySide6")
PYSIDE6_HIDDENIMPORTS = collect_submodules("PySide6")


a = Analysis(
    [str(PROJECT_ROOT / "codexsubmcp" / "__main__.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=PYSIDE6_DATA,
    hiddenimports=PYSIDE6_HIDDENIMPORTS,
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
    name="CodexSubMcpManager",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
)
