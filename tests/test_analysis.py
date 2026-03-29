from __future__ import annotations

from datetime import datetime
from pathlib import Path

from codexsubmcp.core.analysis import analyze_snapshot
from codexsubmcp.core.models import McpRecord, ProcessInfo
from codexsubmcp.core.system_snapshot import CodexRuntimeSnapshot, SystemSnapshot


def _proc(
    pid: int,
    ppid: int,
    name: str,
    created_at: str,
    command_line: str,
) -> ProcessInfo:
    return ProcessInfo(
        pid=pid,
        ppid=ppid,
        name=name,
        created_at=datetime.fromisoformat(created_at),
        command_line=command_line,
    )


def _configured_record(name: str, *args: str) -> McpRecord:
    return McpRecord(
        name=name,
        category="configured",
        source="codex_global_config",
        command="npx",
        args=args,
        type="stdio",
    )


def _snapshot(configured_mcps: list[McpRecord]) -> SystemSnapshot:
    return SystemSnapshot(
        snapshot_id="snapshot-1",
        captured_at=datetime.fromisoformat("2026-03-28T12:00:00"),
        codex=CodexRuntimeSnapshot(
            global_config_path=Path("C:/Users/test/.codex/config.toml"),
            project_config_path=None,
            state_db_path=Path("C:/Users/test/.codex/state_5.sqlite"),
            open_subagent_count=3,
        ),
        configured_mcps=tuple(configured_mcps),
        processes=(
            _proc(100, 1, "codex.exe", "2026-03-28T11:59:00", "codex.exe"),
            _proc(110, 100, "cmd.exe", "2026-03-28T12:00:00", "cmd /c npx -y agentation-mcp server"),
            _proc(111, 110, "node.exe", "2026-03-28T12:00:01", "node agentation-mcp cli.js server"),
            _proc(120, 100, "cmd.exe", "2026-03-28T12:01:00", "cmd /c npx -y agentation-mcp server"),
            _proc(121, 120, "node.exe", "2026-03-28T12:01:01", "node agentation-mcp cli.js server"),
            _proc(
                210,
                9999,
                "cmd.exe",
                "2026-03-28T12:02:00",
                "cmd /c npx -y @modelcontextprotocol/server-memory",
            ),
            _proc(211, 210, "node.exe", "2026-03-28T12:02:01", "node npx-cli.js @modelcontextprotocol/server-memory"),
        ),
    )


def test_analyze_snapshot_reports_configured_running_and_open_counts():
    result = analyze_snapshot(
        _snapshot(
            [
                _configured_record("agentation", "-y", "agentation-mcp", "server"),
                _configured_record("memory", "-y", "@modelcontextprotocol/server-memory"),
            ]
        )
    )

    assert result.summary.configured_mcp_count == 2
    assert result.summary.running_mcp_instance_count == 3
    assert result.summary.open_subagent_count == 3


def test_analyze_snapshot_reports_zero_drift_when_runtime_matches_config():
    result = analyze_snapshot(
        _snapshot(
            [
                _configured_record("agentation", "-y", "agentation-mcp", "server"),
                _configured_record("memory", "-y", "@modelcontextprotocol/server-memory"),
            ]
        )
    )

    assert result.summary.drift_missing_runtime_count == 0
    assert result.summary.drift_unconfigured_runtime_count == 0
    assert result.configured_not_running == ()
    assert result.running_not_configured == ()


def test_analyze_snapshot_reports_unconfigured_runtime_signatures():
    result = analyze_snapshot(
        _snapshot(
            [
                _configured_record("memory", "-y", "@modelcontextprotocol/server-memory"),
            ]
        )
    )

    assert result.summary.drift_unconfigured_runtime_count == 1
    assert result.running_not_configured == ("agentation-mcp",)

def test_analyze_snapshot_groups_running_mcps_by_signature():
    result = analyze_snapshot(
        _snapshot(
            [
                _configured_record("agentation", "-y", "agentation-mcp", "server"),
                _configured_record("memory", "-y", "@modelcontextprotocol/server-memory"),
            ]
        )
    )

    by_signature = {item.tool_signature: item for item in result.running_mcps}

    assert by_signature["agentation-mcp"].instance_count == 2
    assert by_signature["agentation-mcp"].live_codex_pid_count == 1
    assert by_signature["server-memory"].instance_count == 1
    assert by_signature["server-memory"].live_codex_pid_count == 0
