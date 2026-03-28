from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from codexsubmcp.core.config import DEFAULT_CONFIG

APP_DIR_NAME = "CodexSubMcpManager"
CODEX_DIR_NAME = ".codex"
CODEX_STATE_DB_NAME = "state_5.sqlite"


@dataclass(frozen=True)
class RuntimePaths:
    root: Path
    config: Path
    logs: Path
    cache: Path
    exports: Path
    bin_dir: Path


def _local_appdata_root() -> Path:
    value = os.environ.get("LOCALAPPDATA")
    if value:
        return Path(value)
    return Path.home() / "AppData" / "Local"


def resolve_codex_home() -> Path:
    value = os.environ.get("CODEX_HOME")
    if value:
        return Path(value)
    return Path.home() / CODEX_DIR_NAME


def resolve_codex_sqlite_home() -> Path:
    value = os.environ.get("CODEX_SQLITE_HOME")
    if value:
        path = Path(value)
        return path if path.is_absolute() else Path.cwd() / path
    return resolve_codex_home()


def resolve_codex_state_db_path() -> Path:
    return resolve_codex_sqlite_home() / CODEX_STATE_DB_NAME


def build_runtime_paths() -> RuntimePaths:
    root = _local_appdata_root() / APP_DIR_NAME
    return RuntimePaths(
        root=root,
        config=root / "config.json",
        logs=root / "logs",
        cache=root / "cache",
        exports=root / "exports",
        bin_dir=root / "bin",
    )


def ensure_runtime_config() -> Path:
    paths = build_runtime_paths()
    paths.root.mkdir(parents=True, exist_ok=True)
    paths.logs.mkdir(parents=True, exist_ok=True)
    paths.cache.mkdir(parents=True, exist_ok=True)
    paths.exports.mkdir(parents=True, exist_ok=True)
    paths.bin_dir.mkdir(parents=True, exist_ok=True)
    if not paths.config.exists():
        paths.config.write_text(
            json.dumps(DEFAULT_CONFIG, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    return paths.config


def find_legacy_config(project_root: Path) -> Path | None:
    candidate = project_root / "temp" / "codex_mcp_watchdog" / "config.json"
    if candidate.exists():
        return candidate
    return None
