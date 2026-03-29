# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import tomllib

from PyInstaller.utils.win32.versioninfo import (
    VSVersionInfo,
    FixedFileInfo,
    StringFileInfo,
    StringTable,
    StringStruct,
    VarFileInfo,
    VarStruct,
)

PROJECT_ROOT = Path.cwd()


def _load_project_version() -> str:
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return str(pyproject["project"]["version"])


def _version_tuple(version: str) -> tuple[int, int, int, int]:
    parts = [int(part) for part in version.split(".")]
    if len(parts) > 4:
        raise ValueError(f"unsupported version format: {version}")
    while len(parts) < 4:
        parts.append(0)
    return tuple(parts)


def _build_version_info(version: str) -> VSVersionInfo:
    version_tuple = _version_tuple(version)
    file_version = ".".join(str(part) for part in version_tuple)
    return VSVersionInfo(
        ffi=FixedFileInfo(
            filevers=version_tuple,
            prodvers=version_tuple,
            mask=0x3F,
            flags=0x0,
            OS=0x40004,
            fileType=0x1,
            subtype=0x0,
            date=(0, 0),
        ),
        kids=[
            StringFileInfo(
                [
                    StringTable(
                        "040904B0",
                        [
                            StringStruct("CompanyName", "leonsong09"),
                            StringStruct("FileDescription", "CodexSubMcp Windows GUI manager"),
                            StringStruct("FileVersion", file_version),
                            StringStruct("InternalName", "CodexSubMcpManager"),
                            StringStruct("OriginalFilename", "CodexSubMcpManager.exe"),
                            StringStruct("ProductName", "CodexSubMcpManager"),
                            StringStruct("ProductVersion", version),
                        ],
                    )
                ]
            ),
            VarFileInfo([VarStruct("Translation", [1033, 1200])]),
        ],
    )


PROJECT_VERSION = _load_project_version()
VERSION_INFO = _build_version_info(PROJECT_VERSION)

a = Analysis(
    [str(PROJECT_ROOT / "codexsubmcp" / "__main__.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=[],
    hiddenimports=[],
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
    version=VERSION_INFO,
)
