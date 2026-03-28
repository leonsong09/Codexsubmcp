from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from codexsubmcp.app_paths import resolve_codex_state_db_path
from codexsubmcp.core.codex_mcp_config import (
    discover_codex_config_paths,
    scan_codex_configured_mcps,
)
from codexsubmcp.core.models import McpRecord, ProcessInfo
from codexsubmcp.platform.windows.processes import load_windows_processes


@dataclass(frozen=True)
class CodexRuntimeSnapshot:
    global_config_path: Path | None
    project_config_path: Path | None
    state_db_path: Path
    open_subagent_count: int


@dataclass(frozen=True)
class SystemSnapshot:
    snapshot_id: str
    captured_at: datetime
    codex: CodexRuntimeSnapshot
    configured_mcps: tuple[McpRecord, ...]
    processes: tuple[ProcessInfo, ...]


def count_open_subagent_threads(*, state_db_path: Path | None = None) -> int:
    resolved_state_db_path = state_db_path or resolve_codex_state_db_path()
    if not resolved_state_db_path.exists():
        return 0
    try:
        with sqlite3.connect(resolved_state_db_path) as connection:
            row = connection.execute(
                "select count(*) from thread_spawn_edges where status = 'open'"
            ).fetchone()
    except sqlite3.Error:
        return 0
    return int(row[0] if row else 0)


def build_system_snapshot(
    *,
    start_dir: Path | None = None,
    state_db_path: Path | None = None,
    configured_mcp_loader=scan_codex_configured_mcps,
    process_loader=load_windows_processes,
) -> SystemSnapshot:
    config_paths = discover_codex_config_paths(start_dir=start_dir)
    resolved_state_db_path = state_db_path or resolve_codex_state_db_path()
    configured_mcps = tuple(
        configured_mcp_loader(
            start_dir=start_dir,
            global_config_path=config_paths.global_config_path,
            project_config_path=config_paths.project_config_path,
        )
    )
    return SystemSnapshot(
        snapshot_id=uuid4().hex,
        captured_at=datetime.now(),
        codex=CodexRuntimeSnapshot(
            global_config_path=config_paths.global_config_path,
            project_config_path=config_paths.project_config_path,
            state_db_path=resolved_state_db_path,
            open_subagent_count=count_open_subagent_threads(state_db_path=resolved_state_db_path),
        ),
        configured_mcps=configured_mcps,
        processes=tuple(process_loader()),
    )
