from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from codexsubmcp.core.models import McpRecord, ProcessInfo
from codexsubmcp.core.system_snapshot import build_system_snapshot


def _proc(pid: int, ppid: int, created_at: str, command_line: str) -> ProcessInfo:
    return ProcessInfo(
        pid=pid,
        ppid=ppid,
        name="node.exe",
        created_at=datetime.fromisoformat(created_at),
        command_line=command_line,
    )


def _write_open_subagent_db(path: Path, statuses: list[str]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute("create table thread_spawn_edges (status text not null)")
    connection.executemany(
        "insert into thread_spawn_edges(status) values (?)",
        [(status,) for status in statuses],
    )
    connection.commit()
    connection.close()
    return path


def test_build_system_snapshot_combines_configured_mcps_subagents_and_processes(tmp_path):
    state_db_path = _write_open_subagent_db(
        tmp_path / "sqlite" / "state_5.sqlite",
        ["open", "closed", "open"],
    )
    configured_records = [
        McpRecord(
            name="memory",
            category="configured",
            source="codex_global_config",
            command="npx",
            args=("-y", "@modelcontextprotocol/server-memory"),
            type="stdio",
        )
    ]
    processes = [
        _proc(210, 100, "2026-03-28T10:00:00", "npx @modelcontextprotocol/server-memory"),
        _proc(211, 210, "2026-03-28T10:00:01", "node server-memory"),
    ]

    snapshot = build_system_snapshot(
        start_dir=tmp_path / "workspace",
        state_db_path=state_db_path,
        configured_mcp_loader=lambda **_: configured_records,
        process_loader=lambda: processes,
    )

    assert snapshot.codex.open_subagent_count == 2
    assert snapshot.codex.state_db_path == state_db_path
    assert snapshot.configured_mcps == tuple(configured_records)
    assert snapshot.processes == tuple(processes)


def test_build_system_snapshot_returns_stable_empty_state_when_configs_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / ".codex"))
    monkeypatch.setenv("CODEX_SQLITE_HOME", str(tmp_path / "sqlite"))

    snapshot = build_system_snapshot(
        start_dir=tmp_path / "workspace",
        process_loader=lambda: [],
    )

    assert snapshot.codex.global_config_path is None
    assert snapshot.codex.project_config_path is None
    assert snapshot.codex.open_subagent_count == 0
    assert snapshot.configured_mcps == ()
    assert snapshot.processes == ()


def test_build_system_snapshot_generates_snapshot_id_and_captured_at(tmp_path):
    before = datetime.now()

    snapshot = build_system_snapshot(
        start_dir=tmp_path / "workspace",
        state_db_path=tmp_path / "sqlite" / "state_5.sqlite",
        configured_mcp_loader=lambda **_: [],
        process_loader=lambda: [],
    )

    after = datetime.now()

    assert snapshot.snapshot_id
    assert snapshot.captured_at >= before
    assert snapshot.captured_at <= after
