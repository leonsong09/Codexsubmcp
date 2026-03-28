from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from codexsubmcp.core.models import McpRecord

CODEX_CONFIG_FILE_NAME = "config.toml"
CODEX_CONFIG_DIR_NAME = ".codex"
CONFIGURED_CATEGORY = "configured"
GLOBAL_SOURCE = "codex_global_config"
PROJECT_SOURCE = "codex_project_config"
DEFAULT_HOME = Path.home()
_DEFAULT_SENTINEL = object()


@dataclass(frozen=True)
class CodexConfigPaths:
    global_config_path: Path | None
    project_config_path: Path | None


def discover_codex_config_paths(*, start_dir: Path | None = None) -> CodexConfigPaths:
    global_path = _global_codex_config_path()
    project_path = _find_project_codex_config(start_dir or Path.cwd())
    return CodexConfigPaths(
        global_config_path=global_path if global_path.exists() else None,
        project_config_path=project_path,
    )


def scan_codex_configured_mcps(
    *,
    start_dir: Path | None = None,
    global_config_path: Path | None | object = _DEFAULT_SENTINEL,
    project_config_path: Path | None | object = _DEFAULT_SENTINEL,
) -> list[McpRecord]:
    paths = discover_codex_config_paths(start_dir=start_dir)
    resolved_global_path = paths.global_config_path if global_config_path is _DEFAULT_SENTINEL else global_config_path
    resolved_project_path = (
        paths.project_config_path if project_config_path is _DEFAULT_SENTINEL else project_config_path
    )
    records: list[McpRecord] = []
    if isinstance(resolved_global_path, Path):
        records.extend(_load_records_from_toml(resolved_global_path, source=GLOBAL_SOURCE))
    if isinstance(resolved_project_path, Path):
        records.extend(_load_records_from_toml(resolved_project_path, source=PROJECT_SOURCE))
    return records


def _global_codex_config_path() -> Path:
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        return Path(codex_home) / CODEX_CONFIG_FILE_NAME
    return Path.home() / CODEX_CONFIG_DIR_NAME / CODEX_CONFIG_FILE_NAME


def _find_project_codex_config(start_dir: Path) -> Path | None:
    search_root = start_dir
    if search_root.suffix:
        search_root = search_root.parent
    reserved_global_paths = {
        _global_codex_config_path(),
        Path.home() / CODEX_CONFIG_DIR_NAME / CODEX_CONFIG_FILE_NAME,
        DEFAULT_HOME / CODEX_CONFIG_DIR_NAME / CODEX_CONFIG_FILE_NAME,
    }
    for candidate_root in [search_root, *search_root.parents]:
        candidate = candidate_root / CODEX_CONFIG_DIR_NAME / CODEX_CONFIG_FILE_NAME
        if candidate in reserved_global_paths:
            continue
        if candidate.exists():
            return candidate
    return None


def _load_records_from_toml(path: Path, *, source: str) -> list[McpRecord]:
    payload = tomllib.loads(path.read_text(encoding="utf-8"))
    servers = payload.get("mcp_servers")
    if not isinstance(servers, dict):
        return []
    records: list[McpRecord] = []
    for name, config in servers.items():
        if not isinstance(config, dict):
            continue
        record = _normalize_record(name=str(name), config=config, source=source)
        if record is not None:
            records.append(record)
    return records


def _normalize_record(*, name: str, config: dict[str, Any], source: str) -> McpRecord | None:
    command = _string_or_none(config.get("command"))
    url = _string_or_none(config.get("url"))
    if command is not None:
        record_type = "stdio"
        record_command = command
        record_args = _normalize_args(config.get("args"))
        record_path = _command_path(command)
        env_keys = _normalize_env_keys(config.get("env"))
    elif url is not None:
        record_type = "streamable_http"
        record_command = url
        record_args = ()
        record_path = None
        env_keys = ()
    else:
        return None
    return McpRecord(
        name=name,
        category=CONFIGURED_CATEGORY,
        source=source,
        command=record_command,
        path=record_path,
        confidence="high",
        type=record_type,
        args=record_args,
        env_keys=env_keys,
        startup_timeout_ms=_normalize_startup_timeout_ms(config),
        tool_timeout_sec=_normalize_float(config.get("tool_timeout_sec")),
    )


def _normalize_args(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(item) for item in value)


def _normalize_env_keys(value: Any) -> tuple[str, ...]:
    if not isinstance(value, dict):
        return ()
    return tuple(sorted(str(key) for key in value))


def _normalize_startup_timeout_ms(config: dict[str, Any]) -> int | None:
    startup_timeout_ms = config.get("startup_timeout_ms")
    if isinstance(startup_timeout_ms, int):
        return startup_timeout_ms
    startup_timeout_sec = _normalize_float(config.get("startup_timeout_sec"))
    if startup_timeout_sec is None:
        return None
    return int(startup_timeout_sec * 1000)


def _normalize_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    return None


def _string_or_none(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    return None


def _command_path(command: str) -> Path | None:
    if "/" in command or "\\" in command:
        return Path(command)
    return None
