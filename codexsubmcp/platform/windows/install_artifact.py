from __future__ import annotations

import shutil
from pathlib import Path

from codexsubmcp.app_paths import build_runtime_paths


STABLE_EXE_NAME = "CodexSubMcpManager.exe"


def install_current_executable(source_path: Path) -> Path:
    paths = build_runtime_paths()
    paths.bin_dir.mkdir(parents=True, exist_ok=True)
    target_path = paths.bin_dir / STABLE_EXE_NAME
    shutil.copyfile(source_path, target_path)
    return target_path
