from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Sequence

from codexsubmcp.core.models import McpRecord


def _infer_config_source(path: Path) -> str:
    lower_name = path.name.lower()
    if "codex" in lower_name:
        return "codex_config"
    if "cursor" in lower_name:
        return "cursor_config"
    if "claude" in lower_name:
        return "claude_config"
    return "config_file"


def _looks_like_mcp(name: str) -> bool:
    lowered = name.lower()
    return lowered.startswith("@modelcontextprotocol/") or "mcp" in lowered


def discover_config_paths() -> list[Path]:
    appdata = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    localappdata = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    userprofile = Path(os.environ.get("USERPROFILE") or Path.home())
    candidates = [
        appdata / "Claude" / "claude_desktop_config.json",
        appdata / "Codex" / "mcp.json",
        localappdata / "Codex" / "mcp.json",
        userprofile / ".cursor" / "mcp.json",
        userprofile / ".cursor" / "mcp_config.json",
    ]
    return [path for path in candidates if path.exists()]


def scan_configured_sources(config_paths: Sequence[Path] | None = None) -> list[McpRecord]:
    if config_paths is None:
        config_paths = discover_config_paths()

    records: list[McpRecord] = []
    for config_path in config_paths:
        if not config_path.exists():
            continue
        payload = json.loads(config_path.read_text(encoding="utf-8"))
        servers = payload.get("mcpServers") or payload.get("servers") or {}
        if not isinstance(servers, dict):
            continue
        source = _infer_config_source(config_path)
        for name, config in servers.items():
            if not isinstance(config, dict):
                continue
            command = config.get("command")
            args = config.get("args") or []
            command_text = " ".join([str(command), *[str(item) for item in args]]).strip() if command else None
            records.append(
                McpRecord(
                    name=str(name),
                    category="configured",
                    source=source,
                    command=command_text,
                    path=Path(command) if isinstance(command, str) and ("/" in command or "\\" in command) else None,
                    confidence="high",
                )
            )
    return records


def scan_npm_global_packages() -> list[McpRecord]:
    try:
        result = subprocess.run(
            ["npm", "-g", "list", "--depth=0", "--json"],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return []
    if result.returncode != 0:
        return []
    payload = json.loads(result.stdout or "{}")
    dependencies = payload.get("dependencies") or {}
    records: list[McpRecord] = []
    for name, metadata in dependencies.items():
        if not _looks_like_mcp(name):
            continue
        version = None
        if isinstance(metadata, dict):
            version = metadata.get("version")
        records.append(
            McpRecord(
                name=str(name),
                category="installed_candidate",
                source="npm_global",
                version=str(version) if version else None,
                confidence="high" if str(name).startswith("@modelcontextprotocol/") else "medium",
            )
        )
    return records


def scan_path_candidates() -> list[McpRecord]:
    return []


def scan_python_candidates() -> list[McpRecord]:
    return []
